# instabot/views/public_reply_template_views.py
from rest_framework import generics, permissions
from rest_framework.permissions import SAFE_METHODS, BasePermission

from instabot.models import PublicReplyTemplate, PublicReplyContent
from instabot.serializers import PublicReplyTemplateSerializer


class IsOwnerOrReadOnly(BasePermission):
    """
    Only the owner can update or delete the template.
    """
    def has_object_permission(self, request, view, obj):
        return request.method in SAFE_METHODS or obj.user == request.user


class PublicReplyTemplateListCreateView(generics.ListCreateAPIView):
    serializer_class = PublicReplyTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]

    # def get_queryset(self):
    #     return PublicReplyTemplate.objects.filter(user=self.request.user).order_by('-created_at')
    def get_queryset(self):
        user = self.request.user
        queryset = PublicReplyTemplate.objects.filter(user=user)

        if not queryset.exists():
            # Create default template named "Template 1"
            template = PublicReplyTemplate.objects.create(
                user=user,
                name="Template 1"
            )

            # Create default replies
            default_replies = [
                "Thanks for your interest! 😊 Check your DMs for more details.",
                "Just sent you a message! 📨 Let me know if you have any questions.",
                "I've sent you all the information in your DMs! 💯 Thanks for reaching out.",
                "Check your inbox! 🔔 I've sent you everything you need to know."
            ]

            PublicReplyContent.objects.bulk_create([
                PublicReplyContent(template=template, text=reply)
                for reply in default_replies
            ])

            queryset = PublicReplyTemplate.objects.filter(user=user)

        return queryset.order_by('-created_at')


    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PublicReplyTemplateRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PublicReplyTemplateSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    lookup_field = "id"

    def get_queryset(self):
        return PublicReplyTemplate.objects.filter(user=self.request.user)
