import logging
import os
from datetime import datetime, timedelta
from typing import Optional

import jwt
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from ninja import Header, Router
from ninja.responses import Response
from pydantic import BaseModel, EmailStr, Field
from users.models import User, UserSetting

# 獲取日誌記錄器
logger = logging.getLogger("pomodoro_api")

# 從 .env 獲取密鑰或使用 Django settings
JWT_SECRET = os.getenv("SECRET_KEY", settings.SECRET_KEY)

router = Router(tags=["認證"])


# 請求與回應模型
class ErrorResponse(BaseModel):
    detail: str


class SignUpSchema(BaseModel):
    username: str
    email: EmailStr
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class LoginSchema(BaseModel):
    username: str
    password: str


class TokenSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    email: str


class UserProfileSchema(BaseModel):
    id: int
    username: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_joined: datetime


class UserSettingsSchema(BaseModel):
    work_duration: int = Field(default=25 * 60)  # 預設工作時長 (秒)
    short_break_duration: int = Field(default=5 * 60)  # 預設短休息時長 (秒)
    long_break_duration: int = Field(default=15 * 60)  # 預設長休息時長 (秒)
    long_break_interval: int = Field(default=4)  # 多少番茄鐘後長休息
    notifications_enabled: bool = Field(default=True)  # 是否啟用通知


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


# 生成 JWT Token
def create_token(user_id: int) -> str:
    payload = {"user_id": user_id, "exp": datetime.utcnow() + timedelta(days=7)}
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    return token


# 註冊 - 使用 Response 手動建立回應
@router.post("/register", response={200: TokenSchema, 400: ErrorResponse})
def register(request, data: SignUpSchema):
    logger.debug(f"Register attempt for username: {data.username}")

    # 檢查用戶名是否已存在
    if User.objects.filter(username=data.username).exists():
        logger.warning(f"Username already exists: {data.username}")
        return Response({"detail": "使用者名稱已存在"}, status=400)

    # 檢查電子郵件是否已存在
    if User.objects.filter(email=data.email).exists():
        logger.warning(f"Email already exists: {data.email}")
        return Response({"detail": "電子郵件已存在"}, status=400)

    # 驗證密碼強度
    try:
        validate_password(data.password)
    except ValidationError as e:
        error_message = ", ".join([str(msg) for msg in e.messages])
        logger.warning(f"Password validation failed: {error_message}")
        return Response({"detail": error_message}, status=400)

    try:
        # 創建新用戶
        user = User.objects.create_user(
            username=data.username,
            email=data.email,
            password=data.password,
            first_name=data.first_name or "",
            last_name=data.last_name or "",
        )

        # 創建用戶設定
        UserSetting.objects.create(user=user)

        # 生成 token
        token = create_token(user.id)

        logger.info(f"User registered successfully: {user.id}")

        return {
            "access_token": token,
            "token_type": "bearer",
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
        }
    except Exception as e:
        logger.error(f"Error during user registration: {str(e)}")
        return Response({"detail": f"註冊過程中發生錯誤: {str(e)}"}, status=500)


# 登入
@router.post("/login", response={200: TokenSchema, 401: ErrorResponse})
def login(request, data: LoginSchema):
    logger.debug(f"Login attempt for username: {data.username}")

    try:
        user = authenticate(username=data.username, password=data.password)
        if user is None:
            logger.warning(f"Login failed for username: {data.username}")
            return Response({"detail": "使用者名稱或密碼錯誤"}, status=401)

        token = create_token(user.id)
        logger.info(f"User logged in successfully: {user.id}")

        return {
            "access_token": token,
            "token_type": "bearer",
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
        }
    except Exception as e:
        logger.error(f"Error during login: {str(e)}")
        return Response({"detail": f"登入過程中發生錯誤: {str(e)}"}, status=500)


# 獲取用戶資料 - 使用 Header 參數直接獲取授權信息
@router.get(
    "/user", response={200: UserProfileSchema, 401: ErrorResponse, 404: ErrorResponse}
)
def get_user(request, user_id: Optional[int] = None, authorization: str = Header(None)):
    """獲取用戶資料"""
    logger.debug(
        f"Get user profile, authorization header: {authorization[:20] if authorization else None}"
    )

    try:
        # 如果沒有提供user_id，從token中獲取
        if user_id is None:
            user_id = get_user_id_from_token(authorization)

        if user_id is None:
            logger.warning("Authentication failed, cannot get user ID")
            return Response({"detail": "認證失敗，無法獲取用戶ID"}, status=401)

        logger.debug(f"Looking up user with ID: {user_id}")
        user = User.objects.get(id=user_id)

        logger.info(f"User profile retrieved: {user.id}")
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "date_joined": user.date_joined,
        }
    except User.DoesNotExist:
        logger.warning(f"User not found: {user_id}")
        return Response({"detail": f"用戶ID {user_id} 不存在"}, status=404)
    except Exception as e:
        logger.error(f"Error retrieving user profile: {str(e)}")
        return Response({"detail": f"發生錯誤: {str(e)}"}, status=500)


# 獲取用戶設定 - 使用 Header 參數直接獲取授權信息
@router.get(
    "/settings",
    response={200: UserSettingsSchema, 401: ErrorResponse, 404: ErrorResponse},
)
def get_user_settings(request, authorization: str = Header(None)):
    """獲取用戶設定"""
    logger.debug(
        f"Get user settings, authorization header: {authorization[:20] if authorization else None}"
    )

    try:
        user_id = get_user_id_from_token(authorization)
        if user_id is None:
            logger.warning("Authentication failed, cannot get user ID")
            return Response({"detail": "認證失敗，無法獲取用戶ID"}, status=401)

        user = User.objects.get(id=user_id)
        settings, created = UserSetting.objects.get_or_create(user=user)

        logger.info(f"User settings retrieved: {user.id}")
        return {
            "work_duration": settings.work_duration,
            "short_break_duration": settings.short_break_duration,
            "long_break_duration": settings.long_break_duration,
            "long_break_interval": settings.long_break_interval,
            "notifications_enabled": settings.notifications_enabled,
        }
    except User.DoesNotExist:
        logger.warning(f"User not found: {user_id}")
        return Response({"detail": "用戶不存在"}, status=404)
    except Exception as e:
        logger.error(f"Error retrieving user settings: {str(e)}")
        return Response({"detail": f"發生錯誤: {str(e)}"}, status=500)


# 更新用戶設定 - 使用 Header 參數直接獲取授權信息
@router.put(
    "/settings",
    response={200: UserSettingsSchema, 401: ErrorResponse, 404: ErrorResponse},
)
def update_user_settings(
    request, data: UserSettingsSchema, authorization: str = Header(None)
):
    """更新用戶設定"""
    logger.debug(
        f"Update user settings, authorization header: {authorization[:20] if authorization else None}"
    )

    try:
        user_id = get_user_id_from_token(authorization)
        if user_id is None:
            logger.warning("Authentication failed, cannot get user ID")
            return Response({"detail": "認證失敗，無法獲取用戶ID"}, status=401)

        user = User.objects.get(id=user_id)
        settings, created = UserSetting.objects.get_or_create(user=user)

        settings.work_duration = data.work_duration
        settings.short_break_duration = data.short_break_duration
        settings.long_break_duration = data.long_break_duration
        settings.long_break_interval = data.long_break_interval
        settings.notifications_enabled = data.notifications_enabled
        settings.save()

        logger.info(f"User settings updated: {user.id}")
        return {
            "work_duration": settings.work_duration,
            "short_break_duration": settings.short_break_duration,
            "long_break_duration": settings.long_break_duration,
            "long_break_interval": settings.long_break_interval,
            "notifications_enabled": settings.notifications_enabled,
        }
    except User.DoesNotExist:
        logger.warning(f"User not found: {user_id}")
        return Response({"detail": "用戶不存在"}, status=404)
    except Exception as e:
        logger.error(f"Error updating user settings: {str(e)}")
        return Response({"detail": f"發生錯誤: {str(e)}"}, status=500)
