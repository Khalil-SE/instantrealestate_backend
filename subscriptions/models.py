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
    stripe_price_id = models.CharField(max_length=255, unique=True)
    amount = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    currency = models.CharField(max_length=10, default='usd')
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.plan_duration})"

class Subscription(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    stripe_customer_id = models.CharField(max_length=255)
    stripe_subscription_id = models.CharField(max_length=255)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True)
    scheduled_plan = models.ForeignKey(
        SubscriptionPlan, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='scheduled_subscriptions'
    )

    status = models.CharField(max_length=50)  # active, canceled, incomplete, etc.
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)

    started_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Invoice fields
    latest_invoice_id = models.CharField(max_length=255, blank=True, null=True)
    latest_invoice_url = models.URLField(blank=True, null=True)
    latest_invoice_pdf = models.URLField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.email} - {self.plan.name if self.plan else 'No Plan'}"

class PendingSubscription(models.Model):
    email = models.EmailField()
    stripe_customer_id = models.CharField(max_length=255)
    stripe_subscription_id = models.CharField(max_length=255, unique=True)
    stripe_payment_intent_id = models.CharField(max_length=255)
    client_secret = models.CharField(max_length=255)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True)
    is_confirmed = models.BooleanField(default=False)
    status = models.CharField(max_length=50, default='pending')  # pending, confirmed, succeeded
    created_at = models.DateTimeField(auto_now_add=True)

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







# subscriptions/models.py

# from django.db import models
# from django.conf import settings

# class SubscriptionPlan(models.Model):
#     PLAN_DURATION_CHOICES = (
#         ('monthly', 'Monthly'),
#         ('yearly', 'Yearly'),
#     )

#     name = models.CharField(max_length=100, unique=True)
#     plan_duration = models.CharField(max_length=10, choices=PLAN_DURATION_CHOICES)
#     stripe_price_id = models.CharField(max_length=255, unique=True)
#     description = models.TextField(blank=True)

#     def __str__(self):
#         return f"{self.name} ({self.plan_duration})"

# class Subscription(models.Model):
#     user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
#     stripe_customer_id = models.CharField(max_length=255)
#     stripe_subscription_id = models.CharField(max_length=255)
#     plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True)
#     scheduled_plan = models.ForeignKey(
#         SubscriptionPlan, null=True, blank=True,
#         on_delete=models.SET_NULL,
#         related_name='scheduled_subscriptions'
#     )

#     status = models.CharField(max_length=50)  # active, canceled, incomplete, etc.
#     current_period_start = models.DateTimeField(null=True, blank=True)
#     current_period_end = models.DateTimeField(null=True, blank=True)
#     cancel_at_period_end = models.BooleanField(default=False)

#     started_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     # Fields for invoice management
#     latest_invoice_id = models.CharField(max_length=255, blank=True, null=True)
#     latest_invoice_url = models.URLField(blank=True, null=True)
#     latest_invoice_pdf = models.URLField(blank=True, null=True)

#     def __str__(self):
#         return f"{self.user.email} - {self.plan.name if self.plan else 'No Plan'}"



# # # This model is used to store pending subscriptions before confirmation
# class PendingSubscription(models.Model):
#     email = models.EmailField()
#     stripe_customer_id = models.CharField(max_length=255)
#     stripe_subscription_id = models.CharField(max_length=255, unique=True)
#     stripe_payment_intent_id = models.CharField(max_length=255)
#     client_secret = models.CharField(max_length=255)
#     is_confirmed = models.BooleanField(default=False)
#     status = models.CharField(max_length=50, default='pending')  # pending, confirmed, canceled, etc.
#     created_at = models.DateTimeField(auto_now_add=True)




# class SubscriptionHistory(models.Model):
#     user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
#     stripe_invoice_id = models.CharField(max_length=255)
#     amount_paid = models.DecimalField(max_digits=8, decimal_places=2)
#     currency = models.CharField(max_length=10)
#     paid_at = models.DateTimeField()
#     plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True)

#     invoice_pdf = models.URLField(blank=True, null=True)  
#     hosted_invoice_url = models.URLField(blank=True, null=True)  

#     def __str__(self):
#         return f"Invoice {self.stripe_invoice_id} for {self.user.email}"



# class SubscriptionPlanChangeLog(models.Model):
#     user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
#     old_plan = models.ForeignKey(SubscriptionPlan, related_name='old_plans', on_delete=models.SET_NULL, null=True)
#     new_plan = models.ForeignKey(SubscriptionPlan, related_name='new_plans', on_delete=models.SET_NULL, null=True)
#     changed_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.user.email} changed from {self.old_plan} to {self.new_plan} on {self.changed_at}"
