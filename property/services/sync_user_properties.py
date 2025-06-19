# property/services/sync_user_properties.py
from celery import shared_task
from django.utils.timezone import now
from property.models import LoftyProperty
from users.models import CustomUser
from shared.utils import refresh_lofty_token
import requests
from django.conf import settings

@shared_task
def sync_lofty_for_user(user_id):
    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return

    if not user.lofty_access_token:
        return

    if user.lofty_token_expires_at <= now():
        token, error = refresh_lofty_token(user)
        if error:
            return
    else:
        token = user.lofty_access_token

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }

    url = f"{settings.LOFTY_LISTINGS_URL}&limit=50"
    response = requests.get(url, headers=headers)

    try:
        listings = response.json().get("listIng", [])
    except Exception:
        return

    for item in listings:
        obj, created = LoftyProperty.objects.update_or_create(
            listing_id=item["listingId"],
            user=user,
            defaults={
                "address": item.get("listingStreetName"),
                "city": item.get("listingCity"),
                "state": item.get("listingState"),
                "zip_code": (item.get("listingZipcode") or [None])[0],
                "beds": item.get("beds"),
                "baths": item.get("baths"),
                "sqft": item.get("sqft"),
                "price": item.get("price"),
                "description": item.get("detailsDescribe"),
                "image_url": (item.get("pictureList") or [None])[0],
                "raw_data": item,
                "fetched_at": now()
            }
        )
        if created:
            # TODO: Trigger notification logic (email, socket, dashboard update)
            print(f"New listing added for user {user.email}: {obj.address}")
