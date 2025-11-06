# chat/views.py
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Q, Avg
from django.utils.text import slugify
from django.utils import timezone
from datetime import timedelta
from .models import Room, Message, RoomMembership, EmotionLog
from .forms import RoomCreateForm


@login_required
def room_list(request):
    """Display list of available chat rooms"""
    # Get rooms where user is a member
    user_rooms = Room.objects.filter(
        members=request.user,
        is_active=True
    ).annotate(
        message_count=Count('messages')
    ).order_by('-updated_at')
    
    # Get public rooms user can join
    public_rooms = Room.objects.filter(
        room_type='public',
        is_active=True
    ).exclude(
        members=request.user
    ).annotate(
        message_count=Count('messages')
    )[:10]
    
    context = {
        'user_rooms': user_rooms,
        'public_rooms': public_rooms,
    }
    return render(request, 'chat/room_list.html', context)


@login_required
def room_detail(request, room_slug):
    """Display chat room interface"""
    room = get_object_or_404(Room, slug=room_slug, is_active=True)
    
    # Check if user is member of the room
    is_member = RoomMembership.objects.filter(room=room, user=request.user).exists()
    
    # If not a member and room is not public, redirect
    if not is_member:
        if room.room_type == 'public':
            # Auto-join public rooms
            room.add_member(request.user)
            messages.success(request, f'You joined {room.name}')
        else:
            messages.error(request, 'You do not have access to this room.')
            return redirect('chat:room_list')
    
    # Get room members
    members = room.members.select_related('profile').all()
    
    # Get user's membership details
    try:
        membership = RoomMembership.objects.get(room=room, user=request.user)
    except RoomMembership.DoesNotExist:
        membership = None
    
    context = {
        'room': room,
        'members': members,
        'membership': membership,
        'room_slug_json': json.dumps(room_slug),
    }
    return render(request, 'chat/room.html', context)


@login_required
def create_room(request):
    """Create a new chat room"""
    if request.method == 'POST':
        form = RoomCreateForm(request.POST)
        if form.is_valid():
            room = form.save(commit=False)
            room.created_by = request.user
            
            # Generate unique slug
            base_slug = slugify(room.name)
            slug = base_slug
            counter = 1
            while Room.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            room.slug = slug
            
            room.save()
            
            # Add creator as admin member
            room.add_member(request.user, role='admin')
            
            messages.success(request, f'Room "{room.name}" created successfully!')
            return redirect('chat:room', room_slug=room.slug)
    else:
        form = RoomCreateForm()
    
    context = {'form': form}
    return render(request, 'chat/create_room.html', context)


@login_required
def leave_room(request, room_slug):
    """Leave a chat room"""
    room = get_object_or_404(Room, slug=room_slug)
    
    if request.method == 'POST':
        if room.remove_member(request.user):
            messages.success(request, f'You left {room.name}')
        else:
            messages.error(request, 'You are not a member of this room.')
    
    return redirect('chat:room_list')


@login_required
def emotion_dashboard(request):
    """Display emotion analytics dashboard"""
    # Get date range (default: last 30 days)
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)
    
    # Get user's emotion logs
    emotion_logs = EmotionLog.objects.filter(
        user=request.user,
        analyzed_at__gte=start_date
    )
    
    # Get emotion distribution
    emotion_stats = Message.objects.filter(
        sender=request.user,
        timestamp__gte=start_date
    ).values('emotion').annotate(
        count=Count('emotion')
    ).order_by('-count')
    
    # Get daily emotion trends
    daily_emotions = Message.objects.filter(
        sender=request.user,
        timestamp__gte=start_date
    ).extra(
        select={'date': 'DATE(timestamp)'}
    ).values('date', 'emotion').annotate(
        count=Count('emotion')
    ).order_by('date')
    
    # Calculate statistics
    total_messages = Message.objects.filter(
        sender=request.user,
        timestamp__gte=start_date
    ).count()
    
    # Get most common emotion
    most_common_emotion = emotion_stats.first() if emotion_stats else None
    
    # Average sentiment polarity
    avg_sentiment = Message.objects.filter(
        sender=request.user,
        timestamp__gte=start_date
    ).aggregate(Avg('sentiment_polarity'))
    
    # Get emotion breakdown percentages
    emotion_percentages = {}
    if total_messages > 0:
        for stat in emotion_stats:
            emotion_percentages[stat['emotion']] = round((stat['count'] / total_messages) * 100, 1)
    
    context = {
        'emotion_stats': json.dumps(list(emotion_stats)),
        'daily_emotions': json.dumps(list(daily_emotions), default=str),
        'total_messages': total_messages,
        'most_common_emotion': most_common_emotion,
        'avg_sentiment': avg_sentiment['sentiment_polarity__avg'] or 0,
        'emotion_percentages': emotion_percentages,
        'days': days,
    }
    return render(request, 'chat/dashboard.html', context)


@login_required
def get_messages(request, room_slug):
    """API endpoint to get messages for a room"""
    room = get_object_or_404(Room, slug=room_slug)
    
    # Check membership
    if not RoomMembership.objects.filter(room=room, user=request.user).exists():
        return JsonResponse({'error': 'Not a member'}, status=403)
    
    # Get messages
    limit = int(request.GET.get('limit', 50))
    messages_qs = Message.objects.filter(
        room=room,
        is_deleted=False
    ).select_related('sender', 'sender__profile').order_by('-timestamp')[:limit]
    
    messages_data = [
        {
            'id': msg.id,
            'content': msg.content,
            'sender': msg.sender.username,
            'sender_avatar': msg.sender.profile.avatar.url if msg.sender.profile.avatar else '/static/images/default-avatar.png',
            'timestamp': msg.timestamp.isoformat(),
            'emotion': msg.emotion,
            'emotion_emoji': msg.emotion_emoji,
            'emotion_confidence': msg.emotion_confidence,
            'time_display': msg.time_since_sent,
        }
        for msg in reversed(messages_qs)
    ]
    
    return JsonResponse({'messages': messages_data})


@login_required
def get_emotion_stats(request):
    """API endpoint to get emotion statistics"""
    days = int(request.GET.get('days', 7))
    start_date = timezone.now() - timedelta(days=days)
    
    stats = Message.objects.filter(
        sender=request.user,
        timestamp__gte=start_date
    ).values('emotion').annotate(
        count=Count('emotion')
    )
    
    return JsonResponse({'stats': list(stats)})
