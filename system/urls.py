from django.urls import path
from .views import SystemSettingsView, ContactUsView

urlpatterns = [
    path('settings/', SystemSettingsView.as_view(), name='system-settings'),
    path("contact-us/", ContactUsView.as_view(), name="contact-us"),
]