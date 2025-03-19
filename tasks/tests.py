# tasks/tests.py
import json

from django.test import TestCase
from users.models import User

from tasks.models import Category, Tag, Task


class TasksAPITest(TestCase):
    def setUp(self):
        """設置測試環境"""
        # 創建測試用戶
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpassword"
        )

        # 創建測試分類
        self.category = Category.objects.create(
            name="工作", color_code="#e53e3e", user=self.user
        )

        # 創建測試標籤
        self.tag = Tag.objects.create(name="重要", color_code="#3b82f6", user=self.user)

        # 創建測試任務
        self.task = Task.objects.create(
            title="測試任務",
            description="這是一個測試任務",
            status="pending",
            priority="high",
            estimated_pomodoros=3,
            user=self.user,
            category=self.category,
        )
        self.task.tags.add(self.tag)

        # 獲取認證令牌
        import os
        from datetime import datetime, timedelta

        import jwt
        from django.conf import settings

        # 創建一個 JWT 令牌
        payload = {
            "user_id": self.user.id,
            "exp": datetime.utcnow() + timedelta(days=1),
        }
        self.token = jwt.encode(
            payload, os.getenv("SECRET_KEY", settings.SECRET_KEY), algorithm="HS256"
        )

    def test_list_tasks(self):
        """測試獲取任務列表"""
        response = self.client.get(
            "/api/tasks/", HTTP_AUTHORIZATION=f"Bearer {self.token}"
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data), 1)

    def test_get_task(self):
        """測試獲取特定任務"""
        response = self.client.get(
            f"/api/tasks/{self.task.id}", HTTP_AUTHORIZATION=f"Bearer {self.token}"
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["title"], "測試任務")

    def test_create_task(self):
        """測試創建任務"""
        task_data = {
            "title": "新測試任務",
            "description": "這是一個新的測試任務",
            "priority": "medium",
            "estimated_pomodoros": 2,
            "category_id": self.category.id,
            "tag_ids": [self.tag.id],
        }

        response = self.client.post(
            "/api/tasks/",
            data=json.dumps(task_data),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["title"], "新測試任務")
        self.assertEqual(Task.objects.count(), 2)

    def test_update_task(self):
        """測試更新任務"""
        update_data = {"title": "已更新的測試任務", "status": "in_progress"}

        response = self.client.put(
            f"/api/tasks/{self.task.id}",
            data=json.dumps(update_data),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["title"], "已更新的測試任務")
        self.assertEqual(data["status"], "in_progress")

    def test_delete_task(self):
        """測試刪除任務"""
        response = self.client.delete(
            f"/api/tasks/{self.task.id}", HTTP_AUTHORIZATION=f"Bearer {self.token}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Task.objects.count(), 0)

    def test_list_categories(self):
        """測試獲取分類列表"""
        response = self.client.get(
            "/api/tasks/categories/", HTTP_AUTHORIZATION=f"Bearer {self.token}"
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "工作")
