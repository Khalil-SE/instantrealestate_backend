# subscriptions/urls.py
from django.urls import path
# from .views import SubscriptionPlanListView, CurrentSubscriptionView,SubscriptionHistoryView, CreateCheckoutSessionView, StripeWebhookView, CancelSubscriptionView, OpenBillingPortalView
from .views import SubscriptionPlanListView, CurrentSubscriptionView, SubscriptionHistoryView, CancelSubscriptionView, ResumeSubscriptionView, StartAuthenticatedSubscriptionView, SchedulePlanChangeView, OpenBillingPortalView
from .views import CreateSubscriptionPaymentIntentView, ConfirmSignupAfterPaymentView, StripeWebhookView

urlpatterns = [
    path('plans/', SubscriptionPlanListView.as_view(), name='subscription-plans'),
    path("me/", CurrentSubscriptionView.as_view(), name="subscription-me"),
    path("history/", SubscriptionHistoryView.as_view()),
    path("cancel/", CancelSubscriptionView.as_view(), name="subscription-cancel"),
    path("resume/", ResumeSubscriptionView.as_view(), name="resume-subscription"),
    path("start/", StartAuthenticatedSubscriptionView.as_view(), name="start-subscription"),
    path("schedule-plan-change/", SchedulePlanChangeView.as_view(), name="schedule-plan-change"),
    path("open-billing-portal/", OpenBillingPortalView.as_view(), name="billing-portal"),

    # path('create-checkout-session/', CreateCheckoutSessionView.as_view(), name='create-checkout-session'),
    path('webhook/', StripeWebhookView.as_view(), name='stripe-webhook'),  



    # new subscription endpoints
    path('start-subscription/', CreateSubscriptionPaymentIntentView.as_view(), name='start-subscription'),
    path('confirm-signup/', ConfirmSignupAfterPaymentView.as_view(), name='confirm-signup-after-payment'),

]
