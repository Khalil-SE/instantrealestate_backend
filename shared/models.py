# core/models/keyword.py

from django.db import models
from django.utils import timezone

class Keyword(models.Model):
    text = models.CharField(max_length=100, unique=True)

    is_active = models.BooleanField(default=True)  # In case we want to soft-disable reuse
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"#{self.text}"
