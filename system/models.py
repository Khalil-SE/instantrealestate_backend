from django.db import models

# Create your models here.
class SystemSettings(models.Model):
    """
    Model to store system-wide settings.
    """
    admin_chatBot_key = models.TextField(blank=True, null=True)  # For admins only
    chatbot_create_user_url = models.URLField(blank=True, null=True)
    chatbot_create_account_url = models.URLField(blank=True, null=True)


   
    stripe_api_key = models.TextField(blank=True, null=True)
    stripe_webhook_secret = models.TextField(blank=True, null=True)
    stripe_return_url = models.URLField(blank=True, null=True) # URL to redirect after payment

    instabot_ai_prompt = models.TextField(null=True, blank=True)

    


    def save(self, *args, **kwargs):
        self.pk = 1  # ensure singleton
        super().save(*args, **kwargs)
        
    @classmethod
    def get_solo(cls):
        return cls.objects.get_or_create(pk=1)[0]

    def __str__(self):
        return "System Settings"
    


class ChatbotIntegrationLog(models.Model):
    user_email = models.EmailField()
    chatbot_user_id = models.CharField(max_length=255, blank=True, null=True)
    action = models.CharField(max_length=50)  # e.g. "create_user", "create_account"
    status_code = models.IntegerField()
    success = models.BooleanField(default=False)
    response_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.action.upper()}] {self.user_email} - {'Success' if self.success else 'Failure'}"