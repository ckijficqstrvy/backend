import logging
import os
from datetime import datetime

import jwt
from django.conf import settings
from ninja import NinjaAPI
from ninja.security import HttpBearer

# 獲取日誌記錄器
logger = logging.getLogger("pomodoro_api")

# 從 .env 獲取密鑰或使用 Django settings
JWT_SECRET = os.getenv("SECRET_KEY", settings.SECRET_KEY)


class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        try:
            logger.debug(f"Authenticating token: {token[:10]}...")
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            user_id = payload.get("user_id")
            logger.debug(f"Authentication successful for user_id: {user_id}")
            return user_id
        except jwt.PyJWTError as e:
            logger.error(f"JWT Authentication error: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return None


# 創建 API 實例，先不設定全局身份驗證
api = NinjaAPI(
    title="番茄工作法 API",
    version="1.0.0",
    csrf=False,  # 禁用CSRF保護以簡化API測試
    # 不設定全局身份驗證
)


# 健康檢查端點
@api.get("/health-check")
def health_check(request):
    """健康檢查端點 - 不需要身份驗證"""
    return {"status": "ok", "message": "API is running"}


# 調試端點
@api.get("/debug")
def debug_endpoint(request):
    """調試端點 - 返回請求信息"""
    headers = {key: value for key, value in request.headers.items()}
    return {
        "method": request.method,
        "path": request.path,
        "headers": headers,
        "query_params": dict(request.GET),
        "timestamp": datetime.now().isoformat(),
    }


# 導入路由器
from pomodoro_api.routers import analytics, auth, pomodoro, tasks

# 添加路由器 - auth 路由不需要身份驗證，其他需要
api.add_router("/auth", auth.router)  # 不需要身份驗證
api.add_router("/tasks", tasks.router, auth=AuthBearer())  # 需要身份驗證
api.add_router("/pomodoro", pomodoro.router, auth=AuthBearer())  # 需要身份驗證
api.add_router("/analytics", analytics.router, auth=AuthBearer())  # 需要身份驗證


# 添加錯誤處理
@api.exception_handler(Exception)
def handle_unhandled_exception(request, exc):
    logger.exception(f"Unhandled exception: {str(exc)}")
    return api.create_response(
        request, {"detail": f"內部服務器錯誤: {str(exc)}"}, status=500
    )
