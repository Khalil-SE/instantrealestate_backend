"property/tasks/sync.py"
from celery import shared_task
from users.models import CustomUser
from property.services.sync_user_properties import sync_lofty_for_user  # You'll define this logic separately

@shared_task
def sync_lofty_all_users():
    for user in CustomUser.objects.filter(lofty_access_token__isnull=False):
        sync_lofty_for_user.delay(str(user.id))  # Or call directly if not async
