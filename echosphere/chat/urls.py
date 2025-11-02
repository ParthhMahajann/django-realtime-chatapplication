# chat/urls.py
from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    # Room list and management
    path('', views.room_list, name='room_list'),
    path('room/<slug:room_slug>/', views.room_detail, name='room'),
    path('room/create/', views.create_room, name='create_room'),
    path('room/<slug:room_slug>/leave/', views.leave_room, name='leave_room'),
    
    # Analytics dashboard
    path('dashboard/', views.emotion_dashboard, name='dashboard'),
    
    # API endpoints (optional - for AJAX requests)
    path('api/messages/<slug:room_slug>/', views.get_messages, name='get_messages'),
    path('api/emotion-stats/', views.get_emotion_stats, name='emotion_stats'),
]
