from django.contrib import admin
from .models import Property, LoftyProperty

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user', 'keyword', 'city', 'state', 'price', 'home_type', 'created_at'
    )
    search_fields = ('address', 'city', 'state', 'zip_code')
    list_filter = ('state', 'home_type', 'created_at')
    ordering = ('-created_at',)



@admin.register(LoftyProperty)
class LoftyProperty(admin.ModelAdmin):
    list_display = (
        'listing_id', 'user', 'address', 'city', 'state', 'price', 'is_selected', 'fetched_at'
    )
    search_fields = ('address', 'city', 'state', 'zip_code')
    list_filter = ('state', 'city', 'fetched_at')
    ordering = ('-fetched_at',)