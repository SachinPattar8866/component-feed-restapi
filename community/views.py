from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from django.db.models import Count, Q, F
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from .models import User, Post, Comment, Like
from .serializers import (
    UserSerializer, PostSerializer, CommentSerializer,
    LeaderboardUserSerializer
)

class PostViewSet(viewsets.ModelViewSet):
    """ViewSet for posts with optimized queries"""
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        """
        Optimized queryset that prevents N+1 queries.
        Loads posts + authors + comments in just 3 queries
        """
        return Post.objects.select_related('author').prefetch_related(
            'comments__author',
            'comments__replies__author',
        )
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def like(self, request, pk=None):
        """Like a post with race condition handling"""
        post = self.get_object()
        
        with transaction.atomic():
            like, created = Like.objects.get_or_create(
                user=request.user,
                post=post
            )
            
            if created:
                return Response({
                    'status': 'liked',
                    'like_count': post.likes.count()
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    'status': 'already_liked',
                    'like_count': post.likes.count()
                }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def unlike(self, request, pk=None):
        """Unlike a post"""
        post = self.get_object()
        
        with transaction.atomic():
            deleted, _ = Like.objects.filter(
                user=request.user,
                post=post
            ).delete()
            
            if deleted:
                return Response({
                    'status': 'unliked',
                    'like_count': post.likes.count()
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'status': 'not_liked',
                    'like_count': post.likes.count()
                }, status=status.HTTP_200_OK)


class CommentViewSet(viewsets.ModelViewSet):
    """ViewSet for comments"""
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        """Optimized queryset with author prefetch"""
        return Comment.objects.select_related('author', 'post').prefetch_related(
            'replies__author'
        )
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def like(self, request, pk=None):
        """Like a comment with race condition handling"""
        comment = self.get_object()
        
        with transaction.atomic():
            like, created = Like.objects.get_or_create(
                user=request.user,
                comment=comment
            )
            
            if created:
                return Response({
                    'status': 'liked',
                    'like_count': comment.likes.count()
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    'status': 'already_liked',
                    'like_count': comment.likes.count()
                }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def unlike(self, request, pk=None):
        """Unlike a comment"""
        comment = self.get_object()
        
        with transaction.atomic():
            deleted, _ = Like.objects.filter(
                user=request.user,
                comment=comment
            ).delete()
            
            if deleted:
                return Response({
                    'status': 'unliked',
                    'like_count': comment.likes.count()
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'status': 'not_liked',
                    'like_count': comment.likes.count()
                }, status=status.HTTP_200_OK)


class LeaderboardViewSet(viewsets.ViewSet):
    """Leaderboard ViewSet with complex 24-hour aggregation"""
    
    @action(detail=False, methods=['get'])
    def top_users(self, request):
        """
        Get top 5 users by karma in last 24 hours.
        Calculates dynamically from Like history.
        """
        cutoff_time = timezone.now() - timedelta(hours=24)
        
        # This is the critical query for the leaderboard
        top_users = User.objects.annotate(
            # Count post likes in last 24h and multiply by 5
            post_karma=Count(
                'posts__likes',
                filter=Q(
                    posts__likes__created_at__gte=cutoff_time,
                ),
                distinct=True
            ) * 5,
            # Count comment likes in last 24h (worth 1 point each)
            comment_karma=Count(
                'comments__likes',
                filter=Q(
                    comments__likes__created_at__gte=cutoff_time,
                ),
                distinct=True
            ),
            # Total karma is sum of both
            karma_24h=F('post_karma') + F('comment_karma')
        ).filter(
            karma_24h__gt=0  # Only show users with karma
        ).order_by('-karma_24h')[:5]
        
        serializer = LeaderboardUserSerializer(top_users, many=True)
        return Response(serializer.data)


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Login endpoint that returns JWT tokens.
    POST /api/token/ with username and password to get access token.
    """
    permission_classes = [AllowAny]


class RegisterView(APIView):
    """Public endpoint to register a new user.

    POST /api/users/ with {username, email, password} creates a new user.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # Return sanitized user data (password excluded by serializer)
            return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST) 