import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    def handle(self, *args, **options):
        username = os.getenv("DJANGO_SUPERUSER_USERNAME", "admin")
        email = os.getenv("DJANGO_SUPERUSER_EMAIL", "admin@example.com")
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD", "securepassword")

        if not User.objects.filter(email=email).exists():
            user = User.objects.create_superuser(username, email, password)
            user.save()
            print(f"Superuser {username} created successfully!")
        else:
            print(f"Superuser {username} already exists.")
