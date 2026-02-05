from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from mptt.models import MPTTModel, TreeForeignKey
from datetime import timedelta


class User(AbstractUser):
    """Extended User model with karma tracking"""
    
    def get_24h_karma(self):
        """Calculate karma earned in last 24 hours dynamically."""
        cutoff_time = timezone.now() - timedelta(hours=24)
        
        # Karma from post likes (5 points each)
        post_karma = Like.objects.filter(
            post__author=self,
            created_at__gte=cutoff_time,
            comment__isnull=True
        ).count() * 5
        
        # Karma from comment likes (1 point each)
        comment_karma = Like.objects.filter(
            comment__author=self,
            created_at__gte=cutoff_time,
            post__isnull=True
        ).count()
        
        return post_karma + comment_karma


class Post(models.Model):
    """Post model with author and content"""
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"Post by {self.author.username}: {self.content[:50]}"
    
    @property
    def like_count(self):
        """Get total likes for this post"""
        return self.likes.count()


class Comment(MPTTModel):
    """
    Threaded comment model using MPTT (Modified Preorder Tree Traversal).
    MPTT allows us to fetch entire tree in a single query.
    """
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    parent = TreeForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies'
    )
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class MPTTMeta:
        order_insertion_by = ['created_at']
    
    class Meta:
        # Remove the index that referenced tree_id and lft
        # MPTT will create its own indexes automatically
        indexes = [
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"Comment by {self.author.username} on {self.post}"
    
    @property
    def like_count(self):
        """Get total likes for this comment"""
        return self.likes.count()


class Like(models.Model):
    """
    Like model with database-level uniqueness constraint to prevent double-liking.
    This handles race conditions at the database level.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_likes')
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='likes',
        null=True,
        blank=True
    )
    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        related_name='likes',
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        # Composite unique constraint prevents double-liking at DB level
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'post'],
                condition=models.Q(post__isnull=False),
                name='unique_post_like'
            ),
            models.UniqueConstraint(
                fields=['user', 'comment'],
                condition=models.Q(comment__isnull=False),
                name='unique_comment_like'
            ),
        ]
        # Check constraint ensures like is for either post OR comment, not both
        constraints += [
            models.CheckConstraint(
                check=(
                    models.Q(post__isnull=False, comment__isnull=True) |
                    models.Q(post__isnull=True, comment__isnull=False)
                ),
                name='like_post_or_comment'
            ),
        ]
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self):
        if self.post:
            return f"{self.user.username} likes post {self.post.id}"
        return f"{self.user.username} likes comment {self.comment.id}"
    