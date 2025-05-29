# instabot/models.py

from django.db import models
from django.db.models import SET_NULL
from django.contrib.auth import get_user_model
from shared.models import Keyword

User = get_user_model()

class PublicReplyTemplate(models.Model):
    name = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="public_reply_templates")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class PublicReplyContent(models.Model):
    template = models.ForeignKey(PublicReplyTemplate, on_delete=models.CASCADE, related_name='replies')
    text = models.TextField()

    def __str__(self):
        return f"Reply in template: {self.template.name}"

class InstaBot(models.Model):
    MESSAGE_TYPE_CHOICES = (
        ('text', 'Text Only'),
        ('image', 'With Image'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # keyword = models.OneToOneField(Keyword, on_delete=models.CASCADE)  # Unique per bot
    keyword = models.OneToOneField(Keyword, on_delete=models.SET_NULL, null=True, blank=True, related_name='instabot')

    status = models.CharField(max_length=50, default="active")
    
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPE_CHOICES, default="text")
    image_url = models.URLField(blank=True, null=True)

    title = models.CharField(max_length=255)
    message = models.TextField()

    button1_text = models.CharField(max_length=50, null=True, blank=True)
    button1_url = models.URLField(blank=True)
    button2_text = models.CharField(max_length=50, null=True, blank=True)
    button2_url = models.URLField(blank=True)
    button3_text = models.CharField(max_length=50, null=True, blank=True)
    button3_url = models.URLField(blank=True)

    public_reply_template = models.ForeignKey(PublicReplyTemplate, null=True, blank=True, on_delete=models.SET_NULL)
    ai_post_description = models.TextField()

    

    comment_count = models.PositiveIntegerField(default=0)
    click_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"InstaBot - {self.keyword.text}"