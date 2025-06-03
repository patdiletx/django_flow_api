from django.urls import path
from .views import BlogPostListView, BlogPostDetailView

app_name = 'blog'

urlpatterns = [
    path('posts/', BlogPostListView.as_view(), name='blogpost-list'),
    path('posts/<slug:slug>/', BlogPostDetailView.as_view(), name='blogpost-detail'),
]