from django.contrib import admin
from mptt.admin import MPTTModelAdmin
from .models import User, Post, Comment, Like


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'is_staff']
    search_fields = ['username', 'email']


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['id', 'author', 'content_preview', 'like_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['content', 'author__username']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content


@admin.register(Comment)
class CommentAdmin(MPTTModelAdmin):
    list_display = ['id', 'author', 'post', 'parent', 'content_preview', 'created_at']
    list_filter = ['created_at']
    search_fields = ['content', 'author__username']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'post', 'comment', 'created_at']
    list_filter = ['created_at']