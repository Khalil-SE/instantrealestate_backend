# shared/urls.py
from django.urls import path
from .views import KeywordAvailabilityView

urlpatterns = [
    path("check-keyword/", KeywordAvailabilityView.as_view(), name="check-keyword"),
]
