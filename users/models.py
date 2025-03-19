from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models


class User(AbstractUser):
    """自定義使用者模型"""

    profile_picture = models.ImageField(
        upload_to="profile_pictures/", null=True, blank=True
    )

    # 修改 groups 和 user_permissions 的 related_name
    groups = models.ManyToManyField(
        Group,
        verbose_name="groups",
        blank=True,
        help_text="The groups this user belongs to.",
        related_name="user_custom_set",  # 修改 related_name
        related_query_name="user",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name="user permissions",
        blank=True,
        help_text="Specific permissions for this user.",
        related_name="user_custom_set",  # 修改 related_name
        related_query_name="user",
    )

    class Meta:
        verbose_name = "使用者"
        verbose_name_plural = "使用者"

    def __str__(self):
        return self.username


class UserSetting(models.Model):
    """使用者設定"""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="settings")
    work_duration = models.IntegerField(default=25 * 60)  # 預設工作時長 (秒)
    short_break_duration = models.IntegerField(default=5 * 60)  # 預設短休息時長 (秒)
    long_break_duration = models.IntegerField(default=15 * 60)  # 預設長休息時長 (秒)
    long_break_interval = models.IntegerField(default=4)  # 多少番茄鐘後長休息
    notifications_enabled = models.BooleanField(default=True)  # 是否啟用通知

    def __str__(self):
        return f"{self.user.username}的設定"
