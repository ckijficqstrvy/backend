from django.db import models
from tasks.models import Task
from users.models import User

# Create your models here.


class PomodoroSession(models.Model):
    """番茄鐘工作階段"""

    SESSION_TYPES = (
        ("work", "工作"),
        ("short_break", "短休息"),
        ("long_break", "長休息"),
    )

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="pomodoro_sessions"
    )
    task = models.ForeignKey(
        Task,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pomodoro_sessions",
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    duration = models.PositiveIntegerField(help_text="持續時間(秒)")
    type = models.CharField(max_length=15, choices=SESSION_TYPES)
    is_completed = models.BooleanField(default=False)

    class Meta:
        verbose_name = "番茄鐘階段"
        verbose_name_plural = "番茄鐘階段"
        ordering = ["-start_time"]

    def __str__(self):
        task_name = self.task.title if self.task else "無關聯任務"
        return f"{self.get_type_display()} - {task_name} ({self.start_time.strftime('%Y-%m-%d %H:%M')})"
