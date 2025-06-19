"views/public_reply_template_views.py"
from rest_framework import generics, permissions
from rest_framework.permissions import SAFE_METHODS, BasePermission

from instabot.models import PublicReplyTemplate
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

    def get_queryset(self):
        return PublicReplyTemplate.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PublicReplyTemplateRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PublicReplyTemplateSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    lookup_field = "id"

    def get_queryset(self):
        return PublicReplyTemplate.objects.filter(user=self.request.user)
