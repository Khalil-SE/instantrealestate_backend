from django.contrib import admin
from .models import InstaBot, PublicReplyTemplate, PublicReplyContent

# Register your models here.
@admin.register(InstaBot)
class InstaBotAdmin(admin.ModelAdmin):
    list_display = ('keyword', 'user', 'title', 'status', 'created_at')
    search_fields = ('title', 'keyword__text')

@admin.register(PublicReplyTemplate)
class PublicReplyTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'created_at')
    search_fields = ('name',)

@admin.register(PublicReplyContent)
class PublicReplyContentAdmin(admin.ModelAdmin):
    list_display = ('template', 'text')
    search_fields = ('content',)