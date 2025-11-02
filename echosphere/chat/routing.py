 # chat/routing.py
 from django.urls import re_path, path
 from . import consumers
 websocket_urlpatterns = [
    path('ws/chat/&lt;str:room_slug&gt;/', consumers.ChatConsumer.as_asgi()),
 ]