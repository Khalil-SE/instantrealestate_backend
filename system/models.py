# system/models.py
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

# Create your models here.
class SystemSettings(models.Model):
    """
    Model to store system-wide settings.
    """

    

    admin_chatBot_key = models.TextField(blank=True, null=True)  # For admins only
    chatbot_create_user_url = models.URLField(blank=True, null=True)
    chatbot_create_account_url = models.URLField(blank=True, null=True)


    # Stripe check out integration fields
    # stripe_api_key = strip_sceret_key
    stripe_api_key = models.TextField(blank=True, null=True)
    stripe_webhook_secret = models.TextField(blank=True, null=True)
    stripe_return_url = models.URLField(blank=True, null=True) # URL to redirect after payment


    

    openAI_api_key = models.TextField(null=True, blank=True,  help_text="API key for OpenAI integration.")
    instabot_ai_prompt = models.TextField(null=True, blank=True)

    
    email_from = models.EmailField(blank=True, null=True, help_text="Default from email address used in system emails.")
    email_support = models.EmailField(blank=True, null=True, help_text="Support email address for users to contact.")
    email_footer_text = models.TextField(blank=True, null=True, help_text="Text shown at the bottom of system emails.")
    
    
    frontend_base_url = models.URLField(blank=True, null=True, help_text="Base URL of your frontend or domain used in links.")

    def save(self, *args, **kwargs):
        self.pk = 1  # ensure singleton
        super().save(*args, **kwargs)
        
    @classmethod
    def get_solo(cls):
        return cls.objects.get_or_create(pk=1)[0]

    def __str__(self):
        return "System Settings"
    


class ContactMessage(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    subject = models.CharField(max_length=255)
    message = models.TextField()
    email_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.subject} ({'Sent' if self.email_sent else 'Not Sent'})"



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