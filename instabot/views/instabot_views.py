# instabot/views/instabot_views.py
from rest_framework import generics, permissions, filters
from rest_framework.permissions import SAFE_METHODS, BasePermission
from django.core.mail import send_mail

from system.emails.handlers import send_instabot_created_email

from instabot.models import InstaBot
from instabot.serializers import InstaBotSerializer
from instabot.services.openai_generator import generate_social_media_post


class IsBotOwnerOrReadOnly(BasePermission):
    """
    Custom permission to allow only the owner of an InstaBot
    to view, edit or delete it.
    """
    def has_object_permission(self, request, view, obj):
        return request.method in SAFE_METHODS or obj.user == request.user


class InstaBotListCreateView(generics.ListCreateAPIView):
    """
    List all InstaBots belonging to the authenticated user or create a new one.
    """
    serializer_class = InstaBotSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['keyword__text', 'title', 'status', 'message_type']
    ordering_fields = ['id', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        return InstaBot.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        instabot = serializer.save(user=self.request.user)

        # if instabot.ai_post_description and instabot.keyword:
        #     ai_post = generate_social_media_post(instabot.ai_post_description, instabot.keyword.text)
        #     print("Generated AI post:", ai_post)
        #     # instabot.message = ai_post
        #     # instabot.save()





    # def perform_create(self, serializer):
    #     instabot = serializer.save(user=self.request.user)
        # try:
        #     send_instabot_created_email(self.request.user, instabot.title)
        # except Exception as e:
        #     print("Email sending failed:", e)  # Or use logger
        #     # Send the code to the user's email
        #     send_mail(
        #         subject="Verify Your Email",
        #         message=f"You have created instabot: { instabot.title}",
        #         from_email=None,
        #         recipient_list=[self.request.user.email],
        #     )


class InstaBotRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a specific InstaBot (if owned by the user).
    """
    serializer_class = InstaBotSerializer
    permission_classes = [permissions.IsAuthenticated, IsBotOwnerOrReadOnly]
    lookup_field = "id"

    def get_queryset(self):
        return InstaBot.objects.filter(user=self.request.user)

    def perform_update(self, serializer):
        instabot = serializer.save()

        # if instabot.ai_post_description and instabot.keyword:
        #     ai_post = generate_social_media_post(
        #         instabot.ai_post_description,
        #         instabot.keyword.text
        #     )
        #     # instabot.message = ai_post
        #     print("Generated AI post:", ai_post)
        #     # instabot.save()




# from rest_framework import generics, permissions
# from rest_framework.permissions import SAFE_METHODS, BasePermission

# from instabot.models import InstaBot
# from instabot.serializers import InstaBotSerializer

# class IsBotOwnerOrReadOnly(BasePermission):
#     def has_object_permission(self, request, view, obj):
#         return request.method in SAFE_METHODS or obj.user == request.user

# class InstaBotListCreateView(generics.ListCreateAPIView):
#     serializer_class = InstaBotSerializer
#     permission_classes = [permissions.IsAuthenticated]

#     def get_queryset(self):
#         return InstaBot.objects.filter(user=self.request.user).order_by('-created_at')

#     def perform_create(self, serializer):
#         serializer.save(user=self.request.user)

# class InstaBotRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
#     serializer_class = InstaBotSerializer
#     permission_classes = [permissions.IsAuthenticated, IsBotOwnerOrReadOnly]
#     lookup_field = "id"

#     def get_queryset(self):
#         return InstaBot.objects.filter(user=self.request.user)
