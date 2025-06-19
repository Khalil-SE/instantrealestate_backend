"property/lofty_views.py"
import requests
# import datetime
from django.conf import settings
from django.shortcuts import redirect
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils.timezone import now
from users.models import CustomUser  # Adjust if your model is elsewhere
import base64
import requests
from django.conf import settings
from django.utils.timezone import now
from datetime import timedelta

from property.models import LoftyProperty
from property.serializers import LoftyPropertySerializer

# This view redirects the user to Lofty's OAuth authorization page with seesions saving the user id
# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def connect_lofty(request):
#     # Save user ID in session temporarily
#     # request.session['lofty_user_id'] = request.user.id
#     request.session['lofty_user_id'] = str(request.user.id)

#     params = {
#         'client_id': settings.LOFTY_CLIENT_ID,
#         'redirect_uri': settings.LOFTY_REDIRECT_URI,
#         'response_type': 'code',
#         'scope': 'read',
#     }

#     auth_url = f"{settings.LOFTY_AUTH_URL}?client_id={params['client_id']}&redirect_uri={params['redirect_uri']}&response_type=code&scope={params['scope']}"
#     return redirect(auth_url)
# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def connect_lofty(request):
#     try:
#         # Convert UUID to string before saving
#         request.session['lofty_user_id'] = str(request.user.id)

#         client_id = settings.LOFTY_CLIENT_ID
#         redirect_uri = settings.LOFTY_REDIRECT_URI
#         auth_url = settings.LOFTY_AUTH_URL

#         url = f"{auth_url}?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope=read"
#         return redirect(url)
#     except Exception as e:
#         print("ERROR in connect_lofty:", str(e))
#         return Response({"error": "Internal server error", "details": str(e)}, status=500)
# @api_view(['GET'])
# def connect_lofty(request):
#     try:
#         api_key = request.GET.get('key')
#         if not api_key:
#             return Response({"error": "Missing API key"}, status=401)

#         user = CustomUser.objects.filter(api_key=api_key).first()
#         if not user:
#             return Response({"error": "Invalid API key"}, status=404)

#         # Save user ID in session for callback
#         request.session['lofty_user_id'] = str(user.id)

#         # Build Lofty OAuth URL
#         client_id = settings.LOFTY_CLIENT_ID
#         redirect_uri = settings.LOFTY_REDIRECT_URI
#         auth_url = settings.LOFTY_AUTH_URL

#         url = f"{auth_url}?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope=read"
#         return redirect(url)

#     except Exception as e:
#         return Response({"error": "Internal server error", "details": str(e)}, status=500)

@api_view(['GET'])
def connect_lofty(request):
    api_key = request.GET.get('key')
    if not api_key:
        return Response({"error": "Missing API key"}, status=400)

    user = CustomUser.objects.filter(api_key=api_key).first()
    if not user:
        return Response({"error": "Invalid API key"}, status=404)

    # Store user ID for callback later
    # request.session['lofty_user_id'] = str(user.id)

    # Redirect to Lofty's vendor OAuth page
    #   const redirectUrl = `https://lofty.com/page/vendor-auth.html?clientId=${clientId}&state=${user.api_key}`;
    redirect_url = f"{settings.LOFTY_AUTH_URL}?clientId={settings.LOFTY_CLIENT_ID}&state={user.api_key}"
    return redirect(redirect_url)

def refresh_lofty_token(user):
    if not user.lofty_refresh_token:
        return None, "No refresh token available"

    credentials = f"{settings.LOFTY_CLIENT_ID}:{settings.LOFTY_CLIENT_SECRET}"
    encoded = base64.b64encode(credentials.encode()).decode()

    headers = {
        'Authorization': f'Basic {encoded}',
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    data = {
        'grant_type': 'refresh_token',
        'refresh_token': user.lofty_refresh_token,
    }

    response = requests.post(settings.LOFTY_TOKEN_URL, headers=headers, data=data)

    if response.status_code != 200:
        return None, response.json()

    tokens = response.json()
    user.lofty_access_token = tokens.get("access_token")
    user.lofty_refresh_token = tokens.get("refresh_token", user.lofty_refresh_token)  # fallback
    user.lofty_token_expires_at = now() + timedelta(seconds=tokens.get("expires_in", 3600))
    user.save()

    return user.lofty_access_token, None

# This view handles the callback from Lofty (after user grants permission)
# @api_view(['GET'])
# def lofty_callback(request):
#     code = request.GET.get('code')
#     if not code:
#         return Response({"error": "No code received"}, status=400)

#     # Exchange code for access and refresh tokens
#     data = {
#         'client_id': settings.LOFTY_CLIENT_ID,
#         'client_secret': settings.LOFTY_CLIENT_SECRET,
#         'grant_type': 'authorization_code',
#         'redirect_uri': settings.LOFTY_REDIRECT_URI,
#         'code': code,
#     }

#     token_response = requests.post(settings.LOFTY_TOKEN_URL, data=data)
#     if token_response.status_code != 200:
#         return Response({"error": "Token exchange failed", "details": token_response.json()}, status=400)

#     tokens = token_response.json()
#     access_token = tokens['access_token']
#     refresh_token = tokens.get('refresh_token')
#     expires_in = tokens.get('expires_in', 3600)
#     expires_at = now() + datetime.timedelta(seconds=expires_in)

#     # Use access token to get Lofty user info
#     headers = {
#         'Authorization': f'Bearer {access_token}',
#         'Content-Type': 'application/json'
#     }
#     user_info_response = requests.get('https://api.chime.me/v1/me', headers=headers)
#     if user_info_response.status_code != 200:
#         return Response({"error": "Failed to fetch user info", "details": user_info_response.json()}, status=400)

#     user_info = user_info_response.json()
#     lofty_user_id = user_info.get('user_id')

#     user_id = request.session.get('lofty_user_id')
#     if not user_id:
#         return Response({"error": "User session lost. Please try connecting again."}, status=400)

#     user = CustomUser.objects.filter(id=user_id).first()
#     if not user:
#         return Response({"error": "User not found"}, status=404)

#     # Save Lofty tokens and user ID
#     user.lofty_access_token = access_token
#     user.lofty_refresh_token = refresh_token
#     user.lofty_token_expires_at = expires_at
#     user.lofty_user_id = lofty_user_id
#     user.save()

#     # Clear the session
#     del request.session['lofty_user_id']
#     return Response({
#         "message": "Lofty account connected successfully",
#         "lofty_user_id": lofty_user_id
#     })

# @api_view(['GET'])
# def lofty_callback(request):
#     print("Lofty callback received")
#     print("Request GET parameters:", request.GET)
#     code = request.GET.get('code')
#     if not code:
#         return Response({"error": "No code received"}, status=400)

#     # Step 1: Exchange code for access + refresh tokens
#     data = {
#         'client_id': settings.LOFTY_CLIENT_ID,
#         'client_secret': settings.LOFTY_CLIENT_SECRET,
#         'grant_type': 'authorization_code',
#         'redirect_uri': settings.LOFTY_REDIRECT_URI,
#         'code': code,
#     }

#     token_response = requests.post(settings.LOFTY_TOKEN_URL, data=data)
#     if token_response.status_code != 200:
#         return Response({"error": "Token exchange failed", "details": token_response.json()}, status=400)

#     tokens = token_response.json()
#     access_token = tokens['access_token']
#     refresh_token = tokens.get('refresh_token')
#     expires_in = tokens.get('expires_in', 3600)
#     expires_at = now() + datetime.timedelta(seconds=expires_in)

#     # Step 2: Fetch Lofty user profile using the access token
#     user_info_response = requests.get(
#         settings.LOFTY_USER_INFO_URL,
#         headers={
#             'Authorization': f'Bearer {access_token}',
#             'Content-Type': 'application/json',
#         }
#     )
#     if user_info_response.status_code != 200:
#         return Response({"error": "Failed to fetch user info", "details": user_info_response.json()}, status=400)

#     user_info = user_info_response.json()
#     lofty_user_id = user_info.get('user_id')

#     # Step 3: Retrieve user from session-stored ID (originally based on API key)
#     user_id = request.session.get('lofty_user_id')
#     if not user_id:
#         return Response({"error": "User session lost. Please try connecting again."}, status=400)

#     user = CustomUser.objects.filter(id=user_id).first()
#     if not user:
#         return Response({"error": "User not found"}, status=404)

#     # Step 4: Save Lofty details to user
#     user.lofty_access_token = access_token
#     user.lofty_refresh_token = refresh_token
#     user.lofty_token_expires_at = expires_at
#     user.lofty_user_id = lofty_user_id
#     user.save()

#     # Optional: clean up session
#     del request.session['lofty_user_id']

#     return Response({
#         "message": "Lofty account connected successfully",
#         "lofty_user_id": lofty_user_id
#     })

@api_view(['GET'])
def lofty_callback(request):
    print("Lofty callback received")
    # print(request)
    print("Request GET parameters:", request.GET)
    code = request.GET.get('code')
    api_key = request.GET.get('state')
    
    if not code:
        return Response({"error": "No code received"}, status=400)

    # user_id = request.session.get('lofty_user_id')
    # if not user_id:
    #     return Response({"error": "Session expired. Please connect again."}, status=400)
    if not api_key:
        return Response({"error": "Missing InstantRealEstate API key"}, status=400)
    user = CustomUser.objects.filter(api_key=api_key).first()
    if not user:
        return Response({"error": "User not found"}, status=404)

    credentials = f"{settings.LOFTY_CLIENT_ID}:{settings.LOFTY_CLIENT_SECRET}"
    encoded = base64.b64encode(credentials.encode()).decode()

    headers = {
        'Authorization': f'Basic {encoded}',
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    data = {
        'code': code,
        'client_id': settings.LOFTY_CLIENT_ID,
        'redirect_uri': settings.LOFTY_REDIRECT_URI,
        'grant_type': 'authorization_code',
    }

    response = requests.post(settings.LOFTY_TOKEN_URL, headers=headers, data=data)

    try:
        tokens = response.json()
    except ValueError:
        return Response({
            "error": "Token exchange failed",
            "status_code": response.status_code,
            "details": response.text,
        }, status=400)

    if response.status_code != 200:
        return Response({
            "error": "Token exchange failed",
            "status_code": response.status_code,
            "details": tokens,
        }, status=400)

    # Save token
    user.lofty_access_token = tokens.get("access_token")
    user.lofty_refresh_token = tokens.get("refresh_token")
    user.lofty_token_expires_at = now() + timedelta(seconds=tokens.get("expires_in", 3600))
    user.save()

    return Response({"message": "Lofty integration successful ✅"})
    # import base64
    # import requests
    # from django.utils.timezone import now
    # from datetime import timedelta

    # # Prepare Basic Auth header
    # credentials = f"{settings.LOFTY_CLIENT_ID}:{settings.LOFTY_CLIENT_SECRET}"
    # encoded = base64.b64encode(credentials.encode()).decode()

    # headers = {
    #     'Authorization': f'Basic {encoded}',
    #     'Content-Type': 'application/x-www-form-urlencoded'
    # }

    # data = {
    #     'code': code,
    #     'client_id': settings.LOFTY_CLIENT_ID,
    #     'redirect_uri': settings.LOFTY_REDIRECT_URI,
    #     'grant_type': 'authorization_code'
    # }

    # token_response = requests.post(settings.LOFTY_TOKEN_URL, headers=headers, data=data)
    # print("Token response:", token_response)
    # # if token_response.status_code != 200:
    # #     return Response({"error": "Token exchange failed", "details": token_response.json()}, status=400)
    # if token_response.status_code != 200:
    #     try:
    #         error_body = token_response.json()
    #     except ValueError:
    #         error_body = token_response.text  # maybe HTML or plain text error

    #     return Response({
    #         "error": "Token exchange failed",
    #         "status_code": token_response.status_code,
    #         "details": error_body,
    #     }, status=400)


    # token_data = token_response.json()
    # user.lofty_access_token = token_data.get("access_token")
    # user.lofty_refresh_token = token_data.get("refresh_token")
    # user.lofty_token_expires_at = now() + timedelta(seconds=token_data.get("expires_in", 3600))
    # user.save()
    # return Response({
    #     "message": "Lofty account successfully connected",
    #     "lofty_user_id": user.lofty_user_id,
    #     "access_token": user.lofty_access_token,
    # })

    # del request.session['lofty_user_id']
    # return Response({"message": "Lofty account connected successfully"})
    


# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def fetch_properties(request):
#     print("Fetching properties for user:", request.user.id)
#     user = request.user

#     if not user.lofty_access_token:
#         return Response({"error": "User is not connected to Lofty"}, status=400)

#     headers = {
#         "Authorization": f"Bearer {user.lofty_access_token}",
#         "Content-Type": "application/json"
#     }

#     # Example: You might need to paginate depending on Lofty API docs
#     response = requests.get(f"{settings.LOFTY_LISTINGS_URL}", headers=headers)

#     if response.status_code != 200:
#         return Response({"error": "Failed to fetch listings", "details": response.json()}, status=response.status_code)

#     return Response(response.json())


# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def fetch_properties(request):
#     print("Fetching properties for user:", request.user.id)
#     user = request.user

#     if not user.lofty_access_token:
#         return Response({"error": "User is not connected to Lofty"}, status=400)

#     # Check expiration
#     if user.lofty_token_expires_at and user.lofty_token_expires_at <= now():
#         access_token, error = refresh_lofty_token(user)
#         if error:
#             return Response({"error": "Failed to refresh token", "details": error}, status=401)
#     else:
#         access_token = user.lofty_access_token

#     headers = {
#         "Authorization": f"Bearer {access_token}",
#         "Content-Type": "application/json"
#     }

#     response = requests.get(f"{settings.LOFTY_LISTINGS_URL}", headers=headers)

#     if response.status_code != 200:
#         return Response({"error": "Failed to fetch listings", "details": response.json()}, status=response.status_code)

#     return Response(response.json())

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def fetch_properties(request):
    print("Fetching properties for user:", request.user.id)
    user = request.user

    if not user.lofty_access_token:
        return Response({"error": "User is not connected to Lofty"}, status=400)

    # Refresh token if expired
    if user.lofty_token_expires_at and user.lofty_token_expires_at <= now():
        access_token, error = refresh_lofty_token(user)
        if error:
            return Response({"error": "Failed to refresh token", "details": error}, status=401)
    else:
        access_token = user.lofty_access_token

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (compatible; InstantRealEstateBot/1.0)"
    }

    response = requests.get(f"{settings.LOFTY_LISTINGS_URL}", headers=headers)
    print(settings.LOFTY_LISTINGS_URL)
    print("Response from Lofty")
    print(response)
    
    try:
        data = response.json()
    except ValueError:
        return Response({"error": "Lofty response was not valid JSON", "raw": response.text}, status=500)

    if response.status_code != 200:
        return Response({"error": "Failed to fetch listings", "details": data}, status=response.status_code)

    listings = data.get("listIng", [])
    parsed = []

    for item in listings:
        parsed.append({
            "mls_id": item.get("listingId"),
            "address": item.get("listingStreetName"),
            "city": item.get("listingCity"),
            "state": item.get("listingState"),
            "zip_code": item.get("listingZipcode", [None])[0],  # list to str
            "beds": item.get("beds"),
            "baths": item.get("baths"),
            "sqft": item.get("sqft"),
            "price": item.get("price"),
            "description": item.get("detailsDescribe"),
            "image_url": (item.get("pictureList") or [None])[0],  # first image or None
        })

    return Response({
        "properties": parsed,
        "meta": data.get("_listingMetadata", {})
    })



# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def fetch_properties(request):
#     print("Fetching properties for user:", request.user.id)
#     user = request.user

#     if not user.lofty_access_token:
#         return Response({"error": "User is not connected to Lofty"}, status=400)

#     # Refresh token if expired
#     if user.lofty_token_expires_at and user.lofty_token_expires_at <= now():
#         access_token, error = refresh_lofty_token(user)
#         if error:
#             return Response({"error": "Failed to refresh token", "details": error}, status=401)
#     else:
#         access_token = user.lofty_access_token

#     headers = {
#         "Authorization": f"Bearer {access_token}",
#         "Content-Type": "application/json"
#     }

#     # Allow limit to be passed in frontend (default 5)
#     limit = request.GET.get("limit", 5)
#     url = f"{settings.LOFTY_LISTINGS_URL}&limit={limit}"

#     response = requests.get(url, headers=headers)

#     try:
#         data = response.json()
#     except ValueError:
#         return Response({
#             "error": "Failed to fetch listings",
#             "status_code": response.status_code,
#             "details": response.text
#         }, status=response.status_code)

#     if response.status_code != 200:
#         return Response({"error": "Failed to fetch listings", "details": data}, status=response.status_code)

#     return Response(data)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sync_lofty_listings(request):
    user = request.user
    updated = []

    if user.lofty_token_expires_at and user.lofty_token_expires_at <= now():
        access_token, err = refresh_lofty_token(user)
        if err:
            return Response({"error": "Failed refresh", "details": err}, status=401)
    else:
        access_token = user.lofty_access_token

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }
    url = f"{settings.LOFTY_LISTINGS_URL}&limit=50"  # or configurable

    resp = requests.get(url, headers=headers)
    try:
        data = resp.json()
    except ValueError:
        return Response({"error": "Invalid remote response", "raw": resp.text}, status=500)
    if resp.status_code != 200:
        return Response({"error": "Failed fetch", "details": data}, status=resp.status_code)

    for item in data.get("listIng", []):
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
        updated.append(obj)

    serializer = LoftyPropertySerializer(updated, many=True)
    return Response(serializer.data)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_lofty_property(request, pk):
    lp = LoftyProperty.objects.filter(pk=pk, user=request.user, is_selected=False).first()
    if not lp:
        return Response({"error": "Listing not found or already approved"}, status=404)

    # Assuming you have a `Property` model and serializer
    prop = Property.objects.create(
        url=lp.raw_data.get("detailUrl"),
        keyword=None,
        address=lp.address, city=lp.city, state=lp.state, zip_code=lp.zip_code,
        price=lp.price, beds=lp.beds, baths=lp.baths, sqft=lp.sqft,
        lot_size=lp.raw_data.get("totalAvailableAcres"),
        description=lp.description, ai_generated_description="",
        button1_text="", button1_url="", button2_text="", button2_url="",
        image_url=lp.image_url,
        email_recipients=[]
    )
    lp.is_selected = True
    lp.save()
    return Response(PropertySerializer(prop).data)