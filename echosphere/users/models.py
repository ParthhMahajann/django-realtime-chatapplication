from django.db import models
from django.contrib.auth.models import User
from PIL import Image
class Profile(models.Model):
     """Extended user profile with additional fields"""
     user = models.OneToOneField(User, on_delete=models.CASCADE)
     bio = models.TextField(max_length=500, blank=True, help_text="Tell us about yourself"
     location = models.CharField(max_length=30, blank=True
     birth_date = models.DateField(null=True, blank=True)
     avatar = models.ImageField(
        upload_to='profile_pics/', 
        default='profile_pics/default.jpg',
        help_text="Upload a profile picture"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Emotion preferences
    show_emotions = models.BooleanField(
        default=True, 
        help_text="Show emotion indicators in chat"
    )
    emotion_sensitivity = models.CharField(
        max_length=10,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
        ],
        default='medium',
        help_text="Emotion detection sensitivity"
    )
    
    class Meta:
        db_table = 'user_profiles'
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
    
    def __str__(self):
        return f"{self.user.username}'s Profile"
    
    def save(self, *args, **kwargs):
        """Override save to resize images"""
        super().save(*args, **kwargs)
        
        # Resize image if it's too large
        if self.avatar:
            img = Image.open(self.avatar.path)
            if img.height &gt; 300 or img.width &gt; 300:
                output_size = (300, 300)
                img.thumbnail(output_size)
                img.save(self.avatar.path)
 # Signal to create profile when user is created
from django.db.models.signals import post_save
from django.dispatch import receiver
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create profile when user is created"""
    if created:
        Profile.objects.create(user=instance)
@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save profile when user is saved"""
    instance.profile.save()