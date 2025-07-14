import random
# import os



from django.conf import settings
from django.utils import timezone
from django.core.mail import send_mail

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist

from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework import viewsets, filters
from rest_framework import serializers
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser, FormParser

from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken, TokenError



import requests


from .models import CustomUser
from .serializers import UserSignupSerializer, VerifyEmailSerializer, ResendVerificationCodeSerializer, PasswordResetRequestSerializer, PasswordResetConfirmSerializer, UserDetailSerializer, PublicUserDataSerializer
from .permissions import IsAdmin

# from system.models import SystemSettings
from users.services.chatbot import create_chatbot_user_and_account

# Pagination class for the user list view
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    # max_page_size = 100



class CheckEmailExistsView(APIView):
    authentication_classes = []  # Public
    permission_classes = []      # No auth required

    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response({"detail": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)

        # print(f"Checking if email exists: {email}")
        exists = User.objects.filter(email=email).exists()
        # print(f"Email exists: {exists}")
        return Response({"exists": exists}, status=status.HTTP_200_OK)
    




class UserSignupView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSignupSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Generate a 6-digit email code
            code = str(random.randint(100000, 999999))
            # user.email_verification_code = code
            user.email_verification_code = "123456"
            # user.email_verified = False  # Redundant now but kept for clarity
            user.email_code_created_at = timezone.now()
            user.save()

            # Send the code to the user's email
            send_mail(
                subject="Verify Your Email",
                message=f"Your verification code is: {code}",
                from_email=None,
                recipient_list=[user.email],
            )

            print(f"Verification code sent to {user.email}: {code}")
            # settings = SystemSettings.get_solo()
            # print(settings.admin_chatBot_key)

            chatbot_response = create_chatbot_user_and_account(user)
            if chatbot_response:
                return chatbot_response
            
            return Response({"detail": "Signup successful. Please verify your email."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyEmailView(APIView):
    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"detail": "Email verified successfully."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ResendVerificationCodeView(APIView):
    def post(self, request):
        serializer = ResendVerificationCodeSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"detail": "Verification code resent successfully."})
        return Response(serializer.errors, status=400)


# Login Views using JWT - For now I have written Serializer and view here
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)

        user = self.user

        if not user.email_verified:
            raise serializers.ValidationError("Please verify your email to login.")

        if user.status != 'active':
            raise serializers.ValidationError("Your account is disabled by the admin.")

        return data

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")

        if not refresh_token:
            return Response({"detail": "Refresh token is required."}, status=400)

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()  # This only works if token_blacklist app is enabled
            return Response({"detail": "Logged out successfully."}, status=205)
        except TokenError:
            return Response({"detail": "Invalid or expired token."}, status=400)
        


class PasswordResetRequestView(APIView):
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"detail": "Password reset code sent to email."})
        return Response(serializer.errors, status=400)

class PasswordResetConfirmView(APIView):
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"detail": "Password has been reset successfully."})
        return Response(serializer.errors, status=400)


class MeView(generics.RetrieveAPIView):
    serializer_class = UserDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

class MeUpdateView(generics.UpdateAPIView):
    serializer_class = UserDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user
    

class UserAdminViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all().order_by("id")
    serializer_class = UserDetailSerializer
    permission_classes = [IsAdmin]
    pagination_class = StandardResultsSetPagination

    # Enable filtering & search
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['first_name', 'last_name', 'email', 'phone_number', 'role', 'status']
    ordering_fields = ['first_name', 'last_name', 'email', 'status', 'role']

    def perform_create(self, serializer):
        # role should come from request data
        serializer.save()


class UserDataByKeyView(APIView):
    authentication_classes = []  #  Public endpoint
    permission_classes = []      #  No auth required

    def get(self, request, api_key):
        try:
            user = CustomUser.objects.get(api_key=api_key)
        except CustomUser.DoesNotExist:
            return Response({"detail": "Invalid API key."}, status=status.HTTP_404_NOT_FOUND)

        if user.status != 'active':
            return Response({"detail": "This user is inactive."}, status=status.HTTP_403_FORBIDDEN)

        serializer = PublicUserDataSerializer(user)
        return Response(serializer.data)
    
class UploadUserPictureView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        user = request.user
        image = request.FILES.get('picture')

        if not image:
            return Response({"detail": "No image file provided."}, status=400)

        # Generate unique filename
        ext = image.name.split('.')[-1]
        filename = f"user_{user.id}_profile.{ext}"
        storage_region = settings.BUNNY_STORAGE_HOSTNAME.split('.')[0]

        upload_url = f"https://{storage_region}.storage.bunnycdn.com/{settings.BUNNY_STORAGE_ZONE}/{filename}"
        public_url = f"https://{settings.BUNNY_PUBLIC_URL}/{filename}"

        headers = {
            "AccessKey": settings.BUNNY_API_KEY,
            "Content-Type": "application/octet-stream"
        }

        # print(f"Uploading to BunnyCDN: {upload_url}")
        # print(f"Public URL: {public_url}")
        # print(f"Headers: {headers}")

        try:
            response = requests.put(upload_url, headers=headers, data=image.read())
            # print(f"Response from BunnyCDN: {response.status_code} - {response.text}")
            if response.status_code in [200, 201]:
                user.picture = public_url
                user.save()
                return Response({"picture_url": public_url}, status=200)
            else:
                # print(f"Error uploading to BunnyCDN: {response.status_code} - {response.text}")
                return Response({"detail": "Failed to upload to BunnyCDN."}, status=500)

        except Exception as e:
            return Response({"detail": str(e)}, status=500)



User = get_user_model()

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

class GoogleLoginView(APIView):
    def post(self, request):
        token = request.data.get("id_token")

        if not token:
            return Response({"detail": "Missing id_token"}, status=400)

        try:
            idinfo = id_token.verify_oauth2_token(token, google_requests.Request())

            email = idinfo["email"]
            first_name = idinfo.get("given_name", "")
            last_name = idinfo.get("family_name", "")

            try:
                user = User.objects.get(email=email)
            except ObjectDoesNotExist:
                user = User.objects.create_user(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    role="user",
                    email_verified=True,
                    is_social=True,   # <-- Now it is handled properly by your create_user()
                )
                

            tokens = get_tokens_for_user(user)
            return Response(tokens)

        except Exception as e:
            return Response({"detail": str(e)}, status=400)

class FacebookLoginView(APIView):
    def post(self, request):
        access_token = request.data.get("access_token")

        if not access_token:
            return Response({"detail": "Missing access_token"}, status=400)

        fb_url = f"https://graph.facebook.com/me?fields=id,name,email,first_name,last_name&access_token={access_token}"

        response = requests.get(fb_url)
        if response.status_code != 200:
            return Response({"detail": "Invalid Facebook token"}, status=400)

        data = response.json()
        email = data.get("email")
        first_name = data.get("first_name", "")
        last_name = data.get("last_name", "")

        if not email:
            return Response({"detail": "Facebook account has no email."}, status=400)

        user, created = User.objects.get_or_create(email=email, defaults={
            "first_name": first_name,
            "last_name": last_name,
            "role": "user",
            "email_verified": True,
            "is_social" : True  #  This tells the manager to skip opt_terms/sizeOfCompany
        })

        tokens = get_tokens_for_user(user)
        return Response(tokens)
