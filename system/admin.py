from django.contrib import admin
from .models import SystemSettings
# Register your models here.

@admin.register(SystemSettings)

class SystemSettingsAdmin(admin.ModelAdmin):
    fields = ['admin_chatBot_key', 'chatbot_create_user_url', 'chatbot_create_account_url',  'stripe_api_key', 'stripe_webhook_secret', 'stripe_return_url']

    def has_add_permission(self, request):
        return False  # prevent adding new records
    def has_change_permission(self, request, obj=None):
        return True  # allow editing