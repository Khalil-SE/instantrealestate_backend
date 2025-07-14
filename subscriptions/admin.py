from django.contrib import admin
from .models import SubscriptionPlan, Subscription, PendingSubscription, SubscriptionHistory

# Register your models here.
admin.site.register(SubscriptionPlan)
admin.site.register(Subscription)
admin.site.register(PendingSubscription)
admin.site.register(SubscriptionHistory)
# admin.site.register(SubscriptionPlanChangeLog)