from django.urls import path
from instabot.views.public_reply_template_views import (
    PublicReplyTemplateListCreateView,
    PublicReplyTemplateRetrieveUpdateDestroyView,
)

from .views.instabot_views import (
    InstaBotListCreateView,
    InstaBotRetrieveUpdateDestroyView
)




urlpatterns = [
    path("public-reply-templates/", PublicReplyTemplateListCreateView.as_view(), name="template-list"),
    path("public-reply-templates/<int:id>/", PublicReplyTemplateRetrieveUpdateDestroyView.as_view(), name="template-detail"),

     path("instabots/", InstaBotListCreateView.as_view(), name="instabot-list-create"),
    path("instabots/<int:id>/", InstaBotRetrieveUpdateDestroyView.as_view(), name="instabot-detail"),
]

