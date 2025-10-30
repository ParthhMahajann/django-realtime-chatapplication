 # users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Profile
class ProfileInline(admin.StackedInline):
    """Inline profile editing in user admin"""
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'
    fields = ('bio', 'location', 'birth_date', 'avatar', 'show_emotions', 'emotion_sensitons')
class UserAdmin(BaseUserAdmin):
    """Extended user admin with profile"""
    inlines = (ProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'date_joining')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined')
 # Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """Profile admin interface"""
    list_display = ('user', 'location', 'show_emotions', 'emotion_sensitivity', 'created_by')
    list_filter = ('show_emotions', 'emotion_sensitivity', 'created_at')
    search_fields = ('user__username', 'user__email', 'location')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Profile Details', {
            'fields': ('bio', 'location', 'birth_date', 'avatar')
        }),
        ('Emotion Settings', {
            'fields': ('show_emotions', 'emotion_sensitivity')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )