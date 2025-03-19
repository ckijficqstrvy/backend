import logging
import os
from datetime import date, datetime
from typing import List, Optional

import jwt
from django.conf import settings
from django.db.models import Q
from django.shortcuts import get_object_or_404
from ninja import Header, Router
from pydantic import BaseModel
from tasks.models import Category, Tag, Task
from users.models import User

# 獲取日誌記錄器
logger = logging.getLogger("pomodoro_api")

# 從 .env 獲取密鑰或使用 Django settings
JWT_SECRET = os.getenv("SECRET_KEY", settings.SECRET_KEY)

router = Router(tags=["任務"])


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


class CategorySchema(BaseModel):
    id: int
    name: str
    color_code: str


class CategoryCreateSchema(BaseModel):
    name: str
    color_code: str = "#e53e3e"


class TagSchema(BaseModel):
    id: int
    name: str
    color_code: str


class TagCreateSchema(BaseModel):
    name: str
    color_code: str = "#3b82f6"


class TaskSchema(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    due_date: Optional[date] = None
    estimated_pomodoros: int
    completed_pomodoros: int
    created_at: datetime  # 改為使用 datetime 類型而非 date
    updated_at: datetime  # 改為使用 datetime 類型而非 date
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    category_color: Optional[str] = None
    tags: List[TagSchema] = []


class TaskCreateSchema(BaseModel):
    title: str
    description: Optional[str] = None
    status: str = "pending"
    priority: str = "medium"
    due_date: Optional[date] = None
    estimated_pomodoros: int = 1
    category_id: Optional[int] = None
    tag_ids: List[int] = []


class TaskUpdateSchema(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[date] = None
    estimated_pomodoros: Optional[int] = None
    completed_pomodoros: Optional[int] = None
    category_id: Optional[int] = None
    tag_ids: Optional[List[int]] = None


# ============= 任務 API =============


@router.get("/", response=List[TaskSchema])
def list_tasks(
    request,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    category_id: Optional[int] = None,
    search: Optional[str] = None,
    authorization: str = Header(None),
):
    """獲取所有任務，可以按狀態、優先級或分類過濾"""
    user_id = get_user_id_from_token(authorization)
    if not user_id:
        return {"detail": "認證失敗，無法獲取用戶ID"}, 401

    query = Task.objects.filter(user_id=user_id)

    # 過濾
    if status:
        query = query.filter(status=status)
    if priority:
        query = query.filter(priority=priority)
    if category_id:
        query = query.filter(category_id=category_id)
    if search:
        query = query.filter(
            Q(title__icontains=search) | Q(description__icontains=search)
        )

    # 排序：先按優先級，再按到期日，最後按創建時間
    tasks = (
        query.select_related("category")
        .prefetch_related("tags")
        .order_by("-priority", "due_date", "created_at")
    )

    result = []
    for task in tasks:
        task_data = {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "status": task.status,
            "priority": task.priority,
            "due_date": task.due_date,
            "estimated_pomodoros": task.estimated_pomodoros,
            "completed_pomodoros": task.completed_pomodoros,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "category_id": task.category.id if task.category else None,
            "category_name": task.category.name if task.category else None,
            "category_color": task.category.color_code if task.category else None,
            "tags": [
                {"id": tag.id, "name": tag.name, "color_code": tag.color_code}
                for tag in task.tags.all()
            ],
        }
        result.append(task_data)

    return result


@router.post("/", response=TaskSchema)
def create_task(
    request, task_data: TaskCreateSchema, authorization: str = Header(None)
):
    """創建新任務"""
    user_id = get_user_id_from_token(authorization)
    if not user_id:
        return {"detail": "認證失敗，無法獲取用戶ID"}, 401

    user = get_object_or_404(User, id=user_id)

    # 檢查分類是否存在
    category = None
    if task_data.category_id:
        category = get_object_or_404(Category, id=task_data.category_id, user=user)

    # 創建任務
    task = Task.objects.create(
        title=task_data.title,
        description=task_data.description,
        status=task_data.status,
        priority=task_data.priority,
        due_date=task_data.due_date,
        estimated_pomodoros=task_data.estimated_pomodoros,
        user=user,
        category=category,
    )

    # 添加標籤
    if task_data.tag_ids:
        tags = Tag.objects.filter(id__in=task_data.tag_ids, user=user)
        task.tags.set(tags)

    # 返回創建的任務
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "priority": task.priority,
        "due_date": task.due_date,
        "estimated_pomodoros": task.estimated_pomodoros,
        "completed_pomodoros": task.completed_pomodoros,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "category_id": category.id if category else None,
        "category_name": category.name if category else None,
        "category_color": category.color_code if category else None,
        "tags": [
            {"id": tag.id, "name": tag.name, "color_code": tag.color_code}
            for tag in task.tags.all()
        ],
    }


@router.get("/{task_id}", response=TaskSchema)
def get_task(request, task_id: int, authorization: str = Header(None)):
    """獲取特定任務的詳細資訊"""
    user_id = get_user_id_from_token(authorization)
    if not user_id:
        return {"detail": "認證失敗，無法獲取用戶ID"}, 401

    task = get_object_or_404(Task, id=task_id, user_id=user_id)

    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "priority": task.priority,
        "due_date": task.due_date,
        "estimated_pomodoros": task.estimated_pomodoros,
        "completed_pomodoros": task.completed_pomodoros,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "category_id": task.category.id if task.category else None,
        "category_name": task.category.name if task.category else None,
        "category_color": task.category.color_code if task.category else None,
        "tags": [
            {"id": tag.id, "name": tag.name, "color_code": tag.color_code}
            for tag in task.tags.all()
        ],
    }


@router.put("/{task_id}", response=TaskSchema)
def update_task(
    request,
    task_id: int,
    task_data: TaskUpdateSchema,
    authorization: str = Header(None),
):
    """更新任務"""
    user_id = get_user_id_from_token(authorization)
    if not user_id:
        return {"detail": "認證失敗，無法獲取用戶ID"}, 401

    task = get_object_or_404(Task, id=task_id, user_id=user_id)

    # 更新字段
    if task_data.title is not None:
        task.title = task_data.title
    if task_data.description is not None:
        task.description = task_data.description
    if task_data.status is not None:
        task.status = task_data.status
    if task_data.priority is not None:
        task.priority = task_data.priority
    if task_data.due_date is not None:
        task.due_date = task_data.due_date
    if task_data.estimated_pomodoros is not None:
        task.estimated_pomodoros = task_data.estimated_pomodoros
    if task_data.completed_pomodoros is not None:
        task.completed_pomodoros = task_data.completed_pomodoros

    # 更新分類
    if task_data.category_id is not None:
        if task_data.category_id == 0:  # 設為無分類
            task.category = None
        else:
            category = get_object_or_404(
                Category, id=task_data.category_id, user_id=user_id
            )
            task.category = category

    # 更新標籤
    if task_data.tag_ids is not None:
        tags = Tag.objects.filter(id__in=task_data.tag_ids, user_id=user_id)
        task.tags.set(tags)

    task.save()

    # 獲取更新後的分類（如果有）
    category = task.category

    # 返回更新後的任務
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "priority": task.priority,
        "due_date": task.due_date,
        "estimated_pomodoros": task.estimated_pomodoros,
        "completed_pomodoros": task.completed_pomodoros,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "category_id": category.id if category else None,
        "category_name": category.name if category else None,
        "category_color": category.color_code if category else None,
        "tags": [
            {"id": tag.id, "name": tag.name, "color_code": tag.color_code}
            for tag in task.tags.all()
        ],
    }


@router.delete("/{task_id}")
def delete_task(request, task_id: int, authorization: str = Header(None)):
    """刪除任務"""
    user_id = get_user_id_from_token(authorization)
    if not user_id:
        return {"detail": "認證失敗，無法獲取用戶ID"}, 401

    task = get_object_or_404(Task, id=task_id, user_id=user_id)
    task.delete()

    return {"success": True}


# ============= 快速更新任務狀態 =============


@router.post("/{task_id}/complete")
def complete_task(request, task_id: int, authorization: str = Header(None)):
    """將任務標記為已完成"""
    user_id = get_user_id_from_token(authorization)
    if not user_id:
        return {"detail": "認證失敗，無法獲取用戶ID"}, 401

    task = get_object_or_404(Task, id=task_id, user_id=user_id)
    task.status = "completed"
    task.save()

    return {"success": True}


# ============= 分類 API =============


@router.get("/categories/", response=List[CategorySchema])
def list_categories(request, authorization: str = Header(None)):
    """獲取所有分類"""
    user_id = get_user_id_from_token(authorization)
    if not user_id:
        return {"detail": "認證失敗，無法獲取用戶ID"}, 401

    categories = Category.objects.filter(user_id=user_id)

    return [
        {"id": cat.id, "name": cat.name, "color_code": cat.color_code}
        for cat in categories
    ]


@router.post("/categories/", response=CategorySchema)
def create_category(
    request, data: CategoryCreateSchema, authorization: str = Header(None)
):
    """創建新分類"""
    user_id = get_user_id_from_token(authorization)
    if not user_id:
        return {"detail": "認證失敗，無法獲取用戶ID"}, 401

    user = get_object_or_404(User, id=user_id)

    category = Category.objects.create(
        name=data.name, color_code=data.color_code, user=user
    )

    return {"id": category.id, "name": category.name, "color_code": category.color_code}


@router.put("/categories/{category_id}", response=CategorySchema)
def update_category(
    request,
    category_id: int,
    data: CategoryCreateSchema,
    authorization: str = Header(None),
):
    """更新分類"""
    user_id = get_user_id_from_token(authorization)
    if not user_id:
        return {"detail": "認證失敗，無法獲取用戶ID"}, 401

    category = get_object_or_404(Category, id=category_id, user_id=user_id)

    category.name = data.name
    category.color_code = data.color_code
    category.save()

    return {"id": category.id, "name": category.name, "color_code": category.color_code}


@router.delete("/categories/{category_id}")
def delete_category(request, category_id: int, authorization: str = Header(None)):
    """刪除分類"""
    user_id = get_user_id_from_token(authorization)
    if not user_id:
        return {"detail": "認證失敗，無法獲取用戶ID"}, 401

    category = get_object_or_404(Category, id=category_id, user_id=user_id)

    # 將該分類的所有任務設為無分類
    Task.objects.filter(category=category).update(category=None)

    category.delete()

    return {"success": True}


# ============= 標籤 API =============


@router.get("/tags/", response=List[TagSchema])
def list_tags(request, authorization: str = Header(None)):
    """獲取所有標籤"""
    user_id = get_user_id_from_token(authorization)
    if not user_id:
        return {"detail": "認證失敗，無法獲取用戶ID"}, 401

    tags = Tag.objects.filter(user_id=user_id)

    return [
        {"id": tag.id, "name": tag.name, "color_code": tag.color_code} for tag in tags
    ]


@router.post("/tags/", response=TagSchema)
def create_tag(request, data: TagCreateSchema, authorization: str = Header(None)):
    """創建新標籤"""
    user_id = get_user_id_from_token(authorization)
    if not user_id:
        return {"detail": "認證失敗，無法獲取用戶ID"}, 401

    user = get_object_or_404(User, id=user_id)

    tag = Tag.objects.create(name=data.name, color_code=data.color_code, user=user)

    return {"id": tag.id, "name": tag.name, "color_code": tag.color_code}


@router.put("/tags/{tag_id}", response=TagSchema)
def update_tag(
    request, tag_id: int, data: TagCreateSchema, authorization: str = Header(None)
):
    """更新標籤"""
    user_id = get_user_id_from_token(authorization)
    if not user_id:
        return {"detail": "認證失敗，無法獲取用戶ID"}, 401

    tag = get_object_or_404(Tag, id=tag_id, user_id=user_id)

    tag.name = data.name
    tag.color_code = data.color_code
    tag.save()

    return {"id": tag.id, "name": tag.name, "color_code": tag.color_code}


@router.delete("/tags/{tag_id}")
def delete_tag(request, tag_id: int, authorization: str = Header(None)):
    """刪除標籤"""
    user_id = get_user_id_from_token(authorization)
    if not user_id:
        return {"detail": "認證失敗，無法獲取用戶ID"}, 401

    tag = get_object_or_404(Tag, id=tag_id, user_id=user_id)

    # 從所有任務中移除該標籤
    for task in tag.tasks.all():
        task.tags.remove(tag)

    tag.delete()

    return {"success": True}
