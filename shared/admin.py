from django.contrib import admin
from .models import Keyword

# Register your models here.

@admin.register(Keyword)
class KeywordAdmin(admin.ModelAdmin):
    list_display = ('text', 'is_active', 'created_at')
    search_fields = ('text',)