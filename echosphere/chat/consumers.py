# chat/consumers.py
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Room, Message, RoomMembership, EmotionLog
from .emotion_analyzer import EmotionAnalyzer
from datetime import datetime

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time chat"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.room_slug = None
        self.room_group_name = None
        self.room = None
        self.user = None
        self.emotion_analyzer = EmotionAnalyzer()
    
    async def connect(self):
        """Handle WebSocket connection"""
        self.room_slug = self.scope['url_route']['kwargs']['room_slug']
        self.room_group_name = f'chat_{self.room_slug}'
        self.user = self.scope['user']
        
        # Check if user is authenticated
        if not self.user.is_authenticated:
            await self.close()
            return
        
        # Get room and check permissions
        self.room = await self.get_room(self.room_slug)
        if not self.room:
            await self.close()
            return
        
        # Check if user is member of the room
        is_member = await self.check_room_membership(self.room, self.user)
        if not is_member:
            await self.close()
            return
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        # Accept WebSocket connection
        await self.accept()
        
        # Send recent messages to the newly connected user
        await self.send_recent_messages()
        
        # Notify room that user joined
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_joined',
                'user': self.user.username,
                'timestamp': timezone.now().isoformat()
            }
        )
        
        logger.info(f"User {self.user.username} connected to room {self.room_slug}")
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if self.room_group_name:
            # Notify room that user left
            if self.user and self.user.is_authenticated:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'user_left',
                        'user': self.user.username,
                        'timestamp': timezone.now().isoformat()
                    }
                )
            
            # Leave room group
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
            
            logger.info(f"User {self.user.username if self.user else 'Unknown'} disconnected from room {self.room_slug}")
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type', 'message')
            
            if message_type == 'message':
                await self.handle_chat_message(text_data_json)
            elif message_type == 'typing':
                await self.handle_typing_indicator(text_data_json)
            elif message_type == 'read_receipt':
                await self.handle_read_receipt(text_data_json)
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received: {text_data}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    async def handle_chat_message(self, data):
        """Process chat message with emotion analysis"""
        message_content = data.get('message', '').strip()
        
        if not message_content:
            return
        
        # Analyze emotion
        emotion_result = self.emotion_analyzer.analyze(message_content)
        
        # Save message to database
        message = await self.save_message(
            room=self.room,
            sender=self.user,
            content=message_content,
            emotion=emotion_result['emotion'],
            emotion_confidence=emotion_result['confidence'],
            sentiment_polarity=emotion_result['polarity'],
            sentiment_subjectivity=emotion_result['subjectivity']
        )
        
        # Save detailed emotion log for analytics
        await self.save_emotion_log(message, emotion_result)
        
        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': {
                    'id': message.id,
                    'content': message.content,
                    'sender': message.sender.username,
                    'sender_avatar': message.sender.profile.avatar.url if message.sender.profile.avatar else '/static/images/default-avatar.png',
                    'timestamp': message.timestamp.isoformat(),
                    'emotion': message.emotion,
                    'emotion_emoji': message.emotion_emoji,
                    'emotion_confidence': message.emotion_confidence,
                    'time_display': message.time_since_sent
                }
            }
        )
    
    async def handle_typing_indicator(self, data):
        """Handle typing indicator"""
        is_typing = data.get('is_typing', False)
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'user': self.user.username,
                'is_typing': is_typing
            }
        )
    
    async def handle_read_receipt(self, data):
        """Handle read receipt"""
        await self.update_last_read_timestamp()
    
    # WebSocket event handlers
    async def chat_message(self, event):
        """Send chat message to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message']
        }))
    
    async def user_joined(self, event):
        """Handle user joined event"""
        await self.send(text_data=json.dumps({
            'type': 'user_joined',
            'user': event['user'],
            'timestamp': event['timestamp']
        }))
    
    async def user_left(self, event):
        """Handle user left event"""
        await self.send(text_data=json.dumps({
            'type': 'user_left',
            'user': event['user'],
            'timestamp': event['timestamp']
        }))
    
    async def typing_indicator(self, event):
        """Handle typing indicator"""
        # Don't send typing indicator to the sender
        if event['user'] != self.user.username:
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'user': event['user'],
                'is_typing': event['is_typing']
            }))
    
    async def send_recent_messages(self):
        """Send recent messages to newly connected user"""
        messages = await self.get_recent_messages(self.room)
        
        for message in messages:
            await self.send(text_data=json.dumps({
                'type': 'message',
                'message': {
                    'id': message.id,
                    'content': message.content,
                    'sender': message.sender.username,
                    'sender_avatar': message.sender.profile.avatar.url if message.sender.profile.avatar else '/static/images/default-avatar.png',
                    'timestamp': message.timestamp.isoformat(),
                    'emotion': message.emotion,
                    'emotion_emoji': message.emotion_emoji,
                    'emotion_confidence': message.emotion_confidence,
                    'time_display': message.time_since_sent
                }
            }))
    
    # Database operations
    @database_sync_to_async
    def get_room(self, room_slug):
        """Get room by slug"""
        try:
            return Room.objects.get(slug=room_slug, is_active=True)
        except Room.DoesNotExist:
            return None
    
    @database_sync_to_async
    def check_room_membership(self, room, user):
        """Check if user is member of room"""
        return RoomMembership.objects.filter(room=room, user=user).exists()
    
    @database_sync_to_async
    def save_message(self, room, sender, content, emotion, emotion_confidence, sentiment_polarity, sentiment_subjectivity):
        """Save message to database"""
        return Message.objects.create(
            room=room,
            sender=sender,
            content=content,
            emotion=emotion,
            emotion_confidence=emotion_confidence,
            sentiment_polarity=sentiment_polarity,
            sentiment_subjectivity=sentiment_subjectivity
        )
    
    @database_sync_to_async
    def save_emotion_log(self, message, emotion_result):
        """Save detailed emotion analysis for analytics"""
        now = timezone.now()
        pattern_scores = emotion_result.get('pattern_scores', {})
        
        return EmotionLog.objects.create(
            user=message.sender,
            message=message,
            happy_score=pattern_scores.get('happy', 0),
            sad_score=pattern_scores.get('sad', 0),
            angry_score=pattern_scores.get('angry', 0),
            surprised_score=pattern_scores.get('surprised', 0),
            fearful_score=pattern_scores.get('fearful', 0),
            disgusted_score=pattern_scores.get('disgusted', 0),
            room_type=message.room.room_type,
            message_length=len(message.content),
            time_of_day=now.time(),
            day_of_week=now.weekday()
        )
    
    @database_sync_to_async
    def get_recent_messages(self, room, limit=50):
        """Get recent messages for room"""
        return list(
            Message.objects.filter(room=room, is_deleted=False)
            .select_related('sender', 'sender__profile')
            .order_by('-timestamp')[:limit]
        )
    
    @database_sync_to_async
    def update_last_read_timestamp(self):
        """Update user's last read timestamp for the room"""
        try:
            membership = RoomMembership.objects.get(room=self.room, user=self.user)
            membership.last_read_at = timezone.now()
            membership.save()
        except RoomMembership.DoesNotExist:
            pass
