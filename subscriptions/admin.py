from django.contrib import admin
from .models import SubscriptionPlan, Subscription, SubscriptionHistory

# Register your models here.
admin.site.register(SubscriptionPlan)
admin.site.register(Subscription)
admin.site.register(SubscriptionHistory)