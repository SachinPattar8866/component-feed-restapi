from rest_framework import serializers
from .models import User, Post, Comment, Like


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user creation and read operations.

    Includes a write-only `password` so the API can safely accept a password
    and call `set_password` on create (avoids storing raw password).
    """
    karma_24h = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        # expose password for write only so registration can set it
        fields = ['id', 'username', 'email', 'password', 'karma_24h']
        extra_kwargs = {
            'password': {'write_only': True}
        }
        read_only_fields = ['karma_24h']
    
    def create(self, validated_data):
        # Remove password before creating model via ModelSerializer.create
        password = validated_data.pop('password', None)
        user = super().create(validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user
    
    def get_karma_24h(self, obj):
        """Get karma from last 24 hours"""
        return obj.get_24h_karma()


class LeaderboardUserSerializer(serializers.ModelSerializer):
    """Optimized serializer for leaderboard with pre-calculated karma"""
    karma_24h = serializers.IntegerField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'karma_24h']

class RecursiveCommentSerializer(serializers.ModelSerializer):
    """Recursive serializer for nested comments"""
    author = serializers.StringRelatedField()
    author_id = serializers.IntegerField(source='author.id', read_only=True)
    replies = serializers.SerializerMethodField()
    like_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    
    class Meta:
        model = Comment
        fields = [
            'id', 'content', 'author', 'author_id', 
            'created_at', 'like_count', 'replies', 'is_liked'
        ]
    
    def get_replies(self, obj):
        """Serialize child comments recursively"""
        if hasattr(obj, 'get_children'):
            children = obj.get_children()
            return RecursiveCommentSerializer(
                children, 
                many=True, 
                context=self.context
            ).data
        return []
    
    def get_like_count(self, obj):
        """Get like count for this comment"""
        if hasattr(obj, 'like_count') and isinstance(obj.like_count, int):
            return obj.like_count
        return obj.likes.count()
    
    def get_is_liked(self, obj):
        """Check if current user has liked this comment"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Like.objects.filter(
                user=request.user,
                comment=obj
            ).exists()
        return False


class CommentSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating comments"""
    author = serializers.StringRelatedField(read_only=True)
    author_id = serializers.IntegerField(source='author.id', read_only=True)
    like_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    
    class Meta:
        model = Comment
        fields = [
            'id', 'post', 'parent', 'content', 
            'author', 'author_id', 'created_at', 'like_count', 'is_liked'
        ]
        read_only_fields = ['author', 'created_at', 'like_count']
    
    def get_like_count(self, obj):
        """Get like count for this comment"""
        if hasattr(obj, 'like_count') and isinstance(obj.like_count, int):
            return obj.like_count
        return obj.likes.count()
    
    def get_is_liked(self, obj):
        """Check if current user has liked this comment"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Like.objects.filter(
                user=request.user,
                comment=obj
            ).exists()
        return False
    
    def create(self, validated_data):
        """Set author from request user"""
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)


class PostSerializer(serializers.ModelSerializer):
    """Post serializer with optimized comment loading"""
    author = serializers.StringRelatedField(read_only=True)
    author_id = serializers.IntegerField(source='author.id', read_only=True)
    like_count = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Post
        fields = [
            'id', 'content', 'author', 'author_id',
            'created_at', 'like_count', 'comments', 
            'is_liked', 'comment_count'
        ]
        read_only_fields = ['author', 'created_at', 'like_count']
    
    def get_comments(self, obj):
        """Get threaded comments efficiently"""
        from mptt.templatetags.mptt_tags import cache_tree_children
        
        # Get all comments for this post (already prefetched in viewset)
        comments = obj.comments.all()
        
        # Cache the tree structure in memory
        root_comments = cache_tree_children(comments)
        
        # Serialize with recursive structure
        return RecursiveCommentSerializer(
            root_comments,
            many=True,
            context=self.context
        ).data
    
    def get_like_count(self, obj):
        """Get like count for this post"""
        if hasattr(obj, 'like_count') and isinstance(obj.like_count, int):
            return obj.like_count
        return obj.likes.count()
    
    def get_is_liked(self, obj):
        """Check if current user has liked this post"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Like.objects.filter(
                user=request.user,
                post=obj
            ).exists()
        return False
    
    def get_comment_count(self, obj):
        """Get total comment count"""
        return obj.comments.count()
    
    def create(self, validated_data):
        """Set author from request user"""
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)