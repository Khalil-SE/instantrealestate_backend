# subscriptions/models.py

from django.db import models
from django.conf import settings

class SubscriptionPlan(models.Model):
    PLAN_DURATION_CHOICES = (
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    )

    name = models.CharField(max_length=100, unique=True)
    plan_duration = models.CharField(max_length=10, choices=PLAN_DURATION_CHOICES)
    stripe_product_id = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.plan_duration})"


class Subscription(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    stripe_customer_id = models.CharField(max_length=255)
    stripe_subscription_id = models.CharField(max_length=255)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=50)  # e.g., active, canceled, incomplete, etc.
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.plan.name}"


class SubscriptionHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    stripe_invoice_id = models.CharField(max_length=255)
    amount_paid = models.DecimalField(max_digits=8, decimal_places=2)
    currency = models.CharField(max_length=10)
    paid_at = models.DateTimeField()
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True)

    invoice_pdf = models.URLField(blank=True, null=True)  
    hosted_invoice_url = models.URLField(blank=True, null=True)  

    def __str__(self):
        return f"Invoice {self.stripe_invoice_id} for {self.user.email}"
