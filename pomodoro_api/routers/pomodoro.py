import logging
import os
from datetime import datetime
from typing import List, Optional

import jwt
from django.conf import settings
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Header, Router
from ninja.responses import Response
from pomodoro.models import PomodoroSession
from pydantic import BaseModel
from tasks.models import Task
from users.models import User

logger = logging.getLogger("pomodoro_api")

# 從 .env 獲取密鑰或使用 Django settings
JWT_SECRET = os.getenv("SECRET_KEY", settings.SECRET_KEY)

router = Router(tags=["番茄鐘"])


# 從授權標頭中解析用戶ID
def get_user_id_from_token(authorization: str = Header(None)):
    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            return payload.get("user_id")
        except jwt.PyJWTError as e:
            logger.error(f"JWT Authentication error: {str(e)}")
            return None
    return None


# ============= 請求和回應模型 =============


class ErrorResponse(BaseModel):
    detail: str


class PomodoroSessionSchema(BaseModel):
    id: int
    user_id: int
    task_id: Optional[int] = None
    task_title: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: int
    type: str
    is_completed: bool


class SessionCreateSchema(BaseModel):
    task_id: Optional[int] = None
    type: str
    duration: int


class SessionUpdateSchema(BaseModel):
    end_time: datetime
    is_completed: bool


class PomodoroStatsSchema(BaseModel):
    total_sessions: int
    total_completed: int
    total_minutes: int
    work_sessions: int
    short_break_sessions: int
    long_break_sessions: int
    completion_rate: float
    most_productive_day: Optional[str] = None
    most_focused_task_id: Optional[int] = None
    most_focused_task_title: Optional[str] = None


# ============= 番茄鐘 API =============


@router.post(
    "/start",
    response={200: PomodoroSessionSchema, 401: ErrorResponse, 404: ErrorResponse},
)
def start_session(
    request, data: SessionCreateSchema, authorization: str = Header(None)
):
    """開始新的番茄鐘階段"""
    logger.debug(f"Start pomodoro session, task_id: {data.task_id}, type: {data.type}")

    try:
        user_id = get_user_id_from_token(authorization)
        if not user_id:
            return Response({"detail": "認證失敗，無法獲取用戶ID"}, status=401)

        user = get_object_or_404(User, id=user_id)

        # 檢查任務是否存在
        task = None
        if data.task_id:
            task = get_object_or_404(Task, id=data.task_id, user=user)

        # 創建新的番茄鐘階段
        session = PomodoroSession.objects.create(
            user=user,
            task=task,
            start_time=timezone.now(),  # 使用 timezone.now() 而不是 datetime.now()
            duration=data.duration,
            type=data.type,
            is_completed=False,
        )

        return {
            "id": session.id,
            "user_id": user.id,
            "task_id": task.id if task else None,
            "task_title": task.title if task else None,
            "start_time": session.start_time,
            "end_time": None,
            "duration": session.duration,
            "type": session.type,
            "is_completed": session.is_completed,
        }
    except User.DoesNotExist:
        logger.warning(f"User not found: {user_id}")
        return Response({"detail": "用戶不存在"}, status=404)
    except Task.DoesNotExist:
        logger.warning(f"Task not found: {data.task_id}")
        return Response({"detail": "任務不存在"}, status=404)
    except Exception as e:
        logger.error(f"Error starting pomodoro session: {str(e)}")
        return Response({"detail": f"開始番茄鐘階段時發生錯誤: {str(e)}"}, status=500)


@router.put(
    "/{session_id}/complete",
    response={200: PomodoroSessionSchema, 401: ErrorResponse, 404: ErrorResponse},
)
def complete_session(
    request,
    session_id: int,
    data: SessionUpdateSchema,
    authorization: str = Header(None),
):
    """完成番茄鐘階段"""
    logger.debug(f"Complete pomodoro session: {session_id}")

    try:
        user_id = get_user_id_from_token(authorization)
        if not user_id:
            return Response({"detail": "認證失敗，無法獲取用戶ID"}, status=401)

        session = get_object_or_404(PomodoroSession, id=session_id, user_id=user_id)

        # 更新番茄鐘階段，確保時間包含時區信息
        if isinstance(data.end_time, datetime) and data.end_time.tzinfo is None:
            end_time = timezone.make_aware(data.end_time)
        else:
            end_time = data.end_time

        session.end_time = end_time
        session.is_completed = data.is_completed
        session.save()

        # 如果完成了工作階段，更新相關任務的已完成番茄鐘數
        if session.is_completed and session.type == "work" and session.task:
            task = session.task
            task.completed_pomodoros += 1
            task.save()

        return {
            "id": session.id,
            "user_id": session.user.id,
            "task_id": session.task.id if session.task else None,
            "task_title": session.task.title if session.task else None,
            "start_time": session.start_time,
            "end_time": session.end_time,
            "duration": session.duration,
            "type": session.type,
            "is_completed": session.is_completed,
        }
    except PomodoroSession.DoesNotExist:
        logger.warning(f"Session not found: {session_id}")
        return Response({"detail": "番茄鐘階段不存在"}, status=404)
    except Exception as e:
        logger.error(f"Error completing pomodoro session: {str(e)}")
        return Response({"detail": f"完成番茄鐘階段時發生錯誤: {str(e)}"}, status=500)


@router.get("/history", response={200: List[PomodoroSessionSchema], 401: ErrorResponse})
def get_history(
    request,
    days: int = 7,
    task_id: Optional[int] = None,
    authorization: str = Header(None),
):
    """獲取番茄鐘歷史記錄"""
    logger.debug(f"Get pomodoro history, days: {days}, task_id: {task_id}")

    try:
        user_id = get_user_id_from_token(authorization)
        if not user_id:
            return Response({"detail": "認證失敗，無法獲取用戶ID"}, status=401)

        # 計算起始日期
        start_date = timezone.now() - timezone.timedelta(days=days)

        # 獲取歷史記錄
        query = PomodoroSession.objects.filter(
            user_id=user_id, start_time__gte=start_date
        ).order_by("-start_time")

        # 過濾特定任務
        if task_id:
            query = query.filter(task_id=task_id)

        sessions = query.select_related("task")

        return [
            {
                "id": session.id,
                "user_id": session.user.id,
                "task_id": session.task.id if session.task else None,
                "task_title": session.task.title if session.task else None,
                "start_time": session.start_time,
                "end_time": session.end_time,
                "duration": session.duration,
                "type": session.type,
                "is_completed": session.is_completed,
            }
            for session in sessions
        ]
    except Exception as e:
        logger.error(f"Error getting pomodoro history: {str(e)}")
        return Response(
            {"detail": f"獲取番茄鐘歷史記錄時發生錯誤: {str(e)}"}, status=500
        )


@router.get("/stats", response={200: PomodoroStatsSchema, 401: ErrorResponse})
def get_stats(request, days: int = 30, authorization: str = Header(None)):
    """獲取番茄鐘統計數據"""
    logger.debug(f"Get pomodoro stats, days: {days}")

    try:
        user_id = get_user_id_from_token(authorization)
        if not user_id:
            return Response({"detail": "認證失敗，無法獲取用戶ID"}, status=401)

        # 計算起始日期
        start_date = timezone.now() - timezone.timedelta(days=days)

        # 獲取所有符合條件的番茄鐘階段
        sessions = PomodoroSession.objects.filter(
            user_id=user_id, start_time__gte=start_date
        )

        # 計算統計數據
        total_sessions = sessions.count()
        completed_sessions = sessions.filter(is_completed=True).count()

        # 總專注時間（分鐘）
        total_minutes = (
            sessions.filter(is_completed=True).aggregate(total=Sum("duration"))["total"]
            or 0
        )
        total_minutes = total_minutes // 60

        # 不同類型的階段數量
        work_sessions = sessions.filter(type="work", is_completed=True).count()
        short_break_sessions = sessions.filter(
            type="short_break", is_completed=True
        ).count()
        long_break_sessions = sessions.filter(
            type="long_break", is_completed=True
        ).count()

        # 計算完成率
        completion_rate = (
            completed_sessions / total_sessions if total_sessions > 0 else 0
        )

        # 最多專注的日期
        most_productive_day = None
        day_counts = {}
        for session in sessions.filter(type="work", is_completed=True):
            day = session.start_time.date()
            day_counts[day] = day_counts.get(day, 0) + 1

        if day_counts:
            most_productive_day = max(day_counts.items(), key=lambda x: x[1])[0]
            most_productive_day = most_productive_day.strftime("%Y-%m-%d")

        # 最多專注的任務
        most_focused_task_id = None
        most_focused_task_title = None
        task_sessions = sessions.filter(
            type="work", is_completed=True, task__isnull=False
        )

        if task_sessions.exists():
            task_stats = (
                task_sessions.values("task")
                .annotate(count=Count("id"))
                .order_by("-count")
                .first()
            )

            if task_stats:
                task_id = task_stats["task"]
                task = Task.objects.get(id=task_id)
                most_focused_task_id = task.id
                most_focused_task_title = task.title

        return {
            "total_sessions": total_sessions,
            "total_completed": completed_sessions,
            "total_minutes": total_minutes,
            "work_sessions": work_sessions,
            "short_break_sessions": short_break_sessions,
            "long_break_sessions": long_break_sessions,
            "completion_rate": round(completion_rate, 2),
            "most_productive_day": most_productive_day,
            "most_focused_task_id": most_focused_task_id,
            "most_focused_task_title": most_focused_task_title,
        }
    except Exception as e:
        logger.error(f"Error getting pomodoro stats: {str(e)}")
        return Response(
            {"detail": f"獲取番茄鐘統計數據時發生錯誤: {str(e)}"}, status=500
        )


@router.delete(
    "/{session_id}", response={200: dict, 401: ErrorResponse, 404: ErrorResponse}
)
def delete_session(request, session_id: int, authorization: str = Header(None)):
    """刪除番茄鐘階段"""
    logger.debug(f"Delete pomodoro session: {session_id}")

    try:
        user_id = get_user_id_from_token(authorization)
        if not user_id:
            return Response({"detail": "認證失敗，無法獲取用戶ID"}, status=401)

        session = get_object_or_404(PomodoroSession, id=session_id, user_id=user_id)

        # 如果這是已完成的工作階段，需要減少任務的已完成番茄鐘數
        if session.is_completed and session.type == "work" and session.task:
            task = session.task
            if task.completed_pomodoros > 0:
                task.completed_pomodoros -= 1
                task.save()

        session.delete()

        return {"success": True}
    except PomodoroSession.DoesNotExist:
        logger.warning(f"Session not found: {session_id}")
        return Response({"detail": "番茄鐘階段不存在"}, status=404)
    except Exception as e:
        logger.error(f"Error deleting pomodoro session: {str(e)}")
        return Response({"detail": f"刪除番茄鐘階段時發生錯誤: {str(e)}"}, status=500)
