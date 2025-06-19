from rest_framework import serializers
from .models import SystemSettings

# serializers.py
class SystemSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemSettings
        fields = [
            'admin_chatBot_key',
            'chatbot_create_user_url',
            'chatbot_create_account_url',
            'stripe_api_key',
            'stripe_webhook_secret',
            'stripe_return_url',
            'instabot_ai_prompt',
            'email_from',
            'email_footer_text',
            'frontend_base_url',
        ]


# class SystemSettingsSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = SystemSettings
#         fields = ['admin_chatBot_key']