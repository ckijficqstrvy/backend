# Generated by Django 5.1.7 on 2025-03-19 17:46

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('color_code', models.CharField(default='#e53e3e', max_length=20)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='categories', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': '分類',
                'verbose_name_plural': '分類',
            },
        ),
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
                ('color_code', models.CharField(default='#3b82f6', max_length=20)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tags', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': '標籤',
                'verbose_name_plural': '標籤',
            },
        ),
        migrations.CreateModel(
            name='Task',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True, null=True)),
                ('status', models.CharField(choices=[('pending', '待處理'), ('in_progress', '進行中'), ('completed', '已完成')], default='pending', max_length=20)),
                ('priority', models.CharField(choices=[('low', '低'), ('medium', '中'), ('high', '高')], default='medium', max_length=10)),
                ('due_date', models.DateField(blank=True, null=True)),
                ('estimated_pomodoros', models.PositiveIntegerField(default=1)),
                ('completed_pomodoros', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tasks', to='tasks.category')),
                ('tags', models.ManyToManyField(blank=True, related_name='tasks', to='tasks.tag')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tasks', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': '任務',
                'verbose_name_plural': '任務',
                'ordering': ['-priority', 'due_date', 'created_at'],
            },
        ),
    ]
