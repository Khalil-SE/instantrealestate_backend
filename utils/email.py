# from django.core.mail import EmailMultiAlternatives
# from django.template.loader import render_to_string
# from django.conf import settings

# def send_html_email(subject, to_email, template_name, context):
#     html_content = render_to_string(template_name, context)
#     msg = EmailMultiAlternatives(
#         subject=subject,
#         body=html_content,  # fallback plain text
#         from_email=settings.DEFAULT_FROM_EMAIL,
#         to=[to_email],
#     )
#     msg.attach_alternative(html_content, "text/html")
#     msg.send()




# Example usage:
# from utils.email import send_html_email

# send_html_email(
#     subject="Verify Your Email",
#     to_email=user.email,
#     template_name="emails/account_verification.html",
#     context={"user": user, "verification_link": verification_url}
# )


# utils/email.py
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

def send_html_email(subject, to_email, template_name, context={}, from_email=None, reply_to=None):
    """
    Sends an HTML email using a template and context.

    Args:
        subject (str): Email subject
        to_email (str | list): Recipient or list of recipients
        template_name (str): Relative path to the email template (e.g., "emails/verify.html")
        context (dict): Context for rendering the template
        from_email (str): Optional sender email (uses DEFAULT_FROM_EMAIL if None)
        reply_to (str | list): Optional reply-to address
    """
    if not from_email:
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com")

    if isinstance(to_email, str):
        to_email = [to_email]

    html_content = render_to_string(template_name, context)
    text_content = strip_tags(html_content)

    print(f"Sent email to {to_email}: {subject}")
    # Or use a model to store it for audit purposes


    msg = EmailMultiAlternatives(subject, text_content, from_email, to_email)

    if reply_to:
        msg.reply_to = [reply_to] if isinstance(reply_to, str) else reply_to

    msg.attach_alternative(html_content, "text/html")
    msg.send()
