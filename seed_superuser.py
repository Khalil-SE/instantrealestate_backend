# seed_superuser.py
from django.contrib.auth import get_user_model

User = get_user_model()

if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser(
        username='admin',
        email='admin@admin.com',
        password='admin123'
    )
    print("Superuser created.")
else:
    print("Superuser already exists.")
