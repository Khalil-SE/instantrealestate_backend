# subscriptions/urls.py
from django.urls import path
from .views import SubscriptionPlanListView, CurrentSubscriptionView,SubscriptionHistoryView, CreateCheckoutSessionView, StripeWebhookView, CancelSubscriptionView, OpenBillingPortalView

urlpatterns = [
    path('plans/', SubscriptionPlanListView.as_view(), name='subscription-plans'),
    path("me/", CurrentSubscriptionView.as_view(), name="subscription-me"),
    path("history/", SubscriptionHistoryView.as_view()),
    path("cancel/", CancelSubscriptionView.as_view(), name="subscription-cancel"),
    path("open-billing-portal/", OpenBillingPortalView.as_view(), name="billing-portal"),

    path('create-checkout-session/', CreateCheckoutSessionView.as_view(), name='create-checkout-session'),
    path('webhook/', StripeWebhookView.as_view(), name='stripe-webhook'),  
]
