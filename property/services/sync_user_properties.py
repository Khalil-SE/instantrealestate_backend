# property/services/sync_user_properties.py
from celery import shared_task
from django.utils.timezone import now
from property.models import LoftyProperty
from users.models import CustomUser
from property.views.lofty_views import refresh_lofty_token
import requests
from django.conf import settings
from django.core.exceptions import ValidationError

@shared_task
def sync_lofty_for_user(user_id):
    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return

    if not user.lofty_access_token:
        return

    if not user.lofty_token_expires_at or user.lofty_token_expires_at <= now():
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

    # print("Response")
    # print(response.json())
    try:
        listings = response.json().get("listIng", [])
    except Exception:
        return

    for item in listings:
        
        # start for log under development
        # for k, v in item.items():
        #     if isinstance(v, str) and len(v) > 200:
        #         print(f"{k} too long: {len(v)} and the value is {v}")

        # print("MAPPING PREVIEW >>>")
        # print(f"listing_id: {item.get('listingId')}")
        # print(f"address: {item.get('listingStreetName')}")
        # print(f"city: {item.get('listingCity')}")
        # print(f"state: {item.get('listingState')}")
        # print(f"zip_code: {item.get('listingZipcode')}")
        # print(f"description: {item.get('detailsDescribe')[:100]}... ({len(item.get('detailsDescribe', ''))} chars)")
        # print(f"image_url: {(item.get('pictureList') or [None])[0]}")


        # end log under development
        try:
            listing_id = str(item.get("listingId", ""))[:100]
            if not listing_id:
                print("Empty listing_id — skipping")
                continue

            obj, created = LoftyProperty.objects.update_or_create(
                listing_id=listing_id,
                user=user,
                defaults={
                    "address": item.get("listingStreetName", "")[:255],
                    "city": item.get("listingCity", "")[:100],
                    "state": item.get("listingState", "")[:100],
                    "zip_code": (item.get("listingZipcode") or [""])[0][:20],
                    "beds": item.get("beds"),
                    "baths": item.get("baths"),
                    "sqft": item.get("sqft"),
                    "price": item.get("price"),
                    "description": item.get("detailsDescribe", "")[:5000],  # Safe size
                    # "image_url": (item.get("pictureList") or [""])[0][:2000],  # For safety
                    "image_url": (
                        str(item.get("pictureList")[0])[:2000]
                        if isinstance(item.get("pictureList"), list) and item.get("pictureList") else ""
                    ),
                    "raw_data": item,
                    "fetched_at": now()
                }
                # defaults={
                #     "address": item.get("listingStreetName"),
                #     "city": item.get("listingCity"),
                #     "state": item.get("listingState"),
                #     "zip_code": (item.get("listingZipcode") or [None])[0],
                #     "beds": item.get("beds"),
                #     "baths": item.get("baths"),
                #     "sqft": item.get("sqft"),
                #     "price": item.get("price"),
                #     "description": item.get("detailsDescribe")[:1000],  # Limit to 1000 chars
                #     "image_url": (item.get("pictureList") or [None])[0],
                #     "raw_data": item,
                #     "fetched_at": now()
                # }
            )
        except ValidationError as e:
            print("ValidationError:", e)
        except LoftyProperty.MultipleObjectsReturned:
            print(f" Multiple listings with same id+user found: {listing_id}")
            continue
        except Exception as e:
            print("Unexpected Error:", e)
            print(e)
            continue  # Skip this listing
        if created:
            # TODO: Trigger notification logic (email, socket, dashboard update)
            print(f"New listing added for user {user.email}: {obj.address}")
