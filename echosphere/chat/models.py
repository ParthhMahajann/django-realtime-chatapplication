# chat/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
class Room(models.Model):
    """Chat room model"""
    ROOM_TYPES = [
        ('private', 'Private Chat'),
        ('group', 'Group Chat'),
        ('public', 'Public Room'),
    ]
    
    name = models.CharField(max_length=100, help_text="Room display name")
    slug = models.SlugField(max_length=100, unique=True, help_text="URL-friendly room ideantifier")
    description = models.TextField(max_length=500, blank=True, help_text="Room description")
    room_type = models.CharField(max_length=10, choices=ROOM_TYPES, default='private')
    
    # Room settings
    max_members = models.PositiveIntegerField(default=50, help_text="Maximum number of members allowed")
    is_active = models.BooleanField(default=True)
    
    # Relationships
    created_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='created_rooms',
        help_text="User who created this room"
    )
    members = models.ManyToManyField(
        User, 
        through='RoomMembership',
        related_name='chat_rooms',
        help_text="Users in this room"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'chat_rooms'
        verbose_name = 'Chat Room'
        verbose_name_plural = 'Chat Rooms'
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.name} ({self.get_room_type_display()})"
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('chat:room', kwargs={'room_slug': self.slug})
    
    @property
    def member_count(self):
        """Get current number of members"""
        return self.members.count()
    
    @property
    def recent_messages(self):
        """Get recent messages (last 50)"""
        return self.messages.select_related('sender', 'sender__profile').order_by('-timestamp')[:50]
    
    def add_member(self, user, role='member'):
        """Add a user to the room"""
        membership, created = RoomMembership.objects.get_or_create(
            room=self,
            user=user,
            defaults={'role': role}
        )
        return membership, created
    
    def remove_member(self, user):
        """Remove a user from the room"""
        try:
            membership = RoomMembership.objects.get(room=self, user=user)
            membership.delete()
            return True
        except RoomMembership.DoesNotExist:
            return False
class RoomMembership(models.Model):
    """Room membership with roles"""
    ROLES = [
        ('admin', 'Admin'),
        ('moderator', 'Moderator'),
        ('member', 'Member'),
    ]
    
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='room_memberships')
    role = models.CharField(max_length=10, choices=ROLES, default='member')
    
    # Settings
    notifications_enabled = models.BooleanField(default=True)
    is_muted = models.BooleanField(default=False)
    
    # Timestamps
    joined_at = models.DateTimeField(auto_now_add=True)
    last_read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'chat_room_memberships'
        unique_together = ('room', 'user')
        verbose_name = 'Room Membership'
        verbose_name_plural = 'Room Memberships'
    
    def __str__(self):
        return f"{self.user.username} in {self.room.name} ({self.role})"
    
    @property
    def unread_count(self):
        """Get count of unread messages"""
        if not self.last_read_at:
            return self.room.messages.count()
            return self.room.messages.filter(timestamp__gt=self.last_read_at).count()
class Message(models.Model):
    """Chat message model with emotion analysis"""
    EMOTION_CHOICES = [
        ('happy', '😊 Happy'),
        ('sad', '😢 Sad'),
        ('angry', '😠 Angry'),
        ('surprised', '😲 Surprised'),
        ('fearful', '😨 Fearful'),
        ('disgusted', ' Disgusted'),
        ('neutral', '😐 Neutral'),
        ('positive', ' Positive'),
        ('negative', '😞 Negative'),
    ]
    
    # Core fields
    room = models.ForeignKey(
        Room, 
        on_delete=models.CASCADE, 
        related_name='messages',
        help_text="Room where message was sent"
    )
    sender = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='sent_messages',
        help_text="User who sent the message"
    )
    content = models.TextField(help_text="Message content")
    
    # Emotion analysis
    emotion = models.CharField(
        max_length=20, 
        choices=EMOTION_CHOICES, 
        blank=True,
        help_text="Detected emotion"
    )
    emotion_confidence = models.FloatField(
        default=0.0,
        help_text="Confidence score (0.0 to 1.0)"
    )
    sentiment_polarity = models.FloatField(
        default=0.0,
        help_text="Sentiment polarity (-1.0 to 1.0)"
    )
    sentiment_subjectivity = models.FloatField(
        default=0.0,
        help_text="Sentiment subjectivity (0.0 to 1.0)"
    )
    
    # Message metadata
    message_type = models.CharField(
        max_length=20,
        choices=[
            ('text', 'Text Message'),
                       ('image', 'Image'),
            ('file', 'File'),
            ('system', 'System Message'),
        ],
        default='text'
    )
    
    # Status fields
    is_edited = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    
    # Timestamps
    timestamp = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'chat_messages'
        verbose_name = 'Chat Message'
        verbose_name_plural = 'Chat Messages'
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['room', 'timestamp']),
            models.Index(fields=['sender', 'timestamp']),
            models.Index(fields=['emotion']),
        ]
    
    def __str__(self):
        return f"{self.sender.username}: {self.content[:50]}..."
    
    @property
    def emotion_emoji(self):
        """Get emoji for emotion"""
        emotion_emojis = {
            'happy': '😊',
            'sad': '😢',
            'angry': '😠',
            'surprised': '😲',
            'fearful': '😨',
            'disgusted': '',
            'neutral': '😐',
            'positive': '',
            'negative': '😞',
        }
        return emotion_emojis.get(self.emotion, '😐')
    
    @property
    def time_since_sent(self):
        """Get human-readable time since message was sent"""
        now = timezone.now()
        diff = now - self.timestamp
        
        if diff > timedelta(minutes=1):
            return "Just now"
        elif diff > timedelta(hours=1):
            minutes = int(diff.total_seconds() / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif diff > timedelta(days=1):
            hours = int(diff.total_seconds() / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff > timedelta(days=7):
            days = diff.days
            return f"{days} day{'s' if days != 1 else ''} ago"
        else:
            return self.timestamp.strftime("%b %d, %Y")
    
    def save(self, *args, **kwargs):
        """Override save to update room timestamp"""
        super().save(*args, **kwargs)
        # Update room's updated_at when a message is sent
        Room.objects.filter(id=self.room.id).update(updated_at=self.timestamp)
class EmotionLog(models.Model):
    """Log of emotion analysis for analytics"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='emotion_logs')
    message = models.OneToOneField(Message, on_delete=models.CASCADE, related_name='emotion_log')
    
    # Detailed emotion scores
    happy_score = models.FloatField(default=0.0)
    sad_score = models.FloatField(default=0.0)
    angry_score = models.FloatField(default=0.0)
    surprised_score = models.FloatField(default=0.0)
    fearful_score = models.FloatField(default=0.0)
    disgusted_score = models.FloatField(default=0.0)
    
    # Context
    room_type = models.CharField(max_length=20)
    message_length = models.PositiveIntegerField()
    time_of_day = models.TimeField()
    day_of_week = models.PositiveSmallIntegerField()  # 0=Monday, 6=Sunday
    
    # Timestamps
    analyzed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'emotion_logs'
        verbose_name = 'Emotion Log'
        verbose_name_plural = 'Emotion Logs'
        indexes = [
            models.Index(fields=['user', 'analyzed_at']),
            models.Index(fields=['room_type']),
        ]
    
    def __str__(self):
        return f"Emotion log for {self.user.username} - {self.message.emotion}"