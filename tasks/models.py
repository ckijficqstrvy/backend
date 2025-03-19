from django.db import models
from users.models import User

# Create your models here.


class Category(models.Model):
    """任務分類"""

    name = models.CharField(max_length=100)
    color_code = models.CharField(max_length=20, default="#e53e3e")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="categories")

    class Meta:
        verbose_name = "分類"
        verbose_name_plural = "分類"

    def __str__(self):
        return self.name


class Tag(models.Model):
    """任務標籤"""

    name = models.CharField(max_length=50)
    color_code = models.CharField(max_length=20, default="#3b82f6")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tags")

    class Meta:
        verbose_name = "標籤"
        verbose_name_plural = "標籤"

    def __str__(self):
        return self.name


class Task(models.Model):
    """任務模型"""

    STATUS_CHOICES = (
        ("pending", "待處理"),
        ("in_progress", "進行中"),
        ("completed", "已完成"),
    )

    PRIORITY_CHOICES = (
        ("low", "低"),
        ("medium", "中"),
        ("high", "高"),
    )

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    priority = models.CharField(
        max_length=10, choices=PRIORITY_CHOICES, default="medium"
    )
    due_date = models.DateField(blank=True, null=True)
    estimated_pomodoros = models.PositiveIntegerField(default=1)
    completed_pomodoros = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tasks")
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="tasks"
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="tasks")

    class Meta:
        verbose_name = "任務"
        verbose_name_plural = "任務"
        ordering = ["-priority", "due_date", "created_at"]

    def __str__(self):
        return self.title
