# seed_superuser.py

import os
import django

# Set the Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "instantrealestate_backend.settings")  # replace with your settings module

# Setup Django
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Create superuser only if not exists
if not User.objects.filter(role="admin").exists():
    User.objects.create_superuser(
        first_name="Admin",
        last_name="User",
        role="admin",
        email="admin@admin.com",
        password="admin123"
    )
    print("Superuser created successfully.")
else:
    print("Superuser already exists.")
