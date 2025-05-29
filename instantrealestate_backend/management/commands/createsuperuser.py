from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
import os

User = get_user_model()

class Command(BaseCommand):
    help = "Automatically create a superuser"

    def handle(self, *args, **kwargs):
        username = os.getenv("DJANGO_SUPERUSER_USERNAME", "admin")
        email = os.getenv("DJANGO_SUPERUSER_EMAIL", "khalilattns@gmail.com")
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD", "123456789")

        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(username=username, email=email, password=password)
            self.stdout.write(self.style.SUCCESS(f"Superuser {username} created successfully"))
        else:
            self.stdout.write(self.style.WARNING(f"Superuser {username} already exists"))
