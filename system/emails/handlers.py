# emails/handlers.py
from django.template.loader import render_to_string
from django.conf import settings
from utils.email import send_html_email
from system.models import SystemSettings  # Adjust path as needed


def send_account_verification_email(user, verification_code):
    """
    Sends a verification email to a new user.
    """
    settings_obj = SystemSettings.get_solo()

    context = {
        "user": user,
        "verification_code": verification_code,
        "verify_url": f"{settings_obj.frontend_base_url}/verify-email?email={user.email}&code={verification_code}",
        "footer": settings_obj.email_footer_text,
    }

    send_html_email(
        subject="Verify your account",
        to_email=user.email,
        template_name="emails/verify_account.html",
        context=context,
        from_email=settings_obj.email_from or settings.DEFAULT_FROM_EMAIL,
        reply_to = settings_obj.email_support or settings_obj.email_from or settings.DEFAULT_FROM_EMAIL

    )


def send_instabot_created_email(user, bot_name):
    """
    Sends a notification email when a new InstaBot is created.
    """
    settings_obj = SystemSettings.get_solo()

    context = {
        "user": user,
        "bot_name": bot_name,
        "dashboard_url": f"{settings_obj.frontend_base_url}/dashboard",
        "footer": settings_obj.email_footer_text,
    }

    send_html_email(
        subject=f"InstaBot '{bot_name}' Created Successfully",
        to_email=user.email,
        template_name="emails/instabot_created.html",
        context=context,
        from_email=settings_obj.email_from or settings.DEFAULT_FROM_EMAIL,
        reply_to=settings_obj.email_support or settings_obj.email_from or settings.DEFAULT_FROM_EMAIL
    )
