from django.urls import path
from . import views

urlpatterns = [
    path('connect/', views.connect_lofty, name='connect-lofty'),
    path('callback/', views.lofty_callback, name='lofty-callback'),
    path('fetch-properties/', views.fetch_properties, name='fetch-properties'),
]
