"property/models.py"
from django.db import models
from django.contrib.auth import get_user_model
from shared.models import Keyword

User = get_user_model()

class Property(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    keyword = models.OneToOneField(Keyword, on_delete=models.SET_NULL, null=True, blank=True, related_name='property')

    url = models.URLField()
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=20)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    home_type = models.CharField(max_length=100)
    beds = models.PositiveIntegerField()
    baths = models.PositiveIntegerField()
    sqft = models.PositiveIntegerField()
    lot_size = models.FloatField()
    description = models.TextField()
    ai_generated_description = models.TextField(blank=True)

    button1_text = models.CharField(max_length=50, null=True, blank=True)
    button1_url = models.URLField(blank=True)
    button2_text = models.CharField(max_length=50, null=True, blank=True)
    button2_url = models.URLField(blank=True)

    image_url = models.URLField(null=True, blank=True)  # BunnyCDN image URL
    email_recipients = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Property - {self.keyword.text if self.keyword else 'No Keyword'}"



class LoftyProperty(models.Model):
    listing_id = models.CharField(max_length=100, unique=True)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=20, null=True, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    beds = models.FloatField(null=True, blank=True)
    baths = models.FloatField(null=True, blank=True)
    sqft = models.FloatField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    image_url = models.URLField(null=True, blank=True)
    raw_data = models.JSONField()  # Full Lofty payload
    fetched_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lofty_listings')
    is_selected = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.listing_id} - {self.address}"