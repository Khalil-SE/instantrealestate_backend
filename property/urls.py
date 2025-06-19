from django.urls import path
from .views.lofty_views import (connect_lofty,lofty_callback,fetch_properties, sync_lofty_listings, approve_lofty_property)
from property.views.property_views import PropertyListCreateView, PropertyRetrieveUpdateDestroyView 

urlpatterns = [
    path('lofty/connect/', connect_lofty, name='connect-lofty'),
    path('lofty/callback/', lofty_callback, name='lofty-callback'),
    path('lofty/fetch-properties/', fetch_properties, name='fetch-properties'),
    path('lofty/property/sync/', sync_lofty_listings),
    path('lofty/property/approve/<int:pk>/', approve_lofty_property),


    path('', PropertyListCreateView.as_view(), name='property-list-create'),
    path('<int:pk>/', PropertyRetrieveUpdateDestroyView.as_view(), name='property-detail'),
]
