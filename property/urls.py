from django.urls import path
from .views.lofty_views import (connect_lofty,lofty_callback,fetch_properties, sync_lofty_listings, approve_lofty_property)
from property.views.property_views import PropertyListCreateView, PropertyRetrieveUpdateDestroyView 
from property.views.lofty_views import LoftyPropertyListView, mark_lofty_property_imported

urlpatterns = [
    path('lofty/connect/', connect_lofty, name='connect-lofty'),
    path('lofty/callback/', lofty_callback, name='lofty-callback'),
    path('lofty/fetch-properties/', fetch_properties, name='fetch-properties'),
    path('lofty/property/sync/', sync_lofty_listings),
    path('lofty/property/approve/<int:pk>/', approve_lofty_property),
    path('lofty/mark-imported/<str:listing_id>/', mark_lofty_property_imported, name='mark-lofty-imported'),

    # to get lofty properties on the frontend 
    path('lofty/properties/', LoftyPropertyListView.as_view(), name='lofty-property-list'),


    path('', PropertyListCreateView.as_view(), name='property-list-create'),
    path('<int:pk>/', PropertyRetrieveUpdateDestroyView.as_view(), name='property-detail'),
]
