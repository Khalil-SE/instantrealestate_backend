# import stripe
# # import json
# import logging
# import time
# from django.conf import settings

# from rest_framework.response import Response
# from rest_framework.permissions import IsAuthenticated
# from rest_framework import status
# from .models import SubscriptionPlan, Subscription, SubscriptionHistory
# from system.models import SystemSettings  

# from django.views.decorators.csrf import csrf_exempt
# from django.utils.decorators import method_decorator

# # from django.utils.timezone import make_aware
# from django.utils.timezone import now
# from datetime import datetime
# from django.utils.timezone import make_aware
# from django.contrib.auth import get_user_model
# from django.db.utils import IntegrityError


# # subscriptions/views.py (add this)

# class CurrentSubscriptionView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request):
#         subscription = Subscription.objects.filter(user=request.user).first()

#         if not subscription:
#             return Response({"has_subscription": False})

#         return Response({
#             "has_subscription": True,
#             "status": subscription.status,
#             "plan": subscription.plan.name,
#             "cancel_at_period_end": subscription.cancel_at_period_end,
#             "current_period_start": subscription.current_period_start,
#             "current_period_end": subscription.current_period_end,
#         })

# class CurrentSubscriptionView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request):
#         subscription = Subscription.objects.filter(user=request.user).first()
#         if not subscription or subscription.status != "active":
#             return Response({"has_subscription": False})

#         return Response({
#             "has_subscription": True,
#             "status": subscription.status,
#             "plan": subscription.plan.name,
#             "cancel_at_period_end": subscription.cancel_at_period_end,
#             "current_period_start": subscription.current_period_start,
#             "current_period_end": subscription.current_period_end,
#         })


# subscriptions/views.py
# class CancelSubscriptionView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         user = request.user
#         try:
#             subscription = Subscription.objects.get(user=user)
#             stripe.api_key = SystemSettings.get_solo().stripe_api_key

#             stripe.Subscription.modify(
#                 subscription.stripe_subscription_id,
#                 cancel_at_period_end=True
#             )

#             subscription.cancel_at_period_end = True
#             subscription.save()

#             return Response({"success": True, "message": "Subscription marked to cancel at period end."})
#         except Subscription.DoesNotExist:
#             return Response({"error": "No active subscription found."}, status=404)
#         except Exception as e:
#             return Response({"error": str(e)}, status=500)

# subscriptions/views.py


# class CreateCheckoutSessionView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         plan_id = request.data.get("plan_id")
#         if not plan_id:
#             return Response({"detail": "Plan ID is required."}, status=status.HTTP_400_BAD_REQUEST)

#         # Retrieve the selected plan
#         try:
#             plan = SubscriptionPlan.objects.get(id=plan_id)
#         except SubscriptionPlan.DoesNotExist:
#             return Response({"detail": "Invalid subscription plan."}, status=status.HTTP_404_NOT_FOUND)

#         # Load Stripe API Key from system settings
#         settings_obj = SystemSettings.get_solo()
#         stripe.api_key = settings_obj.stripe_api_key

#         try:
#             # Create the Stripe Checkout Session
#             session = stripe.checkout.Session.create(
#                 payment_method_types=["card"],
#                 mode="subscription",
#                 line_items=[{
#                     "price": plan.stripe_product_id,
#                     "quantity": 1,
#                 }],
#                 customer_email=request.user.email,
#                 success_url=request.build_absolute_uri(settings_obj.stripe_return_url),
#                 cancel_url=request.build_absolute_uri(settings_obj.stripe_return_url),
#                 metadata={
#                     "user_id": str(request.user.id),
#                     "plan_name": plan.name,
#                 }
#             )

#             return Response({"checkout_url": session.url}, status=status.HTTP_200_OK)

#         except Exception as e:
#             return Response(
#                 {"detail": f"Failed to create checkout session: {str(e)}"},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
#             )

# logger = logging.getLogger("stripe_webhooks")
# User = get_user_model()

# ALLOWED_EVENTS = {
#     "checkout.session.completed",
#     "invoice.payment_succeeded",
#     "invoice.payment_failed",
#     "customer.subscription.updated",
#     "customer.subscription.deleted",
# }


# @method_decorator(csrf_exempt, name="dispatch")
# class StripeWebhookView(APIView):
#     def post(self, request, *args, **kwargs):
#         settings_obj = SystemSettings.get_solo()
#         stripe.api_key = settings_obj.stripe_api_key
#         stripe.api_version = "2024-04-10"  #  Explicit version locking

#         webhook_secret = settings_obj.stripe_webhook_secret
#         payload = request.body
#         sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

#         try:
#             event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
#         except (ValueError, stripe.error.SignatureVerificationError) as e:
#             logger.error(f"Webhook verification failed: {e}")
#             return Response(status=400)

#         event_type = event["type"]
#         print(f"Stripe event received: {event_type}")

#         if event_type not in ALLOWED_EVENTS:
#             print(f"Ignoring untracked event type: {event_type}")
#             return Response(status=200)

#         try:
#             if event_type == "checkout.session.completed":
#                 self._handle_checkout_completed(event)
#             elif event_type == "invoice.payment_succeeded":
#                 self._handle_invoice_payment_succeeded(event)
#             elif event_type == "invoice.payment_failed":
#                 self._handle_invoice_payment_failed(event)
#             elif event_type == "customer.subscription.updated":
#                 self._handle_subscription_updated(event)
#             elif event_type == "customer.subscription.deleted":
#                 self._handle_subscription_deleted(event)
#         except Exception as e:
#             logger.error(f"Error processing {event_type}: {str(e)}", exc_info=True)
#             return Response(status=500)

#         return Response(status=200)

#     def _handle_checkout_completed(self, event):
#         session = event["data"]["object"]
#         metadata = session.get("metadata", {})
#         user_id = metadata.get("user_id")
#         plan_name = metadata.get("plan_name")
#         customer_id = session.get("customer")
#         subscription_id = session.get("subscription")

#         if not all([user_id, plan_name, customer_id, subscription_id]):
#             logger.warning("Incomplete metadata in checkout.session.completed")
#             return

#         plan = SubscriptionPlan.objects.filter(name=plan_name).first()
#         if not plan:
#             logger.warning(f"Plan not found: {plan_name}")
#             return

#         stripe_subscription = stripe.Subscription.retrieve(subscription_id)
#         items = stripe_subscription.get("items", {}).get("data", [])
#         if not items:
#             logger.warning("No items found in subscription.")
#             return

#         item = items[0]
#         start_ts = item.get("current_period_start")
#         end_ts = item.get("current_period_end")

#         if not (start_ts and end_ts):
#             logger.warning("Missing start or end timestamp in subscription item.")
#             return

#         start_dt = make_aware(datetime.fromtimestamp(start_ts))
#         end_dt = make_aware(datetime.fromtimestamp(end_ts))
#         cancel_at_period_end = stripe_subscription.get("cancel_at_period_end", False)

#         Subscription.objects.update_or_create(
#             user_id=user_id,
#             defaults={
#                 "plan": plan,
#                 "stripe_customer_id": customer_id,
#                 "stripe_subscription_id": subscription_id,
#                 "status": "active",
#                 "current_period_start": start_dt,
#                 "current_period_end": end_dt,
#                 "cancel_at_period_end": cancel_at_period_end,
#             },
#         )
#         print(f"Subscription created or updated for user {user_id}")

#     def _handle_invoice_payment_succeeded(self, event):
#         invoice = event["data"]["object"]
#         customer_id = invoice.get("customer")

#         # Retry once after 2 seconds if subscription is not yet available
#         subscription = Subscription.objects.filter(stripe_customer_id=customer_id).first()
#         if not subscription:
#             logger.warning(f"No subscription found for customer {customer_id}, retrying in 2 seconds...")
#             time.sleep(2)
#             subscription = Subscription.objects.filter(stripe_customer_id=customer_id).first()

#             if not subscription:
#                 logger.warning(f"Retry failed: still no subscription for customer {customer_id}")
#                 return

#         user = subscription.user
#         plan = subscription.plan

#         line = invoice["lines"]["data"][0]
#         paid_ts = invoice.get("status_transitions", {}).get("paid_at")
#         paid_at = make_aware(datetime.fromtimestamp(paid_ts)) if paid_ts else now()

#         SubscriptionHistory.objects.create(
#             user=user,
#             stripe_invoice_id=invoice["id"],
#             amount_paid=invoice.get("amount_paid") / 100,
#             currency=invoice.get("currency"),
#             paid_at=paid_at,
#             plan=plan,
#         )
#         print(f"Subscription history recorded for {user.email}")

#     def _handle_invoice_payment_failed(self, event):
#         invoice = event["data"]["object"]
#         customer_id = invoice.get("customer")

#         subscription = Subscription.objects.filter(stripe_customer_id=customer_id).first()
#         if not subscription:
#             logger.warning(f"Payment failed but no local subscription found for customer {customer_id}")
#             return

#         subscription.status = "incomplete"
#         subscription.save()
#         print(f"Subscription marked as incomplete due to payment failure for customer {customer_id}")

#     def _handle_subscription_updated(self, event):
#         stripe_sub = event["data"]["object"]
#         customer_id = stripe_sub.get("customer")
#         cancel_at_period_end = stripe_sub.get("cancel_at_period_end", False)
#         current_period_start = stripe_sub.get("current_period_start")
#         current_period_end = stripe_sub.get("current_period_end")

#         subscription = Subscription.objects.filter(stripe_customer_id=customer_id).first()
#         if not subscription:
#             logger.warning(f"No local subscription found to update for customer {customer_id}")
#             return

#         subscription.cancel_at_period_end = cancel_at_period_end
#         if current_period_start and current_period_end:
#             subscription.current_period_start = make_aware(datetime.fromtimestamp(current_period_start))
#             subscription.current_period_end = make_aware(datetime.fromtimestamp(current_period_end))
#         subscription.save()
#         print(f"Subscription updated for customer {customer_id}")

#     def _handle_subscription_deleted(self, event):
#         stripe_sub = event["data"]["object"]
#         customer_id = stripe_sub.get("customer")

#         subscription = Subscription.objects.filter(stripe_customer_id=customer_id).first()
#         if not subscription:
#             logger.warning(f"Tried to delete nonexistent subscription for customer {customer_id}")
#             return

#         subscription.status = "canceled"
#         subscription.save()
#         print(f"Subscription marked as canceled for customer {customer_id}")







# subscriptions/views.py
# New Flow of Subscription
import logging
import time
from datetime import datetime
from django.utils.timezone import make_aware, now
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator


from django.conf import settings
from django.contrib.auth import get_user_model

from rest_framework.views import APIView
from django.http import HttpResponse, JsonResponse
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from django.db import transaction


from users.models import CustomUser
from users.serializers import UserDetailSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import make_password
from subscriptions.models import Subscription, PendingSubscription, SubscriptionPlan, SubscriptionHistory
from system.models import SystemSettings

import stripe

from rest_framework.generics import ListAPIView

from .models import SubscriptionPlan
from .serializers import SubscriptionPlanSerializer

# stripe.api_key = SystemSettings.get_solo().stripe_api_key

User = get_user_model()

class SubscriptionPlanListView(ListAPIView):
    queryset = SubscriptionPlan.objects.all().order_by("id")
    serializer_class = SubscriptionPlanSerializer
    permission_classes = []  # Public access — no auth required

# # # For the current subscription Of logged in user
# class CurrentSubscriptionView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request):
#         try:
#             subscription = Subscription.objects.get(user=request.user)
#         except Subscription.DoesNotExist:
#             return Response({
#                 "has_subscription": False,
#                 "message": "No subscription found."
#             })

#         # Check if current period is valid and status is active
#         is_active = (
#             subscription.status == "active" and
#             subscription.current_period_end and
#             subscription.current_period_end > now()
#         )

#         return Response({
#             "has_subscription": True,
#             "is_active": is_active,
#             "status": subscription.status,
#             "plan": subscription.plan.name if subscription.plan else None,
#             "cancel_at_period_end": subscription.cancel_at_period_end,
#             "current_period_start": subscription.current_period_start,
#             "current_period_end": subscription.current_period_end,
#             "latest_invoice_id": subscription.latest_invoice_id,
#             "latest_invoice_url": subscription.latest_invoice_url,
#             "latest_invoice_pdf": subscription.latest_invoice_pdf,
#         })

# class CurrentSubscriptionView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request):
#         try:
#             subscription = Subscription.objects.get(user=request.user)
#         except Subscription.DoesNotExist:
#             return Response({
#                 "has_subscription": False,
#                 "message": "No subscription found."
#             })

#         # Default check: Stripe status and date validity
#         is_active = (
#             subscription.status == "active" and
#             subscription.current_period_end and
#             subscription.current_period_end > now()
#         )
#         # print(f"Subscription status: {subscription.status}, is_active: {is_active}")
#         # Handle fallback if status is incomplete
#         if not is_active and subscription.status == "incomplete":
#             # Check for succeeded pending subscription
#             pending = PendingSubscription.objects.filter(
#                 stripe_subscription_id=subscription.stripe_subscription_id,
#                 email=request.user.email,
#                 is_confirmed=True,
#                 status="succeeded"
#             ).first()
#             # print(f"subscription.stripe_subscription_id :{subscription.stripe_subscription_id}, request.user.email: {request.user.email}")
#             # print(f"is_active: {is_active}, pending: {pending}")
#             if pending and subscription.current_period_end and subscription.current_period_end > now():
#                 is_active = True  # Treat as active fallback
#             # print(is_active)
#         return Response({
#             "has_subscription": True,
#             "is_active": is_active,
#             "status": subscription.status,
#             "plan": subscription.plan.name if subscription.plan else None,
#             "cancel_at_period_end": subscription.cancel_at_period_end,
#             "current_period_start": subscription.current_period_start,
#             "current_period_end": subscription.current_period_end,
#             "latest_invoice_id": subscription.latest_invoice_id,
#             "latest_invoice_url": subscription.latest_invoice_url,
#             "latest_invoice_pdf": subscription.latest_invoice_pdf,
#         })

class CurrentSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            subscription = Subscription.objects.get(user=request.user)
        except Subscription.DoesNotExist:
            return Response({"error": "No subscription found."}, status=404)

        return Response({
            "is_active": (
                (subscription.status == "active" or subscription.status == "incomplete") and
                subscription.current_period_end and
                subscription.current_period_end > now()
            ),
            "status": subscription.status,
            "plan": subscription.plan.name if subscription.plan else None,
            "scheduled_plan": subscription.scheduled_plan.name if subscription.scheduled_plan else None,
            "cancel_at_period_end": subscription.cancel_at_period_end,
            "current_period_start": subscription.current_period_start,
            "current_period_end": subscription.current_period_end,
            "latest_invoice_id": subscription.latest_invoice_id,
            "latest_invoice_url": subscription.latest_invoice_url,
            "latest_invoice_pdf": subscription.latest_invoice_pdf,
        })








class CancelSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        try:
            subscription = Subscription.objects.get(user=user)
        except Subscription.DoesNotExist:
            return Response({"error": "No active subscription found."}, status=404)

        stripe.api_key = SystemSettings.get_solo().stripe_api_key

        try:
            stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=True
            )
            subscription.cancel_at_period_end = True
            subscription.save()
            return Response({"message": "Subscription will be canceled at period end."})
        except Exception as e:
            return Response({"error": str(e)}, status=400)


class ResumeSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        try:
            subscription = Subscription.objects.get(user=user)
        except Subscription.DoesNotExist:
            return Response({"error": "Subscription not found."}, status=404)

        if not subscription.cancel_at_period_end:
            return Response({"message": "Subscription is not scheduled to cancel."}, status=400)

        stripe.api_key = SystemSettings.get_solo().stripe_api_key

        try:
            stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=False
            )
            subscription.cancel_at_period_end = False
            subscription.save()
            return Response({"message": "Subscription resumed successfully."})
        except Exception as e:
            return Response({"error": str(e)}, status=400)


class OpenBillingPortalView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        try:
            systemObject = SystemSettings.get_solo()
            subscription = Subscription.objects.get(user=user)
            stripe.api_key = systemObject.stripe_api_key
            return_url = request.build_absolute_uri(systemObject.stripe_return_url)  # Adjust if needed

            portal_session = stripe.billing_portal.Session.create(
                customer=subscription.stripe_customer_id,
                return_url=return_url
            )

            return Response({"url": portal_session.url})
        except Exception as e:
            return Response({"error": str(e)}, status=500)



class SubscriptionHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        history = SubscriptionHistory.objects.filter(user=request.user).order_by("-paid_at")
        data = [
            {
                "paid_at": entry.paid_at,
                "amount_paid": float(entry.amount_paid),
                "pdf_url": entry.invoice_pdf,
                "hosted_url": entry.hosted_invoice_url,
            }
            for entry in history
        ]
        return Response(data)



# class CreateSubscriptionPaymentIntentView(APIView):
#     permission_classes = [AllowAny]

#     def post(self, request):
#         data = request.data
#         email = data.get("email")
#         plan_id = data.get("plan_id")

#         if not email or not plan_id:
#             return Response({"error": "Email and plan_id are required."}, status=400)

#         try:
#             plan = SubscriptionPlan.objects.get(id=plan_id)
#         except SubscriptionPlan.DoesNotExist:
#             return Response({"error": "Invalid plan_id."}, status=404)

#         stripe.api_key = SystemSettings.get_solo().stripe_api_key

#         try:
#             customer = stripe.Customer.create(email=email)
#             # logging.info(f"Customer created: {customer.id}")
            
#             subscription = stripe.Subscription.create(
#                 customer=customer.id,
#                 items=[{"price": plan.stripe_price_id}],
#                 payment_behavior="default_incomplete",
#                 payment_settings={"payment_method_types": ["card"]},
#                 expand=["latest_invoice.payment_intent"]
#             )
#             payment_intent = stripe.PaymentIntent.create(
#                 amount=subscription.plan.amount,  # Make sure this is in cents
#                 currency=subscription.plan.currency,
#                 customer=customer.id,
#                 payment_method_types=['card'],
#                 metadata={'subscription_id': subscription.id}
#             )

#             return Response({
#                 "client_secret": payment_intent.client_secret,
#                 "customer_id": customer.id,
#                 "subscription_id": subscription.id
#             })
            

#         except stripe.error.StripeError as e:
#             print(f"Stripe error: {str(e)}")
#             return Response({"error": str(e)}, status=400)
#         except Exception as e:
#             print(f"Unexpected error: {str(e)}")
#             return Response({"error": str(e)}, status=500)



# class CreateSubscriptionPaymentIntentView(APIView):
#     permission_classes = [AllowAny]

#     def post(self, request):
#         data = request.data
#         email = data.get("email")
#         plan_id = data.get("plan_id")

#         if not email or not plan_id:
#             return Response({"error": "Email and plan_id are required."}, status=400)

#         try:
#             plan = SubscriptionPlan.objects.get(id=plan_id)
#         except SubscriptionPlan.DoesNotExist:
#             return Response({"error": "Invalid plan_id."}, status=404)

#         stripe.api_key = SystemSettings.get_solo().stripe_api_key

#         try:
#             # Step 1: Create customer
#             customer = stripe.Customer.create(email=email)

#             # Step 2: Create subscription
#             subscription = stripe.Subscription.create(
#                 customer=customer.id,
#                 items=[{"price": plan.stripe_price_id}],
#                 payment_behavior="default_incomplete",
#                 expand=["latest_invoice"],
#                 payment_settings={"payment_method_types": ["card"]},
                
#             )

#             # import json
#             # print("Full subscription object:", json.dumps(subscription, indent=2, default=str))

#             invoice_id = subscription.get("latest_invoice", {}).get("id")
#             if not invoice_id:
#                 return Response({"error": "Invoice not created yet."}, status=400)

#             # Step 3: Retrieve invoice and expand payment intent
#             invoice = stripe.Invoice.retrieve(invoice_id, expand=["payment_intent"])

#             # import pprint
#             # pprint.pprint(invoice)

#             payment_intent = invoice.get("payment_intent")

#             # Step 4: Fallback if missing
#             if not payment_intent:
#                 # Fallback: create manual PaymentIntent (not ideal, but fallback)
#                 payment_intent = stripe.PaymentIntent.create(
#                     amount=subscription.plan.amount,  # or plan.amount if stored as cents
#                     currency=subscription.plan.currency,
#                     customer=customer.id,
#                     metadata={"subscription_id": subscription.id},
#                     payment_method_types=["card"]
#                 )

#             # Step 5: Save PendingSubscription
#             PendingSubscription.objects.filter(
#                 email=email,
#                 stripe_subscription_id=subscription.id
#             ).delete()

#             PendingSubscription.objects.create(
#                 email=email,
#                 stripe_customer_id=customer.id,
#                 stripe_subscription_id=subscription.id,
#                 stripe_payment_intent_id=payment_intent.id,
#                 client_secret=payment_intent.client_secret,
#             )

#             return Response({
#                 "client_secret": payment_intent.client_secret,
#                 "customer_id": customer.id,
#                 "subscription_id": subscription.id,
#             })

#         except stripe.error.StripeError as e:
#             return Response({"error": str(e)}, status=400)
#         except Exception as e:
#             return Response({"error": str(e)}, status=500)

# class CreateSubscriptionPaymentIntentView(APIView):
#     permission_classes = [AllowAny]

#     def post(self, request):
#         data = request.data
#         email = data.get("email")
#         plan_id = data.get("plan_id")

#         if not email or not plan_id:
#             return Response({"error": "Email and plan_id are required."}, status=400)

#         try:
#             plan = SubscriptionPlan.objects.get(id=plan_id)
#         except SubscriptionPlan.DoesNotExist:
#             return Response({"error": "Invalid plan_id."}, status=404)

#         stripe.api_key = SystemSettings.get_solo().stripe_api_key

#         try:
#             # Step 1: Create customer (optional: check if already exists)
#             customer = stripe.Customer.create(email=email)

#             # Step 2: Create subscription with incomplete payment behavior
#             subscription = stripe.Subscription.create(
#                 customer=customer.id,
#                 items=[{"price": plan.stripe_price_id}],
#                 payment_behavior="default_incomplete",
#                 payment_settings={"payment_method_types": ["card"]},
#                 expand=["latest_invoice", "latest_invoice.payment_intent"]
#             )

#             latest_invoice = subscription.get("latest_invoice")
#             if not latest_invoice:
#                 return Response({"error": "Invoice not generated yet."}, status=400)

#             payment_intent = latest_invoice.get("payment_intent")
#             if not payment_intent:
#                 # Fallback: create manual PaymentIntent
#                 payment_intent = stripe.PaymentIntent.create(
#                     amount=subscription.plan.amount,
#                     currency=subscription.plan.currency,
#                     # amount = 2000,
#                     # currency="usd",  # Adjust as needed
#                     customer=customer.id,
#                     payment_method_types=["card"],
#                     metadata={"subscription_id": subscription.id}
#                 )

#             # Step 3: Store or update PendingSubscription
#             PendingSubscription.objects.filter(
#                 email=email,
#                 stripe_subscription_id=subscription.id
#             ).delete()

#             PendingSubscription.objects.create(
#                 email=email,
#                 stripe_customer_id=customer.id,
#                 stripe_subscription_id=subscription.id,
#                 stripe_payment_intent_id=payment_intent["id"],
#                 client_secret=payment_intent["client_secret"],
#                 status="pending"
#             )

#             return Response({
#                 "client_secret": payment_intent["client_secret"],
#                 "customer_id": customer.id,
#                 "subscription_id": subscription.id,
#             })

#         except stripe.error.StripeError as e:
#             return Response({"error": f"Stripe error: {str(e)}"}, status=400)

#         except Exception as e:
#             return Response({"error": f"Unexpected error: {str(e)}"}, status=500)

class CreateSubscriptionPaymentIntentView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data
        email = data.get("email")
        plan_id = data.get("plan_id")

        if not email or not plan_id:
            return Response({"error": "Email and plan_id are required."}, status=400)

        try:
            plan = SubscriptionPlan.objects.get(id=plan_id)
        except SubscriptionPlan.DoesNotExist:
            return Response({"error": "Invalid plan_id."}, status=404)

        stripe.api_key = SystemSettings.get_solo().stripe_api_key

        try:
            # Step 1: Create Stripe Customer
            customer = stripe.Customer.create(email=email)

            # Step 2: Create Stripe Subscription
            stripe_sub = stripe.Subscription.create(
                customer=customer.id,
                items=[{"price": plan.stripe_price_id}],
                payment_behavior="default_incomplete",
                payment_settings={"payment_method_types": ["card"]},
                expand=["latest_invoice", "latest_invoice.payment_intent"]
            )

            # Step 3: Get PaymentIntent or create fallback
            latest_invoice = stripe_sub.get("latest_invoice", {})
            payment_intent = latest_invoice.get("payment_intent")

            if not payment_intent:
                print("⚠️ PaymentIntent not found. Creating fallback PaymentIntent...")
                payment_intent = stripe.PaymentIntent.create(
                    amount=int(plan.amount * 100),
                    currency=plan.currency.lower(),
                    customer=customer.id,
                    payment_method_types=["card"],
                    metadata={"subscription_id": stripe_sub.id}
                )

            # Step 4: Store PendingSubscription
            PendingSubscription.objects.filter(
                email=email,
                stripe_subscription_id=stripe_sub.id
            ).delete()

            PendingSubscription.objects.create(
                email=email,
                stripe_customer_id=customer.id,
                stripe_subscription_id=stripe_sub.id,
                stripe_payment_intent_id=payment_intent["id"],
                client_secret=payment_intent["client_secret"],
                status="pending"
            )

            return Response({
                "client_secret": payment_intent["client_secret"],
                "customer_id": customer.id,
                "subscription_id": stripe_sub.id,
            })

        except stripe.error.StripeError as e:
            return Response({"error": f"Stripe error: {str(e)}"}, status=400)

        except Exception as e:
            return Response({"error": f"Unexpected error: {str(e)}"}, status=500)










# class StartAuthenticatedSubscriptionView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         plan_id = request.data.get("plan_id")
#         user = request.user

#         if not plan_id:
#             return Response({"error": "Missing plan_id."}, status=400)

#         try:
#             plan = SubscriptionPlan.objects.get(id=plan_id)
#         except SubscriptionPlan.DoesNotExist:
#             return Response({"error": "Invalid plan ID."}, status=404)

#         stripe.api_key = SystemSettings.get_solo().stripe_api_key

#         try:
#             # Check for existing subscription
#             subscription = Subscription.objects.filter(user=user).first()

#             if subscription and subscription.status in ["active", "incomplete", "trialing"]:
#                 return Response({"error": "You already have an active or ongoing subscription."}, status=400)

#             # Step 1: Create or reuse Stripe customer
#             if subscription and subscription.stripe_customer_id:
#                 customer_id = subscription.stripe_customer_id
#             else:
#                 customer = stripe.Customer.create(email=user.email)
#                 customer_id = customer.id

#                 # Create or reuse local Subscription record
#                 if subscription:
#                     subscription.stripe_customer_id = customer_id
#                     subscription.status = "incomplete"
#                     subscription.plan = plan
#                 else:
#                     subscription = Subscription.objects.create(
#                         user=user,
#                         plan=plan,
#                         stripe_customer_id=customer_id,
#                         stripe_subscription_id="",
#                         status="incomplete"
#                     )

#                 subscription.save()

#             # Step 2: Create new Stripe Subscription
#             stripe_sub = stripe.Subscription.create(
#                 customer=customer_id,
#                 items=[{"price": plan.stripe_price_id}],
#                 payment_behavior="default_incomplete",
#                 payment_settings={"payment_method_types": ["card"]},
#                 expand=["latest_invoice", "latest_invoice.payment_intent"]
#             )

#             # Step 3: Save Stripe subscription info locally
#             subscription.stripe_subscription_id = stripe_sub.id
#             subscription.plan = plan
#             subscription.status = stripe_sub.status
#             subscription.save()

#             latest_invoice = stripe_sub.get("latest_invoice", {})
#             payment_intent = latest_invoice.get("payment_intent")

#             # Step 4: Fallback if payment_intent is missing
#             if not payment_intent:
#                 print(" PaymentIntent not found. Creating fallback...")
#                 payment_intent = stripe.PaymentIntent.create(
#                     amount=stripe_sub.plan.amount,
#                     currency=stripe_sub.plan.currency.lower(),
#                     customer=customer_id,
#                     payment_method_types=["card"],
#                     metadata={"subscription_id": stripe_sub.id}
#                 )

#             return Response({
#                 "client_secret": payment_intent["client_secret"],
#                 "customer_id": customer_id,
#                 "subscription_id": stripe_sub.id,
#             })

#         except stripe.error.StripeError as e:
#             return Response({"error": f"Stripe error: {str(e)}"}, status=400)
#         except Exception as e:
#             return Response({"error": f"Unexpected error: {str(e)}"}, status=500)

# class StartAuthenticatedSubscriptionView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         plan_id = request.data.get("plan_id")
#         user = request.user

#         if not plan_id:
#             return Response({"error": "Missing plan_id."}, status=400)

#         try:
#             plan = SubscriptionPlan.objects.get(id=plan_id)
#         except SubscriptionPlan.DoesNotExist:
#             return Response({"error": "Invalid plan ID."}, status=404)

#         stripe.api_key = SystemSettings.get_solo().stripe_api_key

#         try:
#             subscription = Subscription.objects.filter(user=user).first()
#             if subscription and subscription.status in ["active", "incomplete"]:
#                 return Response({"error": "You already have a subscription."}, status=400)

#             customer_id = subscription.stripe_customer_id if subscription and subscription.stripe_customer_id else None

#             if not customer_id:
#                 customer = stripe.Customer.create(email=user.email)
#                 customer_id = customer.id

#             # 🔁 Check if an incomplete Stripe subscription already exists
#             existing = stripe.Subscription.list(customer=customer_id, status="incomplete", limit=1).data
#             if existing:
#                 stripe_sub = existing[0]
#             else:
#                 stripe_sub = stripe.Subscription.create(
#                     customer=customer_id,
#                     items=[{"price": plan.stripe_price_id}],
#                     payment_behavior="default_incomplete",
#                     payment_settings={"payment_method_types": ["card"]},
#                     expand=["latest_invoice", "latest_invoice.payment_intent"]
#                 )

#             latest_invoice = stripe_sub.get("latest_invoice", {})
#             payment_intent = latest_invoice.get("payment_intent")

#             if not payment_intent:
#                 payment_intent = stripe.PaymentIntent.create(
#                     amount=int(plan.amount * 100),
#                     currency=plan.currency,
#                     customer=customer_id,
#                     payment_method_types=["card"],
#                     metadata={"subscription_id": stripe_sub.id}
#                 )

#             # Save to Subscription model
#             if not subscription:
#                 subscription = Subscription.objects.create(
#                     user=user,
#                     plan=plan,
#                     stripe_customer_id=customer_id,
#                     stripe_subscription_id=stripe_sub.id,
#                     status=stripe_sub.status
#                 )
#             else:
#                 subscription.plan = plan
#                 subscription.stripe_subscription_id = stripe_sub.id
#                 subscription.status = stripe_sub.status
#                 subscription.save()

#             return Response({
#                 "client_secret": payment_intent["client_secret"],
#                 "customer_id": customer_id,
#                 "subscription_id": stripe_sub.id,
#             })

#         except stripe.error.StripeError as e:
#             return Response({"error": f"Stripe error: {str(e)}"}, status=400)
#         except Exception as e:
#             return Response({"error": f"Unexpected error: {str(e)}"}, status=500)


# class StartAuthenticatedSubscriptionView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         user = request.user
#         plan_id = request.data.get("plan_id")

#         if not plan_id:
#             return Response({"error": "Missing plan_id."}, status=400)

#         try:
#             plan = SubscriptionPlan.objects.get(id=plan_id)
#         except SubscriptionPlan.DoesNotExist:
#             return Response({"error": "Invalid plan ID."}, status=404)

#         stripe.api_key = SystemSettings.get_solo().stripe_api_key

#         try:
#             # Step 1: Get or create Stripe Customer ID
#             existing_sub = Subscription.objects.filter(user=user).first()
#             if existing_sub and existing_sub.stripe_customer_id:
#                 customer_id = existing_sub.stripe_customer_id
#             else:
#                 customer = stripe.Customer.create(email=user.email)
#                 customer_id = customer.id

#             # Step 2: Check for existing subscription
#             existing_pending = PendingSubscription.objects.filter(
#                 email=user.email, is_confirmed=False
#             ).first()

#             if existing_pending:
#                 try:
#                     existing_stripe_sub = stripe.Subscription.retrieve(
#                         existing_pending.stripe_subscription_id,
#                         expand=["latest_invoice", "latest_invoice.payment_intent"]
#                     )
#                     stripe_sub = existing_stripe_sub
#                 except Exception as e:
#                     print(f"⚠️ Could not retrieve existing pending subscription: {e}")
#                     existing_pending.delete()  # Clean up invalid record
#                     stripe_sub = None
#             else:
#                 stripe_sub = None

#             # Step 3: Create new Stripe Subscription if not reused
#             if not stripe_sub:
#                 stripe_sub = stripe.Subscription.create(
#                     customer=customer_id,
#                     items=[{"price": plan.stripe_price_id}],
#                     payment_behavior="default_incomplete",
#                     payment_settings={"payment_method_types": ["card"]},
#                     expand=["latest_invoice", "latest_invoice.payment_intent"]
#                 )

#             latest_invoice = stripe_sub.get("latest_invoice", {})
#             payment_intent = latest_invoice.get("payment_intent")

#             # Step 4: Fallback if PaymentIntent is missing
#             if not payment_intent:
#                 print("⚠️ PaymentIntent not found. Creating fallback PaymentIntent...")
#                 payment_intent = stripe.PaymentIntent.create(
#                     amount=int(plan.amount * 100),  # Stripe expects amount in cents
#                     currency=plan.currency.lower(),
#                     customer=customer_id,
#                     payment_method_types=["card"],
#                     metadata={"subscription_id": stripe_sub.id}
#                 )

#             # Step 5: Save or update PendingSubscription
#             PendingSubscription.objects.update_or_create(
#                 email=user.email,
#                 stripe_subscription_id=stripe_sub.id,
#                 defaults={
#                     "stripe_customer_id": customer_id,
#                     "stripe_payment_intent_id": payment_intent["id"],
#                     "client_secret": payment_intent["client_secret"],
#                     "status": "pending",
#                     "is_confirmed": False,
#                 }
#             )

#             return Response({
#                 "client_secret": payment_intent["client_secret"],
#                 "customer_id": customer_id,
#                 "subscription_id": stripe_sub.id,
#             })

#         except stripe.error.StripeError as e:
#             return Response({"error": f"Stripe error: {str(e)}"}, status=400)
#         except Exception as e:
#             return Response({"error": f"Unexpected error: {str(e)}"}, status=500)


class StartAuthenticatedSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        plan_id = request.data.get("plan_id")
        user = request.user

        if not plan_id:
            return Response({"error": "Missing plan_id."}, status=400)

        try:
            plan = SubscriptionPlan.objects.get(id=plan_id)
        except SubscriptionPlan.DoesNotExist:
            return Response({"error": "Invalid plan ID."}, status=404)

        stripe.api_key = SystemSettings.get_solo().stripe_api_key

        try:
            # Check for existing subscription
            subscription = Subscription.objects.filter(user=user).first()
            if subscription and subscription.status in ["active", "incomplete", "trialing"]:
                return Response({"error": "You already have an active or ongoing subscription."}, status=400)

            # Create or reuse Stripe customer
            if subscription and subscription.stripe_customer_id:
                customer_id = subscription.stripe_customer_id
            else:
                customer = stripe.Customer.create(email=user.email)
                customer_id = customer.id

                # Create or update local subscription
                if subscription:
                    subscription.stripe_customer_id = customer_id
                    subscription.status = "incomplete"
                    subscription.plan = plan
                else:
                    subscription = Subscription.objects.create(
                        user=user,
                        plan=plan,
                        stripe_customer_id=customer_id,
                        stripe_subscription_id="",
                        status="incomplete"
                    )
                subscription.save()

            # Create Stripe subscription
            stripe_sub = stripe.Subscription.create(
                customer=customer_id,
                items=[{"price": plan.stripe_price_id}],
                payment_behavior="default_incomplete",
                payment_settings={"payment_method_types": ["card"]},
                expand=["latest_invoice", "latest_invoice.payment_intent"]
            )

            # Save Stripe subscription details locally
            subscription.stripe_subscription_id = stripe_sub.id
            subscription.plan = plan
            subscription.status = stripe_sub.status
            subscription.save()

            latest_invoice = stripe_sub.get("latest_invoice", {})
            payment_intent = latest_invoice.get("payment_intent")

            # Fallback PaymentIntent if not found
            if not payment_intent:
                print("⚠️ PaymentIntent not found in invoice. Creating fallback PaymentIntent...")
                payment_intent = stripe.PaymentIntent.create(
                    amount=int(plan.amount * 100),
                    currency=plan.currency.lower(),
                    customer=customer_id,
                    payment_method_types=["card"],
                    metadata={"subscription_id": stripe_sub.id}
                )

                

            return Response({
                "client_secret": payment_intent["client_secret"],
                "customer_id": customer_id,
                "subscription_id": stripe_sub.id,
            })

        except stripe.error.StripeError as e:
            return Response({"error": f"Stripe error: {str(e)}"}, status=400)
        except Exception as e:
            return Response({"error": f"Unexpected error: {str(e)}"}, status=500)







# class StartAuthenticatedSubscriptionView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         plan_id = request.data.get("plan_id")
#         user = request.user

#         if not plan_id:
#             return Response({"error": "Missing plan_id."}, status=400)

#         try:
#             plan = SubscriptionPlan.objects.get(id=plan_id)
#         except SubscriptionPlan.DoesNotExist:
#             return Response({"error": "Invalid plan ID."}, status=404)

#         stripe.api_key = SystemSettings.get_solo().stripe_api_key

#         try:
#             # Step 1: Get or create Stripe customer
#             subscription = Subscription.objects.filter(user=user).first()
#             if subscription and subscription.stripe_customer_id:
#                 customer_id = subscription.stripe_customer_id
#             else:
#                 customer = stripe.Customer.create(email=user.email)
#                 customer_id = customer.id

#                 # Create a local subscription record (even before payment)
#                 subscription = Subscription.objects.create(
#                     user=user,
#                     plan=plan,
#                     stripe_customer_id=customer_id,
#                     stripe_subscription_id="",
#                     status="incomplete"
#                 )
            

#             # Step 2: Create Stripe Subscription
#             stripe_sub = stripe.Subscription.create(
#                 customer=customer_id,
#                 items=[{"price": plan.stripe_price_id}],
#                 payment_behavior="default_incomplete",
#                 payment_settings={"payment_method_types": ["card"]},
#                 expand=["latest_invoice", "latest_invoice.payment_intent"]
#             )

#             # print("-------------------")

#             subscription.stripe_subscription_id = stripe_sub.id
#             subscription.plan = plan
#             subscription.status = stripe_sub.status
#             subscription.save()

#             latest_invoice = stripe_sub.get("latest_invoice", {})
#             payment_intent = latest_invoice.get("payment_intent")

#             # Step 3: Fallback if payment_intent is missing
#             if not payment_intent:
#                 print("⚠️ PaymentIntent not found in invoice. Creating fallback PaymentIntent...")
#                 payment_intent = stripe.PaymentIntent.create(
#                     amount=int(stripe_sub.plan.amount * 100),
#                     currency=stripe_sub.plan.currency.lower(),
#                     customer=customer_id,
#                     payment_method_types=["card"],
#                     metadata={"subscription_id": stripe_sub.id}
#                 )

#             return Response({
#                 "client_secret": payment_intent["client_secret"],
#                 "customer_id": customer_id,
#                 "subscription_id": stripe_sub.id,
#             })

#         except stripe.error.StripeError as e:
#             return Response({"error": f"Stripe error: {str(e)}"}, status=400)
#         except Exception as e:
#             return Response({"error": f"Unexpected error: {str(e)}"}, status=500)



class SchedulePlanChangeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        plan_id = request.data.get("plan_id")
        user = request.user

        if not plan_id:
            return Response({"error": "Missing plan_id"}, status=400)

        try:
            new_plan = SubscriptionPlan.objects.get(id=plan_id)
        except SubscriptionPlan.DoesNotExist:
            return Response({"error": "Invalid plan ID"}, status=404)

        try:
            subscription = Subscription.objects.get(user=user)
        except Subscription.DoesNotExist:
            return Response({"error": "No active subscription found"}, status=404)

        if subscription.plan == new_plan:
            return Response({"error": "You're already on this plan."}, status=400)

        # Save the new plan as scheduled
        subscription.scheduled_plan = new_plan
        subscription.save()

        return Response({"message": f"Plan '{new_plan.name}' scheduled to start after current billing period."})






# class ConfirmSignupAfterPaymentView(APIView):
#     permission_classes = [AllowAny]

#     def post(self, request):
#         data = request.data
#         email = data.get("email")
#         first_name = data.get("first_name")
#         last_name = data.get("last_name")
#         password = data.get("password")
#         customer_id = data.get("customer_id")
#         subscription_id = data.get("subscription_id")

#         if not all([email, password, first_name, last_name, customer_id, subscription_id]):
#             return Response({"error": "Missing required fields."}, status=400)

#         if CustomUser.objects.filter(email=email).exists():
#             return Response({"error": "User already exists. Please login instead."}, status=400)

#         pending = PendingSubscription.objects.filter(
#             email=email,
#             stripe_customer_id=customer_id,
#             stripe_subscription_id=subscription_id,
#             is_confirmed=False
#         ).first()

#         if not pending:
#             return Response({"error": "Payment not verified or already used."}, status=402)

#         stripe.api_key = SystemSettings.get_solo().stripe_api_key
#         try:
#             intent = stripe.PaymentIntent.retrieve(pending.stripe_payment_intent_id)
#             if intent.status != "succeeded":
#                 return Response({"error": "Payment not completed."}, status=402)

#             stripe_sub = stripe.Subscription.retrieve(subscription_id, expand=["latest_invoice"])

#             item = stripe_sub['items']['data'][0]
#             start_ts = item.get("current_period_start")
#             end_ts = item.get("current_period_end")

#             if not start_ts or not end_ts:
#                 return Response({"error": "Missing period info from Stripe."}, status=400)

#             current_period_start = make_aware(datetime.fromtimestamp(start_ts))
#             current_period_end = make_aware(datetime.fromtimestamp(end_ts))

#             # Extract invoice details
#             latest_invoice = stripe_sub.get("latest_invoice", {})
#             latest_invoice_id = latest_invoice.get("id")
#             latest_invoice_url = latest_invoice.get("hosted_invoice_url")
#             latest_invoice_pdf = latest_invoice.get("invoice_pdf")

#         except Exception as e:
#             return Response({"error": f"Stripe error: {str(e)}"}, status=400)

#         price_id = item['price']['id']
#         plan = SubscriptionPlan.objects.filter(stripe_price_id=price_id).first()
#         if not plan:
#             return Response({"error": "Associated plan not found."}, status=400)

#         user = CustomUser.objects.create_user(
#             email=email,
#             first_name=first_name,
#             last_name=last_name,
#             password=password,
#             email_verified=True,
#             role='user'
#         )

#         #  Save invoice details in subscription
#         Subscription.objects.create(
#             user=user,
#             plan=plan,
#             stripe_customer_id=customer_id,
#             stripe_subscription_id=subscription_id,
#             status=stripe_sub.status,
#             current_period_start=current_period_start,
#             current_period_end=current_period_end,
#             cancel_at_period_end=stripe_sub.get("cancel_at_period_end", False),
#             latest_invoice_id=latest_invoice_id,
#             latest_invoice_url=latest_invoice_url,
#             latest_invoice_pdf=latest_invoice_pdf
#         )

#         pending.is_confirmed = True
#         pending.save()

#         refresh = RefreshToken.for_user(user)
#         return Response({
#             "access": str(refresh.access_token),
#             "refresh": str(refresh),
#             "user": UserDetailSerializer(user).data
#         })
        

# class ConfirmSignupAfterPaymentView(APIView):
#     permission_classes = [AllowAny]

#     def post(self, request):
#         data = request.data
#         email = data.get("email")
#         first_name = data.get("first_name")
#         last_name = data.get("last_name")
#         password = data.get("password")
#         customer_id = data.get("customer_id")
#         subscription_id = data.get("subscription_id")

#         # Step 1: Validate all required fields
#         if not all([email, password, first_name, last_name, customer_id, subscription_id]):
#             return Response({"error": "Missing required fields."}, status=400)

#         if CustomUser.objects.filter(email=email).exists():
#             return Response({"error": "User already exists. Please login instead."}, status=400)

#         # Step 2: Get pending subscription record
#         pending = PendingSubscription.objects.filter(
#             email=email,
#             stripe_customer_id=customer_id,
#             stripe_subscription_id=subscription_id,
#             is_confirmed=False
#         ).first()

#         if not pending:
#             return Response({"error": "Payment not verified or already used."}, status=402)

#         # Step 3: Retrieve and verify Stripe payment and subscription
#         stripe.api_key = SystemSettings.get_solo().stripe_api_key
#         try:
#             intent = stripe.PaymentIntent.retrieve(pending.stripe_payment_intent_id)
#             if intent.status != "succeeded":
#                 return Response({"error": "Payment not completed."}, status=402)

#             stripe_sub = stripe.Subscription.retrieve(subscription_id, expand=["latest_invoice", "items.data.price"])

#             start_ts = stripe_sub.get("current_period_start")
#             end_ts = stripe_sub.get("current_period_end")

#             if not start_ts or not end_ts:
#                 return Response({"error": "Missing subscription period information."}, status=400)

#             current_period_start = make_aware(datetime.fromtimestamp(start_ts))
#             current_period_end = make_aware(datetime.fromtimestamp(end_ts))

#             price_id = stripe_sub["items"]["data"][0]["price"]["id"]

#             latest_invoice = stripe_sub.get("latest_invoice", {})
#             latest_invoice_id = latest_invoice.get("id")
#             latest_invoice_url = latest_invoice.get("hosted_invoice_url")
#             latest_invoice_pdf = latest_invoice.get("invoice_pdf")

#         except Exception as e:
#             return Response({"error": f"Stripe error: {str(e)}"}, status=400)

#         # Step 4: Ensure matching SubscriptionPlan exists
#         plan = SubscriptionPlan.objects.filter(stripe_price_id=price_id).first()
#         if not plan:
#             return Response({"error": "Associated subscription plan not found."}, status=400)

#         # Step 5: Create user and subscription
#         user = CustomUser.objects.create_user(
#             email=email,
#             first_name=first_name,
#             last_name=last_name,
#             password=password,
#             email_verified=True,
#             role='user'
#         )

#         Subscription.objects.create(
#             user=user,
#             plan=plan,
#             stripe_customer_id=customer_id,
#             stripe_subscription_id=subscription_id,
#             status=stripe_sub.status,
#             current_period_start=current_period_start,
#             current_period_end=current_period_end,
#             cancel_at_period_end=stripe_sub.get("cancel_at_period_end", False),
#             latest_invoice_id=latest_invoice_id,
#             latest_invoice_url=latest_invoice_url,
#             latest_invoice_pdf=latest_invoice_pdf
#         )

#         # Step 6: Mark pending as confirmed
#         pending.is_confirmed = True
#         pending.status = "confirmed"
#         pending.save()

#         # Step 7: Return tokens and user info
#         refresh = RefreshToken.for_user(user)
#         return Response({
#             "access": str(refresh.access_token),
#             "refresh": str(refresh),
#             "user": UserDetailSerializer(user).data
#         })

# class ConfirmSignupAfterPaymentView(APIView):
#     permission_classes = [AllowAny]

#     def post(self, request):
#         data = request.data
#         email = data.get("email")
#         first_name = data.get("first_name")
#         last_name = data.get("last_name")
#         password = data.get("password")
#         customer_id = data.get("customer_id")
#         subscription_id = data.get("subscription_id")
#         plan_id = data.get("plan_id")

#         # Step 1: Validate inputs
#         if not all([email, password, first_name, last_name, customer_id, subscription_id]):
#             return Response({"error": "Missing required fields."}, status=400)

#         if CustomUser.objects.filter(email=email).exists():
#             return Response({"error": "User already exists. Please login instead."}, status=400)

#         pending = PendingSubscription.objects.filter(
#             email=email,
#             stripe_customer_id=customer_id,
#             stripe_subscription_id=subscription_id,
#             is_confirmed=False,
            
#         ).first()

#         if not pending:
#             return Response({"error": "Payment not verified or already used."}, status=402)

#         stripe.api_key = SystemSettings.get_solo().stripe_api_key
#         try:
#             intent = stripe.PaymentIntent.retrieve(pending.stripe_payment_intent_id)
#             if intent.status != "succeeded":
#                 return Response({"error": "Payment not completed."}, status=402)

#             # Fetch full subscription and expand invoice + price details
#             stripe_sub = stripe.Subscription.retrieve(
#                 subscription_id, expand=["latest_invoice", "items.data.price"]
#             )

#             #  Corrected: Extract period from the subscription item
#             item = stripe_sub["items"]["data"][0]
#             start_ts = item.get("current_period_start")
#             end_ts = item.get("current_period_end")

#             if not start_ts or not end_ts:
#                 return Response({"error": "Missing subscription period information."}, status=400)

#             current_period_start = make_aware(datetime.fromtimestamp(start_ts))
#             current_period_end = make_aware(datetime.fromtimestamp(end_ts))

#             # Invoice info
#             latest_invoice = stripe_sub.get("latest_invoice", {})
#             latest_invoice_id = latest_invoice.get("id")
#             latest_invoice_url = latest_invoice.get("hosted_invoice_url")
#             latest_invoice_pdf = latest_invoice.get("invoice_pdf")

#             # Price and plan
#             price_id = item["price"]["id"]
#             plan = SubscriptionPlan.objects.filter(stripe_price_id=price_id).first()
#             if not plan:
#                 return Response({"error": "Associated subscription plan not found."}, status=400)

#         except Exception as e:
#             return Response({"error": f"Stripe error: {str(e)}"}, status=400)

#         # Create user
#         user = CustomUser.objects.create_user(
#             email=email,
#             first_name=first_name,
#             last_name=last_name,
#             password=password,
#             email_verified=True,
#             role='user'
#         )

#         # Create subscription
#         Subscription.objects.create(
#             user=user,
#             plan=plan,
#             stripe_customer_id=customer_id,
#             stripe_subscription_id=subscription_id,
#             status=stripe_sub.status,
#             current_period_start=current_period_start,
#             current_period_end=current_period_end,
#             cancel_at_period_end=stripe_sub.get("cancel_at_period_end", False),
#             latest_invoice_id=latest_invoice_id,
#             latest_invoice_url=latest_invoice_url,
#             latest_invoice_pdf=latest_invoice_pdf
#         )

#         # Confirm pending subscription
#         pending.is_confirmed = True
#         if pending.status != "succeeded":
#             pending.status = "succeeded"
#         pending.save()

#         SubscriptionPlanChangeLog.objects.create(
#             user=user,
#             # stripe_subscription_id=subscription_id,
#             old_plan=None,
#             new_plan=SubscriptionPlan.objects.get(id=plan_id),
#         )

#         # Return tokens and user info
#         refresh = RefreshToken.for_user(user)
#         return Response({
#             "access": str(refresh.access_token),
#             "refresh": str(refresh),
#             "user": UserDetailSerializer(user).data
#         })


# class ConfirmSignupAfterPaymentView(APIView):
#     permission_classes = [AllowAny]

#     def post(self, request):
#         data = request.data
#         email = data.get("email")
#         first_name = data.get("first_name")
#         last_name = data.get("last_name")
#         password = data.get("password")
#         customer_id = data.get("customer_id")
#         subscription_id = data.get("subscription_id")
#         plan_id = data.get("plan_id")

#         # ===== Step 1: Basic validation =====
#         if not all([email, password, first_name, last_name, customer_id, subscription_id, plan_id]):
#             return Response({"error": "Missing required fields."}, status=400)

#         if CustomUser.objects.filter(email=email).exists():
#             return Response({"error": "User already exists. Please login instead."}, status=400)

#         pending = PendingSubscription.objects.filter(
#             email=email,
#             stripe_customer_id=customer_id,
#             stripe_subscription_id=subscription_id,
#             is_confirmed=False,
#         ).first()

#         if not pending:
#             return Response({"error": "Payment not verified or already used."}, status=402)

#         # ===== Step 2: Verify Stripe payment & get subscription details =====
#         stripe.api_key = SystemSettings.get_solo().stripe_api_key
#         try:
#             intent = stripe.PaymentIntent.retrieve(pending.stripe_payment_intent_id)
#             if intent.status != "succeeded":
#                 return Response({"error": "Payment not completed."}, status=402)

#             stripe_sub = stripe.Subscription.retrieve(
#                 subscription_id, expand=["latest_invoice", "items.data.price"]
#             )
#             item = stripe_sub["items"]["data"][0]

#             # Dates
#             start_ts = item.get("current_period_start")
#             end_ts = item.get("current_period_end")

#             if not start_ts or not end_ts:
#                 return Response({"error": "Missing subscription period information."}, status=400)

#             current_period_start = make_aware(datetime.fromtimestamp(start_ts))
#             current_period_end = make_aware(datetime.fromtimestamp(end_ts))

#             # Invoice info
#             latest_invoice = stripe_sub.get("latest_invoice", {})
#             latest_invoice_id = latest_invoice.get("id")
#             latest_invoice_url = latest_invoice.get("hosted_invoice_url")
#             latest_invoice_pdf = latest_invoice.get("invoice_pdf")

#             # Plan from Stripe price ID
#             price_id = item["price"]["id"]
#             plan = SubscriptionPlan.objects.filter(stripe_price_id=price_id).first()
#             if not plan:
#                 return Response({"error": "Associated subscription plan not found."}, status=400)

#         except Exception as e:
#             return Response({"error": f"Stripe error: {str(e)}"}, status=400)

#         # ===== Step 3: Create user and local subscription =====
#         user = CustomUser.objects.create_user(
#             email=email,
#             first_name=first_name,
#             last_name=last_name,
#             password=password,
#             email_verified=True,
#             role='user'
#         )

#         subscription = Subscription.objects.create(
#             user=user,
#             plan=plan,
#             stripe_customer_id=customer_id,
#             stripe_subscription_id=subscription_id,
#             status=stripe_sub.status,
#             current_period_start=current_period_start,
#             current_period_end=current_period_end,
#             cancel_at_period_end=stripe_sub.get("cancel_at_period_end", False),
#             latest_invoice_id=latest_invoice_id,
#             latest_invoice_url=latest_invoice_url,
#             latest_invoice_pdf=latest_invoice_pdf
#         )

#         # ===== Step 4: Confirm pending subscription =====
#         pending.is_confirmed = True
#         if pending.status != "succeeded":
#             pending.status = "succeeded"
#         pending.save()

#         # ===== Step 5: Log Plan Change =====
#         SubscriptionPlanChangeLog.objects.create(
#             user=user,
#             old_plan=None,
#             new_plan=plan
#         )

#         # ===== Step 6: Log to SubscriptionHistory if paid =====
#         if latest_invoice and latest_invoice.get("status") == "paid":
#             try:
#                 SubscriptionHistory.objects.create(
#                     user=user,
#                     stripe_invoice_id=latest_invoice.get("id"),
#                     amount_paid=latest_invoice.get("amount_paid", 0) / 100,
#                     currency=latest_invoice.get("currency", "").upper(),
#                     paid_at=make_aware(datetime.fromtimestamp(latest_invoice.get("created"))),
#                     plan=plan,
#                     invoice_pdf=latest_invoice_pdf,
#                     hosted_invoice_url=latest_invoice_url,
#                 )
#             except Exception as e:
#                 print(f"⚠️ Failed to log SubscriptionHistory: {e}")

#         # ===== Step 7: Return tokens =====
#         refresh = RefreshToken.for_user(user)
#         return Response({
#             "access": str(refresh.access_token),
#             "refresh": str(refresh),
#             "user": UserDetailSerializer(user).data
#         })

# class ConfirmSignupAfterPaymentView(APIView):
#     permission_classes = [AllowAny]

#     def post(self, request):
#         data = request.data
#         email = data.get("email")
#         first_name = data.get("first_name")
#         last_name = data.get("last_name")
#         password = data.get("password")
#         customer_id = data.get("customer_id")
#         subscription_id = data.get("subscription_id")

#         if not all([email, first_name, last_name, password, customer_id, subscription_id]):
#             return Response({"error": "Missing required fields."}, status=400)

#         if User.objects.filter(email=email).exists():
#             return Response({"error": "User already exists. Please login."}, status=400)

#         try:
#             pending = PendingSubscription.objects.get(
#                 email=email,
#                 stripe_customer_id=customer_id,
#                 stripe_subscription_id=subscription_id,
#                 is_confirmed=False
#             )
#         except PendingSubscription.DoesNotExist:
#             return Response({"error": "Payment not verified or already confirmed."}, status=402)

#         try:
#             intent = stripe.PaymentIntent.retrieve(pending.stripe_payment_intent_id)
#             if intent.status != "succeeded":
#                 return Response({"error": "Payment not completed."}, status=402)

#             stripe_sub = stripe.Subscription.retrieve(
#                 subscription_id, expand=["latest_invoice", "items.data.price"]
#             )
#             item = stripe_sub.items.data[0]
#             price_id = item.price.id
#             plan = SubscriptionPlan.objects.get(stripe_price_id=price_id)
#             period_start = make_aware(datetime.fromtimestamp(item.current_period_start))
#             period_end = make_aware(datetime.fromtimestamp(item.current_period_end))

#             latest_invoice = stripe_sub.latest_invoice
#             invoice_id = latest_invoice.id
#             invoice_url = latest_invoice.hosted_invoice_url
#             invoice_pdf = latest_invoice.invoice_pdf

#             user = User.objects.create_user(
#                 email=email,
#                 first_name=first_name,
#                 last_name=last_name,
#                 password=password,
#                 email_verified=True,
#                 role="user"
#             )

#             Subscription.objects.create(
#                 user=user,
#                 plan=plan,
#                 stripe_customer_id=customer_id,
#                 stripe_subscription_id=subscription_id,
#                 status=stripe_sub.status,
#                 current_period_start=period_start,
#                 current_period_end=period_end,
#                 cancel_at_period_end=stripe_sub.cancel_at_period_end,
#                 latest_invoice_id=invoice_id,
#                 latest_invoice_url=invoice_url,
#                 latest_invoice_pdf=invoice_pdf
#             )

#             pending.status = "succeeded"
#             pending.is_confirmed = True
#             pending.save()

#             if latest_invoice.status == "paid":
#                 SubscriptionHistory.objects.create(
#                     user=user,
#                     stripe_invoice_id=invoice_id,
#                     amount_paid=latest_invoice.amount_paid / 100,
#                     currency=latest_invoice.currency.upper(),
#                     paid_at=make_aware(datetime.fromtimestamp(latest_invoice.created)),
#                     plan=plan,
#                     invoice_pdf=invoice_pdf,
#                     hosted_invoice_url=invoice_url
#                 )

#             refresh = RefreshToken.for_user(user)
#             return Response({
#                 "access": str(refresh.access_token),
#                 "refresh": str(refresh),
#                 "user": UserDetailSerializer(user).data
#             })

#         except Exception as e:
#             return Response({"error": f"Stripe error: {str(e)}"}, status=400)

class ConfirmSignupAfterPaymentView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data
        email = data.get("email")
        first_name = data.get("first_name")
        last_name = data.get("last_name")
        password = data.get("password")
        customer_id = data.get("customer_id")
        subscription_id = data.get("subscription_id")

        if not all([email, first_name, last_name, password, customer_id, subscription_id]):
            return Response({"error": "Missing required fields."}, status=400)

        if User.objects.filter(email=email).exists():
            return Response({"error": "User already exists. Please login."}, status=400)

        try:
            pending = PendingSubscription.objects.get(
                email=email,
                stripe_customer_id=customer_id,
                stripe_subscription_id=subscription_id,
                is_confirmed=False
            )
        except PendingSubscription.DoesNotExist:
            return Response({"error": "Payment not verified or already confirmed."}, status=402)

        try:
            intent = stripe.PaymentIntent.retrieve(pending.stripe_payment_intent_id)
            if intent.status != "succeeded":
                return Response({"error": "Payment not completed."}, status=402)

            stripe_sub = stripe.Subscription.retrieve(
                subscription_id, expand=["latest_invoice", "items.data.price"]
            )

            item = stripe_sub["items"]["data"][0]
            price_id = item["price"]["id"]
            plan = SubscriptionPlan.objects.filter(stripe_price_id=price_id).first()
            if not plan:
                return Response({"error": "Subscription plan not found."}, status=400)

            period_start = make_aware(datetime.fromtimestamp(item["current_period_start"]))
            period_end = make_aware(datetime.fromtimestamp(item["current_period_end"]))

            latest_invoice = stripe_sub.get("latest_invoice") or {}
            invoice_id = latest_invoice.get("id")
            invoice_url = latest_invoice.get("hosted_invoice_url")
            invoice_pdf = latest_invoice.get("invoice_pdf")

            user = User.objects.create_user(
                email=email,
                first_name=first_name,
                last_name=last_name,
                password=password,
                email_verified=True,
                role="user"
            )

            Subscription.objects.create(
                user=user,
                plan=plan,
                stripe_customer_id=customer_id,
                stripe_subscription_id=subscription_id,
                status=stripe_sub["status"],
                current_period_start=period_start,
                current_period_end=period_end,
                cancel_at_period_end=stripe_sub.get("cancel_at_period_end", False),
                latest_invoice_id=invoice_id,
                latest_invoice_url=invoice_url,
                latest_invoice_pdf=invoice_pdf
            )

            # Mark as succeeded and confirmed
            pending.status = "succeeded"
            pending.is_confirmed = True
            pending.save()

            if latest_invoice and latest_invoice.get("status") == "paid":
                SubscriptionHistory.objects.create(
                    user=user,
                    stripe_invoice_id=invoice_id,
                    amount_paid=latest_invoice.get("amount_paid", 0) / 100,
                    currency=latest_invoice.get("currency", "").upper(),
                    paid_at=make_aware(datetime.fromtimestamp(latest_invoice.get("created"))),
                    plan=plan,
                    invoice_pdf=invoice_pdf,
                    hosted_invoice_url=invoice_url
                )

            refresh = RefreshToken.for_user(user)
            return Response({
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserDetailSerializer(user).data
            })

        except Exception as e:
            return Response({"error": f"Stripe error: {str(e)}"}, status=400)




# class StripeWebhookView(APIView):
#     permission_classes = [AllowAny]

#     def post(self, request):
#         stripe.api_key = SystemSettings.get_solo().stripe_api_key
#         webhook_secret = SystemSettings.get_solo().stripe_webhook_secret

#         payload = request.body
#         sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

#         try:
#             event = stripe.Webhook.construct_event(
#                 payload, sig_header, webhook_secret
#             )
#         except ValueError:
#             return Response(status=400)
#         except stripe.error.SignatureVerificationError:
#             return Response(status=400)

#         event_type = event['type']
#         data = event['data']['object']

#         print(f"Received Stripe event: {event_type}")
#         if event_type == "invoice.payment_succeeded":
#             print(f"Payment succeeded for subscription: {data.get('subscription')}")
#             sub_id = data.get('subscription')
#             # customer_id = data.get('customer')
#             payment_intent_id = data.get('payment_intent')
#             invoice_id = data.get("id")
#             hosted_invoice_url = data.get("hosted_invoice_url")
#             invoice_pdf = data.get("invoice_pdf")

#             try:
#                 payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
#                 stripe.Subscription.modify(
#                     sub_id,
#                     default_payment_method=payment_intent.payment_method
#                 )
#             except Exception:
#                 pass  # Safe to ignore if not available

#             try:
#                 local_sub = Subscription.objects.get(stripe_subscription_id=sub_id)
#                 local_sub.status = "active"
#                 local_sub.latest_invoice_id = invoice_id
#                 local_sub.latest_invoice_url = hosted_invoice_url
#                 local_sub.latest_invoice_pdf = invoice_pdf
#                 local_sub.save()
#             except Subscription.DoesNotExist:
#                 print(f"No local subscription found for {sub_id}")


#         elif event_type == "payment_intent.succeeded":
#             # Try to find the pending subscription and update status
#             payment_intent_id = data.get("id")
#             pending = PendingSubscription.objects.filter(stripe_payment_intent_id=payment_intent_id, is_confirmed=False).first()

#             if pending:
#                 try:
#                     stripe_sub = stripe.Subscription.retrieve(pending.stripe_subscription_id)
#                     local_sub = Subscription.objects.get(stripe_subscription_id=stripe_sub.id)
#                     local_sub.status = stripe_sub.status  # should be 'active' or will remain 'incomplete'
#                     local_sub.save()
#                 except Exception as e:
#                     print(f"Error updating from payment_intent.succeeded: {e}")

#         elif event_type == "invoice.payment_failed":
#             print(f"Payment failed for subscription: {data.get('subscription')}")
#             # Optional: Notify user, mark as 'past_due'

#         elif event_type == "customer.subscription.deleted":
#             sub_id = data.get("id")
#             try:
#                 local_sub = Subscription.objects.get(stripe_subscription_id=sub_id)
#                 local_sub.status = "canceled"
#                 local_sub.save()
#             except Subscription.DoesNotExist:
#                 print(f"No local subscription to cancel for {sub_id}")

#         elif event_type == "customer.subscription.updated":
#             sub_id = data.get("id")
#             status = data.get("status")
#             current_period_start = data.get("current_period_start")
#             current_period_end = data.get("current_period_end")
#             cancel_at_period_end = data.get("cancel_at_period_end", False)
#             latest_invoice = data.get("latest_invoice")

#             try:
#                 invoice = stripe.Invoice.retrieve(latest_invoice) if latest_invoice else None
#                 local_sub = Subscription.objects.get(stripe_subscription_id=sub_id)
#                 local_sub.status = status
#                 local_sub.cancel_at_period_end = cancel_at_period_end
#                 local_sub.current_period_start = make_aware(datetime.fromtimestamp(current_period_start))
#                 local_sub.current_period_end = make_aware(datetime.fromtimestamp(current_period_end))

#                 if invoice:
#                     local_sub.latest_invoice_id = invoice.id
#                     local_sub.latest_invoice_url = invoice.hosted_invoice_url
#                     local_sub.latest_invoice_pdf = invoice.invoice_pdf

#                 local_sub.save()
#             except Subscription.DoesNotExist:
#                 print(f"Subscription not found for update: {sub_id}")

#         elif event_type == "invoice.created":
#             invoice_pdf = data.get("invoice_pdf")
#             hosted_url = data.get("hosted_invoice_url")
#             print(f"New invoice created. PDF: {invoice_pdf}, Hosted: {hosted_url}")

#         return JsonResponse({"status": "success"}, status=200)


# class StripeWebhookView(APIView):
#     permission_classes = [AllowAny]

#     def post(self, request):
#         # Load Stripe credentials
#         stripe.api_key = SystemSettings.get_solo().stripe_api_key
#         webhook_secret = SystemSettings.get_solo().stripe_webhook_secret

#         # Validate Stripe webhook signature
#         payload = request.body
#         sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
#         try:
#             event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
#         except (ValueError, stripe.error.SignatureVerificationError):
#             return Response(status=400)

#         # Extract event data
#         event_type = event.get("type")
#         data = event["data"]["object"]
#         print(f"✅ Received Stripe event: {event_type}")

#         try:
#             # ========== 1. Payment Succeeded ==========
#             if event_type == "invoice.payment_succeeded":
#                 self.handle_invoice_payment_succeeded(data)

#             # ========== 2. Payment Intent Succeeded ==========
#             elif event_type == "payment_intent.succeeded":
#                 self.handle_payment_intent_succeeded(data)

#             # ========== 3. Subscription Canceled ==========
#             elif event_type == "customer.subscription.deleted":
#                 self.handle_subscription_deleted(data)

#             # ========== 4. Subscription Updated (renewal, status change, etc.) ==========
#             elif event_type == "customer.subscription.updated":
#                 self.handle_subscription_updated(data)

#             # ========== 5. Invoice Created (for logging/analytics) ==========
#             elif event_type == "invoice.created":
#                 invoice_pdf = data.get("invoice_pdf")
#                 hosted_url = data.get("hosted_invoice_url")
#                 print(f"🧾 New invoice created. PDF: {invoice_pdf}, Hosted: {hosted_url}")

#             # ========== 6. Invoice Failed ==========
#             elif event_type == "invoice.payment_failed":
#                 print(f"❌ Payment failed for subscription: {data.get('subscription')}")

#         except Exception as e:
#             print(f"⚠️ Webhook processing error for {event_type}: {e}")

#         return JsonResponse({"status": "success"}, status=200)

#     # ===== HANDLER METHODS =====

#     def handle_invoice_payment_succeeded(self, data):
#         sub_id = data.get("subscription")
#         payment_intent_id = data.get("payment_intent")
#         invoice_id = data.get("id")
#         hosted_invoice_url = data.get("hosted_invoice_url")
#         invoice_pdf = data.get("invoice_pdf")

#         # Try to set default payment method on subscription
#         try:
#             payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
#             stripe.Subscription.modify(
#                 sub_id,
#                 default_payment_method=payment_intent.payment_method
#             )
#         except Exception as e:
#             print(f"⚠️ Could not update default payment method: {e}")

#         # Update existing subscription or fallback to pending
#         updated = self.update_local_subscription(
#             stripe_subscription_id=sub_id,
#             updates={
#                 "status": "active",
#                 "latest_invoice_id": invoice_id,
#                 "latest_invoice_url": hosted_invoice_url,
#                 "latest_invoice_pdf": invoice_pdf,
#             }
#         )
        

#         if not updated:
#             # fallback to pending if Subscription not found
#             PendingSubscription.objects.filter(stripe_subscription_id=sub_id).update(
#                 status="succeeded"
#             )
#             print(f"✅ Fallback: marked pending subscription {sub_id} as succeeded")

#     def handle_payment_intent_succeeded(self, data):
#         payment_intent_id = data.get("id")
#         metadata = data.get("metadata", {})
#         subscription_id = metadata.get("subscription_id")

#         # Try finding pending record via payment_intent_id first
#         pending = PendingSubscription.objects.filter(stripe_payment_intent_id=payment_intent_id).first()

#         if pending:
#             # Use the subscription ID from pending (not from metadata)
#             subscription_id = pending.stripe_subscription_id
#             pending.status = "succeeded"
#             pending.save()
#             print(f"✅ Marked pending subscription {pending.email} as succeeded")
#             print(f"New status for PendingSubscription {pending.email}: {pending.status}")
#         else:
#             print(f"⚠️ No PendingSubscription found for payment_intent {payment_intent_id}")

#         if not subscription_id:
#             print(f"⚠️ Could not determine subscription_id from metadata or PendingSubscription for PI {payment_intent_id}")
#             return

#         updated = self.update_local_subscription(
#             stripe_subscription_id=subscription_id,
#             updates={"status": "active"}
#         )

#         if updated:
#             print(f"✅ Updated Subscription {subscription_id} to active")
#         else:
#             print(f"ℹ️ No existing Subscription found for {subscription_id}, will wait for ConfirmSignupView.")


#     # def handle_payment_intent_succeeded(self, data):
#     #     payment_intent_id = data.get("id")
#     #     subscription_id = data.get("metadata", {}).get("subscription_id")

#     #     if not subscription_id:
#     #         print(f"⚠️ Missing subscription_id in metadata for PaymentIntent {payment_intent_id}")
#     #         return

#     #     updated = self.update_local_subscription(
#     #         stripe_subscription_id=subscription_id,
#     #         updates={"status": "active"}
#     #     )

#     #     if not updated:
#     #         # Fallback: mark PendingSubscription as succeeded
#     #         pending = PendingSubscription.objects.filter(stripe_payment_intent_id=payment_intent_id).first()
#     #         if pending:
#     #             pending.status = "succeeded"
#     #             pending.save()
#     #             print(f"✅ Marked pending subscription {pending.email} as succeeded")
#     #         else:
#     #             print(f"⚠️ No PendingSubscription found for payment_intent {payment_intent_id}")

#     def handle_subscription_deleted(self, data):
#         sub_id = data.get("id")
#         if self.update_local_subscription(sub_id, {"status": "canceled"}):
#             print(f"🚫 Subscription {sub_id} marked as canceled")
#         else:
#             print(f"⚠️ Subscription not found to cancel: {sub_id}")

#     def handle_subscription_updated(self, data):
#         sub_id = data.get("id")
#         status = data.get("status")
#         cancel_at_period_end = data.get("cancel_at_period_end", False)
#         current_period_start = data.get("current_period_start")
#         current_period_end = data.get("current_period_end")
#         latest_invoice_id = data.get("latest_invoice")

#         updates = {
#             "status": status,
#             "cancel_at_period_end": cancel_at_period_end,
#             "current_period_start": make_aware(datetime.fromtimestamp(current_period_start)) if current_period_start else None,
#             "current_period_end": make_aware(datetime.fromtimestamp(current_period_end)) if current_period_end else None,
#         }

#         # Try to retrieve invoice (optional)
#         if latest_invoice_id:
#             try:
#                 invoice = stripe.Invoice.retrieve(latest_invoice_id)
#                 updates["latest_invoice_id"] = invoice.id
#                 updates["latest_invoice_url"] = invoice.hosted_invoice_url
#                 updates["latest_invoice_pdf"] = invoice.invoice_pdf
#             except Exception as e:
#                 print(f"⚠️ Failed to retrieve invoice {latest_invoice_id}: {e}")

#         if self.update_local_subscription(sub_id, updates):
#             print(f"🔄 Subscription {sub_id} updated successfully.")
#         else:
#             print(f"⚠️ Subscription not found for update: {sub_id}")

#     # ===== HELPER METHOD =====

#     def update_local_subscription(self, stripe_subscription_id, updates: dict) -> bool:
#         """
#         Utility method to update a Subscription record if it exists.
#         Returns True if updated, False if not found.
#         """
#         try:
#             sub = Subscription.objects.get(stripe_subscription_id=stripe_subscription_id)
#             for field, value in updates.items():
#                 if value is not None:
#                     setattr(sub, field, value)
#             sub.save()
#             if "status" in updates:
#                 if updates.get("status") in ["canceled", "active"]:
#                     PendingSubscription.objects.filter(
#                         stripe_subscription_id=sub.stripe_subscription_id
#                     ).delete()
#             return True
#         except Subscription.DoesNotExist:
#             return False

# class StripeWebhookView(APIView):
#     permission_classes = [AllowAny]

#     def post(self, request):
#         # Load keys
#         stripe.api_key = SystemSettings.get_solo().stripe_api_key
#         webhook_secret = SystemSettings.get_solo().stripe_webhook_secret

#         # Validate webhook signature
#         payload = request.body
#         sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
#         try:
#             event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
#         except (ValueError, stripe.error.SignatureVerificationError):
#             return Response(status=400)

#         event_type = event.get("type")
#         data = event["data"]["object"]

#         print(f"✅ Received Stripe event: {event_type}")

#         try:
#             match event_type:
#                 case "invoice.payment_succeeded":
#                     self.handle_invoice_payment_succeeded(data)

#                 case "payment_intent.succeeded":
#                     self.handle_payment_intent_succeeded(data)

#                 case "customer.subscription.updated":
#                     self.handle_subscription_updated(data)

#                 case "customer.subscription.deleted":
#                     self.handle_subscription_deleted(data)

#                 case "invoice.payment_failed":
#                     print(f"❌ Payment failed for subscription: {data.get('subscription')}")

#                 case "invoice.created":
#                     print(f"🧾 New invoice created. PDF: {data.get('invoice_pdf')}, Hosted: {data.get('hosted_invoice_url')}")

#         except Exception as e:
#             print(f"⚠️ Webhook processing error for {event_type}: {e}")

#         return JsonResponse({"status": "success"}, status=200)

#     # ========== HANDLERS ==========

#     def handle_invoice_payment_succeeded(self, data):
#         sub_id = data.get("subscription")
#         payment_intent_id = data.get("payment_intent")
#         invoice_id = data.get("id")
#         hosted_invoice_url = data.get("hosted_invoice_url")
#         invoice_pdf = data.get("invoice_pdf")

#         try:
#             payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
#             stripe.Subscription.modify(
#                 sub_id,
#                 default_payment_method=payment_intent.payment_method
#             )
#         except Exception as e:
#             print(f"⚠️ Could not update default payment method: {e}")

#         updated = self.update_local_subscription(
#             stripe_subscription_id=sub_id,
#             updates={
#                 "status": "active",
#                 "latest_invoice_id": invoice_id,
#                 "latest_invoice_url": hosted_invoice_url,
#                 "latest_invoice_pdf": invoice_pdf,
#             }
#         )

#         if not updated:
#             PendingSubscription.objects.filter(stripe_subscription_id=sub_id).update(status="succeeded")
#             print(f"✅ Fallback: Marked PendingSubscription {sub_id} as succeeded")

#     def handle_payment_intent_succeeded(self, data):
#         payment_intent_id = data.get("id")
#         metadata = data.get("metadata", {})
#         subscription_id = metadata.get("subscription_id")

#         pending = PendingSubscription.objects.filter(stripe_payment_intent_id=payment_intent_id).first()

#         if pending:
#             subscription_id = pending.stripe_subscription_id
#             pending.status = "succeeded"
#             pending.save(update_fields=["status"])
#             # pending.save()
#             print(f"✅ Marked PendingSubscription {pending.email} as succeeded")
#             print(f"New status for PendingSubscription {pending.email}: {pending.status}")
#         else:
#             print(f"⚠️ No PendingSubscription found for payment_intent {payment_intent_id}")

#         if not subscription_id:
#             print(f"⚠️ Cannot determine subscription_id for PI {payment_intent_id}")
#             return

#         updated = self.update_local_subscription(
#             stripe_subscription_id=subscription_id,
#             updates={"status": "active"}
#         )

#         if updated:
#             print(f"✅ Updated Subscription {subscription_id} to active")
#         else:
#             print(f"ℹ️ Subscription {subscription_id} not found yet. Waiting for user signup.")

#     def handle_subscription_updated(self, data):
#         sub_id = data.get("id")
#         updates = {
#             "status": data.get("status"),
#             "cancel_at_period_end": data.get("cancel_at_period_end", False),
#             "current_period_start": make_aware(datetime.fromtimestamp(data.get("current_period_start")))
#             if data.get("current_period_start") else None,
#             "current_period_end": make_aware(datetime.fromtimestamp(data.get("current_period_end")))
#             if data.get("current_period_end") else None,
#         }

#         invoice_id = data.get("latest_invoice")
#         if invoice_id:
#             try:
#                 invoice = stripe.Invoice.retrieve(invoice_id)
#                 updates["latest_invoice_id"] = invoice.id
#                 updates["latest_invoice_url"] = invoice.hosted_invoice_url
#                 updates["latest_invoice_pdf"] = invoice.invoice_pdf
#             except Exception as e:
#                 print(f"⚠️ Could not retrieve invoice {invoice_id}: {e}")

#         if self.update_local_subscription(sub_id, updates):
#             print(f"🔄 Subscription {sub_id} updated")
#         else:
#             print(f"⚠️ Subscription {sub_id} not found")

#     def handle_subscription_deleted(self, data):
#         sub_id = data.get("id")
#         if self.update_local_subscription(sub_id, {"status": "canceled"}):
#             print(f"🚫 Subscription {sub_id} marked as canceled")
#         else:
#             print(f"⚠️ Subscription {sub_id} not found for cancellation")

#     # ========== HELPER ==========

#     def update_local_subscription(self, stripe_subscription_id, updates: dict) -> bool:
#         """
#         Safely update the Subscription model if exists.
#         Deletes matching PendingSubscription if status is confirmed.
#         """
#         try:
#             sub = Subscription.objects.get(stripe_subscription_id=stripe_subscription_id)
#             for field, value in updates.items():
#                 if value is not None:
#                     setattr(sub, field, value)
#             sub.save()

#             # Delete matching pending if subscription is confirmed
#             if updates.get("status") in ["active", "canceled"]:
#                 PendingSubscription.objects.filter(
#                     stripe_subscription_id=sub.stripe_subscription_id
#                 ).delete()

#             return True
#         except Subscription.DoesNotExist:
#             return False


# class StripeWebhookView(APIView):
#     permission_classes = [AllowAny]

#     def post(self, request):
#         stripe.api_key = SystemSettings.get_solo().stripe_api_key
#         webhook_secret = SystemSettings.get_solo().stripe_webhook_secret

#         payload = request.body
#         sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
#         try:
#             event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
#         except (ValueError, stripe.error.SignatureVerificationError):
#             return Response(status=400)

#         event_type = event.get("type")
#         data = event["data"]["object"]

#         print(f"✅ Received Stripe event: {event_type}")

#         try:
#             match event_type:
#                 case "invoice.payment_succeeded":
#                     self.handle_invoice_payment_succeeded(data)
#                 case "payment_intent.succeeded":
#                     self.handle_payment_intent_succeeded(data)
#                 case "customer.subscription.updated":
#                     self.handle_subscription_updated(data)
#                 case "customer.subscription.deleted":
#                     self.handle_subscription_deleted(data)
#                 case "invoice.payment_failed":
#                     print(f"❌ Payment failed for subscription: {data.get('subscription')}")
#                 case "invoice.created":
#                     print(f"🧾 Invoice created. PDF: {data.get('invoice_pdf')} Hosted: {data.get('hosted_invoice_url')}")
#         except Exception as e:
#             print(f"⚠️ Webhook error for {event_type}: {e}")

#         return JsonResponse({"status": "success"}, status=200)

#     def handle_invoice_payment_succeeded(self, data):
#         sub_id = data.get("subscription")
#         invoice_id = data.get("id")
#         payment_intent_id = data.get("payment_intent")
#         hosted_invoice_url = data.get("hosted_invoice_url")
#         invoice_pdf = data.get("invoice_pdf")
#         amount_paid = data.get("amount_paid", 0) / 100
#         currency = data.get("currency", "usd")
#         paid_at = make_aware(datetime.fromtimestamp(data.get("created")))

#         try:
#             payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
#             stripe.Subscription.modify(
#                 sub_id,
#                 default_payment_method=payment_intent.payment_method
#             )
#         except Exception as e:
#             print(f"⚠️ Could not update default payment method: {e}")

#         updated = self.update_local_subscription(sub_id, {
#             "status": "active",
#             "latest_invoice_id": invoice_id,
#             "latest_invoice_url": hosted_invoice_url,
#             "latest_invoice_pdf": invoice_pdf
#         })

#         if updated:
#             sub = Subscription.objects.filter(stripe_subscription_id=sub_id).first()
#             if sub and sub.user:
#                 SubscriptionHistory.objects.create(
#                     user=sub.user,
#                     stripe_invoice_id=invoice_id,
#                     amount_paid=amount_paid,
#                     currency=currency,
#                     paid_at=paid_at,
#                     plan=sub.plan,
#                     invoice_pdf=invoice_pdf,
#                     hosted_invoice_url=hosted_invoice_url
#                 )
#                 print(f"🧾 Invoice history saved for {sub.user.email}")
#         else:
#             PendingSubscription.objects.filter(stripe_subscription_id=sub_id).update(status="succeeded")
#             print(f"✅ Fallback: Marked PendingSubscription {sub_id} as succeeded")

#     def handle_payment_intent_succeeded(self, data):
#         payment_intent_id = data.get("id")
#         metadata = data.get("metadata", {})
#         subscription_id = metadata.get("subscription_id")

#         pending = PendingSubscription.objects.filter(stripe_payment_intent_id=payment_intent_id).first()
#         if pending:
#             subscription_id = pending.stripe_subscription_id
#             pending.status = "succeeded"
#             pending.save()
#             print(f"✅ Marked PendingSubscription {pending.email} as succeeded")
#         else:
#             print(f"⚠️ No PendingSubscription for payment_intent {payment_intent_id}")

#         if not subscription_id:
#             print(f"⚠️ No subscription_id found for PI {payment_intent_id}")
#             return

#         updated = self.update_local_subscription(subscription_id, {"status": "active"})
#         if updated:
#             print(f"✅ Subscription {subscription_id} activated")
#         else:
#             print(f"ℹ️ Subscription {subscription_id} not found yet")

#     def handle_subscription_updated(self, data):
#         sub_id = data.get("id")
#         updates = {
#             "status": data.get("status"),
#             "cancel_at_period_end": data.get("cancel_at_period_end", False),
#             "current_period_start": make_aware(datetime.fromtimestamp(data["current_period_start"])) if data.get("current_period_start") else None,
#             "current_period_end": make_aware(datetime.fromtimestamp(data["current_period_end"])) if data.get("current_period_end") else None,
#         }

#         invoice_id = data.get("latest_invoice")
#         if invoice_id:
#             try:
#                 invoice = stripe.Invoice.retrieve(invoice_id)
#                 updates.update({
#                     "latest_invoice_id": invoice.id,
#                     "latest_invoice_url": invoice.hosted_invoice_url,
#                     "latest_invoice_pdf": invoice.invoice_pdf
#                 })
#             except Exception as e:
#                 print(f"⚠️ Could not retrieve invoice {invoice_id}: {e}")

#         if self.update_local_subscription(sub_id, updates):
#             print(f"🔄 Subscription {sub_id} updated")
#         else:
#             print(f"⚠️ Subscription {sub_id} not found")

#     def handle_subscription_deleted(self, data):
#         sub_id = data.get("id")
#         if self.update_local_subscription(sub_id, {"status": "canceled"}):
#             print(f"🚫 Subscription {sub_id} canceled")
#         else:
#             print(f"⚠️ Subscription {sub_id} not found for deletion")

#     def update_local_subscription(self, stripe_subscription_id, updates: dict) -> bool:
#         try:
#             sub = Subscription.objects.get(stripe_subscription_id=stripe_subscription_id)
#             for field, value in updates.items():
#                 if value is not None:
#                     setattr(sub, field, value)
#             sub.save()

#             # Delete matching pending
#             if updates.get("status") in ["active", "canceled"]:
#                 PendingSubscription.objects.filter(stripe_subscription_id=stripe_subscription_id).delete()

#             return True
#         except Subscription.DoesNotExist:
#             return False

# @method_decorator(csrf_exempt, name='dispatch')
# class StripeWebhookView(APIView):
#     permission_classes = []

#     def post(self, request):
#         stripe.api_key = SystemSettings.get_solo().stripe_api_key
#         webhook_secret = SystemSettings.get_solo().stripe_webhook_secret

#         payload = request.body
#         sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
#         try:
#             event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
#         except (ValueError, stripe.error.SignatureVerificationError):
#             return Response(status=400)

#         event_type = event.get("type")
#         data = event["data"]["object"]
#         print(f"✅ Received Stripe event: {event_type}")

#         try:
#             match event_type:
#                 case "invoice.payment_succeeded":
#                     self.handle_invoice_payment_succeeded(data)

#                 case "payment_intent.succeeded":
#                     self.handle_payment_intent_succeeded(data)

#                 case "customer.subscription.updated":
#                     self.handle_subscription_updated(data)

#                 case "customer.subscription.deleted":
#                     self.handle_subscription_deleted(data)

#                 case "invoice.payment_failed":
#                     print(f"❌ Payment failed for subscription: {data.get('subscription')}")

#                 case "invoice.created":
#                     print(f"🧾 New invoice created. PDF: {data.get('invoice_pdf')}, Hosted: {data.get('hosted_invoice_url')}")

#         except Exception as e:
#             print(f"⚠️ Webhook processing error for {event_type}: {e}")

#         return JsonResponse({"status": "success"}, status=200)

#     # ========================= HANDLERS =========================

#     def handle_invoice_payment_succeeded(self, data):
#         sub_id = data.get("subscription")
#         invoice_id = data.get("id")
#         hosted_invoice_url = data.get("hosted_invoice_url")
#         invoice_pdf = data.get("invoice_pdf")
#         payment_intent_id = data.get("payment_intent")

#         try:
#             payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
#             stripe.Subscription.modify(
#                 sub_id,
#                 default_payment_method=payment_intent.payment_method
#             )
#         except Exception as e:
#             print(f"⚠️ Failed to set default payment method: {e}")

#         updated = self.update_local_subscription(
#             stripe_subscription_id=sub_id,
#             updates={
#                 "status": "active",
#                 "latest_invoice_id": invoice_id,
#                 "latest_invoice_url": hosted_invoice_url,
#                 "latest_invoice_pdf": invoice_pdf,
#             }
#         )

#         if not updated:
#             PendingSubscription.objects.filter(stripe_subscription_id=sub_id).update(status="succeeded")
#             print(f"✅ Fallback: Marked PendingSubscription {sub_id} as succeeded")
#         else:
#             self.log_subscription_history(sub_id, invoice_id)

#     def handle_payment_intent_succeeded(self, data):
#         payment_intent_id = data.get("id")
#         metadata = data.get("metadata", {})
#         subscription_id = metadata.get("subscription_id")

#         pending = PendingSubscription.objects.filter(stripe_payment_intent_id=payment_intent_id).first()
#         if pending:
#             subscription_id = pending.stripe_subscription_id
#             pending.status = "succeeded"
#             pending.save()
#             print(f"✅ Marked PendingSubscription {pending.email} as succeeded")

#         if not subscription_id:
#             print(f"⚠️ Could not determine subscription_id for PI {payment_intent_id}")
#             return

#         updated = self.update_local_subscription(
#             stripe_subscription_id=subscription_id,
#             updates={"status": "active"}
#         )

#         if updated:
#             print(f"✅ Updated Subscription {subscription_id} to active")
#         else:
#             print(f"ℹ️ Subscription {subscription_id} not found yet. Waiting for user signup.")


#     def handle_subscription_updated(self, data):
#         sub_id = data.get("id")
#         new_plan_id = None

#         try:
#             stripe_sub = stripe.Subscription.retrieve(sub_id, expand=["items.data.price", "latest_invoice"])
#             new_price_id = stripe_sub["items"]["data"][0]["price"]["id"]
#             new_plan = SubscriptionPlan.objects.filter(stripe_price_id=new_price_id).first()
#             new_plan_id = new_plan.id if new_plan else None
#         except Exception as e:
#             print(f"⚠️ Could not expand subscription for plan: {e}")
#             new_plan = None

#         updates = {
#             "status": data.get("status"),
#             "cancel_at_period_end": data.get("cancel_at_period_end", False),
#             "current_period_start": make_aware(datetime.fromtimestamp(data["current_period_start"]))
#             if data.get("current_period_start") else None,
#             "current_period_end": make_aware(datetime.fromtimestamp(data["current_period_end"]))
#             if data.get("current_period_end") else None,
#         }

#         invoice_id = data.get("latest_invoice")
#         if invoice_id:
#             try:
#                 invoice = stripe.Invoice.retrieve(invoice_id)
#                 updates["latest_invoice_id"] = invoice.id
#                 updates["latest_invoice_url"] = invoice.hosted_invoice_url
#                 updates["latest_invoice_pdf"] = invoice.invoice_pdf
#             except Exception as e:
#                 print(f"⚠️ Could not retrieve invoice {invoice_id}: {e}")

#         try:
#             with transaction.atomic():
#                 sub = Subscription.objects.select_for_update().get(stripe_subscription_id=sub_id)
#                 old_plan = sub.plan

#                 # 🔁 If user has scheduled a new plan, update it now
#                 if sub.scheduled_plan and sub.scheduled_plan != sub.plan:
#                     try:
#                         stripe.Subscription.modify(
#                             sub_id,
#                             items=[{
#                                 "id": stripe_sub["items"]["data"][0]["id"],
#                                 "price": sub.scheduled_plan.stripe_price_id,
#                             }]
#                         )

#                         SubscriptionPlanChangeLog.objects.create(
#                             user=sub.user,
#                             old_plan=sub.plan,
#                             new_plan=sub.scheduled_plan,
#                         )

#                         sub.plan = sub.scheduled_plan
#                         sub.scheduled_plan = None  # Clear scheduled plan after applying
#                         print(f"✅ Scheduled plan change applied for {sub.user.email}")

#                     except Exception as e:
#                         print(f"⚠️ Failed to apply scheduled plan change: {e}")

#                 elif new_plan and new_plan != old_plan:
#                     SubscriptionPlanChangeLog.objects.create(
#                         user=sub.user,
#                         old_plan=old_plan,
#                         new_plan=new_plan
#                     )
#                     sub.plan = new_plan

#                 for field, value in updates.items():
#                     if value is not None:
#                         setattr(sub, field, value)

#                 sub.save()
#                 print(f"🔄 Subscription {sub_id} updated successfully.")

#         except Subscription.DoesNotExist:
#             print(f"⚠️ Subscription {sub_id} not found")

#     # def handle_subscription_updated(self, data):
#     #     sub_id = data.get("id")
#     #     new_plan_id = None

#     #     try:
#     #         stripe_sub = stripe.Subscription.retrieve(sub_id, expand=["items.data.price", "latest_invoice"])
#     #         new_price_id = stripe_sub["items"]["data"][0]["price"]["id"]
#     #         new_plan = SubscriptionPlan.objects.filter(stripe_price_id=new_price_id).first()
#     #         new_plan_id = new_plan.id if new_plan else None
#     #     except Exception as e:
#     #         print(f"⚠️ Could not expand subscription for plan: {e}")
#     #         new_plan = None

#     #     updates = {
#     #         "status": data.get("status"),
#     #         "cancel_at_period_end": data.get("cancel_at_period_end", False),
#     #         "current_period_start": make_aware(datetime.fromtimestamp(data["current_period_start"]))
#     #         if data.get("current_period_start") else None,
#     #         "current_period_end": make_aware(datetime.fromtimestamp(data["current_period_end"]))
#     #         if data.get("current_period_end") else None,
#     #     }

#     #     invoice_id = data.get("latest_invoice")
#     #     if invoice_id:
#     #         try:
#     #             invoice = stripe.Invoice.retrieve(invoice_id)
#     #             updates["latest_invoice_id"] = invoice.id
#     #             updates["latest_invoice_url"] = invoice.hosted_invoice_url
#     #             updates["latest_invoice_pdf"] = invoice.invoice_pdf
#     #         except Exception as e:
#     #             print(f"⚠️ Could not retrieve invoice {invoice_id}: {e}")

#     #     try:
#     #         with transaction.atomic():
#     #             sub = Subscription.objects.select_for_update().get(stripe_subscription_id=sub_id)
#     #             old_plan = sub.plan
#     #             if new_plan and new_plan != old_plan:
#     #                 # Log plan change
#     #                 SubscriptionPlanChangeLog.objects.create(
#     #                     user=sub.user,
#     #                     old_plan=old_plan,
#     #                     new_plan=new_plan
#     #                 )
#     #                 sub.plan = new_plan

#     #             for field, value in updates.items():
#     #                 if value is not None:
#     #                     setattr(sub, field, value)

#     #             sub.save()
#     #             print(f"🔄 Subscription {sub_id} updated successfully.")

#     #     except Subscription.DoesNotExist:
#     #         print(f"⚠️ Subscription {sub_id} not found")

#     def handle_subscription_deleted(self, data):
#         sub_id = data.get("id")
#         if self.update_local_subscription(sub_id, {"status": "canceled"}):
#             print(f"🚫 Subscription {sub_id} marked as canceled")
#         else:
#             print(f"⚠️ Subscription {sub_id} not found for cancellation")

#     # ========================= HELPERS =========================

#     def update_local_subscription(self, stripe_subscription_id, updates: dict) -> bool:
#         try:
#             sub = Subscription.objects.get(stripe_subscription_id=stripe_subscription_id)
#             for field, value in updates.items():
#                 if value is not None:
#                     setattr(sub, field, value)
#             sub.save()

#             # Remove related pending record if confirmed
#             if updates.get("status") in ["active", "canceled"]:
#                 PendingSubscription.objects.filter(
#                     stripe_subscription_id=sub.stripe_subscription_id
#                 ).delete()

#             return True
#         except Subscription.DoesNotExist:
#             return False

#     def log_subscription_history(self, stripe_subscription_id: str, invoice_id: str):
#         try:
#             sub = Subscription.objects.get(stripe_subscription_id=stripe_subscription_id)
#             invoice = stripe.Invoice.retrieve(invoice_id)
#             if invoice.status != "paid":
#                 print(f"⚠️ Invoice {invoice_id} is not paid yet")
#                 return

#             SubscriptionHistory.objects.create(
#                 user=sub.user,
#                 stripe_invoice_id=invoice.id,
#                 amount_paid=invoice.amount_paid / 100,
#                 currency=invoice.currency.upper(),
#                 paid_at=make_aware(datetime.fromtimestamp(invoice.created)),
#                 plan=sub.plan,
#                 invoice_pdf=invoice.invoice_pdf,
#                 hosted_invoice_url=invoice.hosted_invoice_url
#             )
#             print(f"🧾 Logged SubscriptionHistory for invoice {invoice_id}")
#         except Exception as e:
#             print(f"⚠️ Failed to log SubscriptionHistory for {invoice_id}: {e}")


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(APIView):
    permission_classes = []

    def post(self, request):
        stripe.api_key = SystemSettings.get_solo().stripe_api_key
        webhook_secret = SystemSettings.get_solo().stripe_webhook_secret

        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

        try:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        except (ValueError, stripe.error.SignatureVerificationError):
            return Response(status=400)

        event_type = event.get("type")
        data = event["data"]["object"]
        print(f"✅ Received Stripe event: {event_type}")

        try:
            match event_type:
                case "invoice.payment_succeeded":
                    self.handle_invoice_payment_succeeded(data)

                case "payment_intent.succeeded":
                    self.handle_payment_intent_succeeded(data)

                case "customer.subscription.updated":
                    self.handle_subscription_updated(data)

                case "customer.subscription.deleted":
                    self.handle_subscription_deleted(data)

                case "invoice.payment_failed":
                    print(f"❌ Payment failed for subscription: {data.get('subscription')}")

                case "invoice.created":
                    print(f"🧾 New invoice created. PDF: {data.get('invoice_pdf')}, Hosted: {data.get('hosted_invoice_url')}")

        except Exception as e:
            print(f"⚠️ Webhook processing error for {event_type}: {e}")

        return JsonResponse({"status": "success"}, status=200)

    # ========================= HANDLERS =========================

    def handle_invoice_payment_succeeded(self, data):
        sub_id = data.get("subscription")
        invoice_id = data.get("id")
        hosted_invoice_url = data.get("hosted_invoice_url")
        invoice_pdf = data.get("invoice_pdf")
        payment_intent_id = data.get("payment_intent")

        try:
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            stripe.Subscription.modify(
                sub_id,
                default_payment_method=payment_intent.payment_method
            )
        except Exception as e:
            print(f"⚠️ Failed to set default payment method: {e}")

        updated = self.update_local_subscription(
            stripe_subscription_id=sub_id,
            updates={
                "status": "active",
                "latest_invoice_id": invoice_id,
                "latest_invoice_url": hosted_invoice_url,
                "latest_invoice_pdf": invoice_pdf,
            }
        )

        if not updated:
            # Fallback: update PendingSubscription
            PendingSubscription.objects.filter(stripe_subscription_id=sub_id).update(status="succeeded")
            print(f"✅ Fallback: Marked PendingSubscription {sub_id} as succeeded")
        else:
            self.log_subscription_history(sub_id, invoice_id)

    def handle_payment_intent_succeeded(self, data):
        payment_intent_id = data.get("id")
        metadata = data.get("metadata", {})
        subscription_id = metadata.get("subscription_id")

        pending = PendingSubscription.objects.filter(stripe_payment_intent_id=payment_intent_id).first()
        if pending:
            subscription_id = pending.stripe_subscription_id
            pending.status = "succeeded"
            pending.save()
            print(f"✅ Marked PendingSubscription {pending.email} as succeeded")

        if not subscription_id:
            print(f"⚠️ Could not determine subscription_id for PI {payment_intent_id}")
            return

        updated = self.update_local_subscription(
            stripe_subscription_id=subscription_id,
            updates={"status": "active"}
        )

        if updated:
            print(f"✅ Updated Subscription {subscription_id} to active")
        else:
            print(f"ℹ️ Subscription {subscription_id} not found yet (likely pending user signup)")

    def handle_subscription_updated(self, data):
        sub_id = data.get("id")
        updates = {
            "status": data.get("status"),
            "cancel_at_period_end": data.get("cancel_at_period_end", False),
            "current_period_start": make_aware(datetime.fromtimestamp(data["current_period_start"])) if data.get("current_period_start") else None,
            "current_period_end": make_aware(datetime.fromtimestamp(data["current_period_end"])) if data.get("current_period_end") else None,
        }

        # Invoice info
        invoice_id = data.get("latest_invoice")
        if invoice_id:
            try:
                invoice = stripe.Invoice.retrieve(invoice_id)
                updates["latest_invoice_id"] = invoice.id
                updates["latest_invoice_url"] = invoice.hosted_invoice_url
                updates["latest_invoice_pdf"] = invoice.invoice_pdf
            except Exception as e:
                print(f"⚠️ Could not retrieve invoice {invoice_id}: {e}")

        try:
            with transaction.atomic():
                sub = Subscription.objects.select_for_update().get(stripe_subscription_id=sub_id)

                # Apply scheduled plan if present
                if sub.scheduled_plan and sub.scheduled_plan != sub.plan:
                    try:
                        stripe_sub = stripe.Subscription.retrieve(sub_id, expand=["items.data"])
                        stripe_item_id = stripe_sub["items"]["data"][0]["id"]

                        stripe.Subscription.modify(
                            sub_id,
                            items=[{"id": stripe_item_id, "price": sub.scheduled_plan.stripe_price_id}]
                        )

                        sub.plan = sub.scheduled_plan
                        sub.scheduled_plan = None
                        print(f"✅ Scheduled plan change applied for {sub.user.email}")

                    except Exception as e:
                        print(f"⚠️ Failed to apply scheduled plan change: {e}")

                for field, value in updates.items():
                    if value is not None:
                        setattr(sub, field, value)

                sub.save()
                print(f"🔄 Subscription {sub_id} updated successfully.")

        except Subscription.DoesNotExist:
            print(f"⚠️ Subscription {sub_id} not found (user may not be created yet). Skipping.")

    def handle_subscription_deleted(self, data):
        sub_id = data.get("id")
        if self.update_local_subscription(sub_id, {"status": "canceled"}):
            print(f"🚫 Subscription {sub_id} marked as canceled")
        else:
            print(f"⚠️ Subscription {sub_id} not found. Possibly pending signup.")

    # ========================= HELPERS =========================

    def update_local_subscription(self, stripe_subscription_id, updates: dict) -> bool:
        try:
            sub = Subscription.objects.get(stripe_subscription_id=stripe_subscription_id)
            for field, value in updates.items():
                if value is not None:
                    setattr(sub, field, value)
            sub.save()

            # Cleanup if confirmed
            if updates.get("status") in ["active", "canceled"]:
                PendingSubscription.objects.filter(
                    stripe_subscription_id=sub.stripe_subscription_id
                ).delete()

            return True
        except Subscription.DoesNotExist:
            return False

    def log_subscription_history(self, stripe_subscription_id: str, invoice_id: str):
        try:
            sub = Subscription.objects.get(stripe_subscription_id=stripe_subscription_id)
            invoice = stripe.Invoice.retrieve(invoice_id)
            if invoice.status != "paid":
                print(f"⚠️ Invoice {invoice_id} is not paid yet")
                return

            SubscriptionHistory.objects.create(
                user=sub.user,
                stripe_invoice_id=invoice.id,
                amount_paid=invoice.amount_paid / 100,
                currency=invoice.currency.upper(),
                paid_at=make_aware(datetime.fromtimestamp(invoice.created)),
                plan=sub.plan,
                invoice_pdf=invoice.invoice_pdf,
                hosted_invoice_url=invoice.hosted_invoice_url
            )
            print(f"🧾 Logged SubscriptionHistory for invoice {invoice_id}")
        except Exception as e:
            print(f"⚠️ Failed to log SubscriptionHistory for {invoice_id}: {e}")




