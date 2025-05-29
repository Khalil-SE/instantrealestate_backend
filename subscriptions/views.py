import stripe
# import json
import logging
import time
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import SubscriptionPlan, Subscription, SubscriptionHistory
from system.models import SystemSettings  

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

# from django.utils.timezone import make_aware
from django.utils.timezone import now
from datetime import datetime
from django.utils.timezone import make_aware
from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError


# subscriptions/views.py (add this)
from rest_framework.generics import ListAPIView
from .models import SubscriptionPlan
from .serializers import SubscriptionPlanSerializer

class SubscriptionPlanListView(ListAPIView):
    queryset = SubscriptionPlan.objects.all().order_by("id")
    serializer_class = SubscriptionPlanSerializer
    permission_classes = []  # Public access — no auth required

# For the current subscription Of logged in user
class CurrentSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        subscription = Subscription.objects.filter(user=request.user).first()

        if not subscription:
            return Response({"has_subscription": False})

        return Response({
            "has_subscription": True,
            "status": subscription.status,
            "plan": subscription.plan.name,
            "cancel_at_period_end": subscription.cancel_at_period_end,
            "current_period_start": subscription.current_period_start,
            "current_period_end": subscription.current_period_end,
        })

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

# subscriptions/views.py
class CancelSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        try:
            subscription = Subscription.objects.get(user=user)
            stripe.api_key = SystemSettings.get_solo().stripe_api_key

            stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=True
            )

            subscription.cancel_at_period_end = True
            subscription.save()

            return Response({"success": True, "message": "Subscription marked to cancel at period end."})
        except Subscription.DoesNotExist:
            return Response({"error": "No active subscription found."}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

# subscriptions/views.py
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


class CreateCheckoutSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        plan_id = request.data.get("plan_id")
        if not plan_id:
            return Response({"detail": "Plan ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Retrieve the selected plan
        try:
            plan = SubscriptionPlan.objects.get(id=plan_id)
        except SubscriptionPlan.DoesNotExist:
            return Response({"detail": "Invalid subscription plan."}, status=status.HTTP_404_NOT_FOUND)

        # Load Stripe API Key from system settings
        settings_obj = SystemSettings.get_solo()
        stripe.api_key = settings_obj.stripe_api_key

        try:
            # Create the Stripe Checkout Session
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                mode="subscription",
                line_items=[{
                    "price": plan.stripe_product_id,
                    "quantity": 1,
                }],
                customer_email=request.user.email,
                success_url=request.build_absolute_uri(settings_obj.stripe_return_url),
                cancel_url=request.build_absolute_uri(settings_obj.stripe_return_url),
                metadata={
                    "user_id": str(request.user.id),
                    "plan_name": plan.name,
                }
            )

            return Response({"checkout_url": session.url}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"detail": f"Failed to create checkout session: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

logger = logging.getLogger("stripe_webhooks")
User = get_user_model()

ALLOWED_EVENTS = {
    "checkout.session.completed",
    "invoice.payment_succeeded",
    "invoice.payment_failed",
    "customer.subscription.updated",
    "customer.subscription.deleted",
}


@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(APIView):
    def post(self, request, *args, **kwargs):
        settings_obj = SystemSettings.get_solo()
        stripe.api_key = settings_obj.stripe_api_key
        stripe.api_version = "2024-04-10"  #  Explicit version locking

        webhook_secret = settings_obj.stripe_webhook_secret
        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

        try:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        except (ValueError, stripe.error.SignatureVerificationError) as e:
            logger.error(f"Webhook verification failed: {e}")
            return Response(status=400)

        event_type = event["type"]
        logger.info(f"Stripe event received: {event_type}")

        if event_type not in ALLOWED_EVENTS:
            logger.info(f"Ignoring untracked event type: {event_type}")
            return Response(status=200)

        try:
            if event_type == "checkout.session.completed":
                self._handle_checkout_completed(event)
            elif event_type == "invoice.payment_succeeded":
                self._handle_invoice_payment_succeeded(event)
            elif event_type == "invoice.payment_failed":
                self._handle_invoice_payment_failed(event)
            elif event_type == "customer.subscription.updated":
                self._handle_subscription_updated(event)
            elif event_type == "customer.subscription.deleted":
                self._handle_subscription_deleted(event)
        except Exception as e:
            logger.error(f"Error processing {event_type}: {str(e)}", exc_info=True)
            return Response(status=500)

        return Response(status=200)

    def _handle_checkout_completed(self, event):
        session = event["data"]["object"]
        metadata = session.get("metadata", {})
        user_id = metadata.get("user_id")
        plan_name = metadata.get("plan_name")
        customer_id = session.get("customer")
        subscription_id = session.get("subscription")

        if not all([user_id, plan_name, customer_id, subscription_id]):
            logger.warning("Incomplete metadata in checkout.session.completed")
            return

        plan = SubscriptionPlan.objects.filter(name=plan_name).first()
        if not plan:
            logger.warning(f"Plan not found: {plan_name}")
            return

        stripe_subscription = stripe.Subscription.retrieve(subscription_id)
        items = stripe_subscription.get("items", {}).get("data", [])
        if not items:
            logger.warning("No items found in subscription.")
            return

        item = items[0]
        start_ts = item.get("current_period_start")
        end_ts = item.get("current_period_end")

        if not (start_ts and end_ts):
            logger.warning("Missing start or end timestamp in subscription item.")
            return

        start_dt = make_aware(datetime.fromtimestamp(start_ts))
        end_dt = make_aware(datetime.fromtimestamp(end_ts))
        cancel_at_period_end = stripe_subscription.get("cancel_at_period_end", False)

        Subscription.objects.update_or_create(
            user_id=user_id,
            defaults={
                "plan": plan,
                "stripe_customer_id": customer_id,
                "stripe_subscription_id": subscription_id,
                "status": "active",
                "current_period_start": start_dt,
                "current_period_end": end_dt,
                "cancel_at_period_end": cancel_at_period_end,
            },
        )
        logger.info(f"Subscription created or updated for user {user_id}")

    def _handle_invoice_payment_succeeded(self, event):
        invoice = event["data"]["object"]
        customer_id = invoice.get("customer")

        # Retry once after 2 seconds if subscription is not yet available
        subscription = Subscription.objects.filter(stripe_customer_id=customer_id).first()
        if not subscription:
            logger.warning(f"No subscription found for customer {customer_id}, retrying in 2 seconds...")
            time.sleep(2)
            subscription = Subscription.objects.filter(stripe_customer_id=customer_id).first()

            if not subscription:
                logger.warning(f"Retry failed: still no subscription for customer {customer_id}")
                return

        user = subscription.user
        plan = subscription.plan

        line = invoice["lines"]["data"][0]
        paid_ts = invoice.get("status_transitions", {}).get("paid_at")
        paid_at = make_aware(datetime.fromtimestamp(paid_ts)) if paid_ts else now()

        SubscriptionHistory.objects.create(
            user=user,
            stripe_invoice_id=invoice["id"],
            amount_paid=invoice.get("amount_paid") / 100,
            currency=invoice.get("currency"),
            paid_at=paid_at,
            plan=plan,
        )
        logger.info(f"Subscription history recorded for {user.email}")

    def _handle_invoice_payment_failed(self, event):
        invoice = event["data"]["object"]
        customer_id = invoice.get("customer")

        subscription = Subscription.objects.filter(stripe_customer_id=customer_id).first()
        if not subscription:
            logger.warning(f"Payment failed but no local subscription found for customer {customer_id}")
            return

        subscription.status = "incomplete"
        subscription.save()
        logger.info(f"Subscription marked as incomplete due to payment failure for customer {customer_id}")

    def _handle_subscription_updated(self, event):
        stripe_sub = event["data"]["object"]
        customer_id = stripe_sub.get("customer")
        cancel_at_period_end = stripe_sub.get("cancel_at_period_end", False)
        current_period_start = stripe_sub.get("current_period_start")
        current_period_end = stripe_sub.get("current_period_end")

        subscription = Subscription.objects.filter(stripe_customer_id=customer_id).first()
        if not subscription:
            logger.warning(f"No local subscription found to update for customer {customer_id}")
            return

        subscription.cancel_at_period_end = cancel_at_period_end
        if current_period_start and current_period_end:
            subscription.current_period_start = make_aware(datetime.fromtimestamp(current_period_start))
            subscription.current_period_end = make_aware(datetime.fromtimestamp(current_period_end))
        subscription.save()
        logger.info(f"Subscription updated for customer {customer_id}")

    def _handle_subscription_deleted(self, event):
        stripe_sub = event["data"]["object"]
        customer_id = stripe_sub.get("customer")

        subscription = Subscription.objects.filter(stripe_customer_id=customer_id).first()
        if not subscription:
            logger.warning(f"Tried to delete nonexistent subscription for customer {customer_id}")
            return

        subscription.status = "canceled"
        subscription.save()
        logger.info(f"Subscription marked as canceled for customer {customer_id}")

# version 4 working fine
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
#         webhook_secret = settings_obj.stripe_webhook_secret

#         payload = request.body
#         sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

#         try:
#             event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
#         except (ValueError, stripe.error.SignatureVerificationError) as e:
#             logger.error(f"Webhook verification failed: {e}")
#             return Response(status=400)

#         event_type = event["type"]
#         logger.info(f"Stripe event received: {event_type}")

#         if event_type not in ALLOWED_EVENTS:
#             logger.info(f"Ignoring untracked event type: {event_type}")
#             return Response(status=200)

#         try:
#             handler_map = {
#                 "checkout.session.completed": self._handle_checkout_completed,
#                 "invoice.payment_succeeded": self._handle_invoice_payment_succeeded,
#                 "invoice.payment_failed": self._handle_invoice_payment_failed,
#                 "customer.subscription.updated": self._handle_subscription_updated,
#                 "customer.subscription.deleted": self._handle_subscription_deleted,
#             }
#             handler = handler_map.get(event_type)
#             if handler:
#                 handler(event)

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
#         logger.info(f"Subscription created or updated for user {user_id}")

#     def _handle_invoice_payment_succeeded(self, event):
#         invoice = event["data"]["object"]
#         customer_id = invoice.get("customer")

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
#         logger.info(f"Subscription history recorded for user {user.email}")

#     def _handle_invoice_payment_failed(self, event):
#         invoice = event["data"]["object"]
#         customer_id = invoice.get("customer")

#         subscription = Subscription.objects.filter(stripe_customer_id=customer_id).first()
#         if not subscription:
#             logger.warning(f"Payment failed, but no local subscription found for customer {customer_id}")
#             return

#         subscription.status = "incomplete"
#         subscription.save()
#         logger.info(f"Subscription marked as incomplete due to payment failure for customer {customer_id}")

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
#         logger.info(f"Subscription updated for customer {customer_id}")

#     def _handle_subscription_deleted(self, event):
#         stripe_sub = event["data"]["object"]
#         customer_id = stripe_sub.get("customer")

#         subscription = Subscription.objects.filter(stripe_customer_id=customer_id).first()
#         if not subscription:
#             logger.warning(f"Tried to delete nonexistent subscription for customer {customer_id}")
#             return

#         subscription.status = "canceled"
#         subscription.save()
#         logger.info(f"Subscription marked as canceled for customer {customer_id}")


# Version 3 Working Code
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
#         webhook_secret = settings_obj.stripe_webhook_secret

#         payload = request.body
#         sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

#         try:
#             event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
#         except (ValueError, stripe.error.SignatureVerificationError) as e:
#             logger.error(f"Webhook verification failed: {e}")
#             return Response(status=400)

#         event_type = event["type"]
#         logger.info(f"Stripe event received: {event_type}")

#         if event_type not in ALLOWED_EVENTS:
#             logger.info(f"Ignoring untracked event type: {event_type}")
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
#         logger.info(f"Subscription created or updated for user {user_id}")

#     def _handle_invoice_payment_succeeded(self, event):
#         invoice = event["data"]["object"]
#         customer_id = invoice.get("customer")

#         # Retry logic in case subscription hasn't yet been saved
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
#         price = line.get("price", {})
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
#         logger.info(f"Subscription history recorded for {user.email}")

#     def _handle_invoice_payment_failed(self, event):
#         invoice = event["data"]["object"]
#         customer_id = invoice.get("customer")

#         subscription = Subscription.objects.filter(stripe_customer_id=customer_id).first()
#         if not subscription:
#             logger.warning(f"Payment failed, but no local subscription found for customer {customer_id}")
#             return

#         subscription.status = "incomplete"
#         subscription.save()
#         logger.info(f"Subscription marked as incomplete due to payment failure: {customer_id}")


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
#         logger.info(f"Subscription updated for customer {customer_id}")

#     def _handle_subscription_deleted(self, event):
#         stripe_sub = event["data"]["object"]
#         customer_id = stripe_sub.get("customer")

#         subscription = Subscription.objects.filter(stripe_customer_id=customer_id).first()
#         if not subscription:
#             logger.warning(f"Tried to delete nonexistent subscription for {customer_id}")
#             return

#         subscription.status = "canceled"
#         subscription.save()
#         logger.info(f"Subscription marked as canceled for customer {customer_id}")

# Version 2 Working Code
# logger = logging.getLogger("stripe_webhooks")
# User = get_user_model()

# ALLOWED_EVENTS = {
#     "checkout.session.completed",
#     "invoice.payment_succeeded",
#     "invoice.payment_failed",
#     "customer.subscription.deleted",
#     "customer.subscription.updated",
# }


# @method_decorator(csrf_exempt, name='dispatch')
# class StripeWebhookView(APIView):
#     def post(self, request, *args, **kwargs):
#         settings_obj = SystemSettings.get_solo()
#         stripe.api_key = settings_obj.stripe_api_key
#         webhook_secret = settings_obj.stripe_webhook_secret

#         payload = request.body
#         sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

#         try:
#             event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
#         except (ValueError, stripe.error.SignatureVerificationError) as e:
#             logger.error(f"❌ Invalid Stripe webhook: {e}")
#             return Response(status=400)

#         event_type = event.get("type")
#         logger.info(f"📩 Stripe event received: {event_type}")

#         if event_type not in ALLOWED_EVENTS:
#             logger.info(f"🔕 Ignoring unhandled event type: {event_type}")
#             return Response(status=200)

#         try:
#             if event_type == "checkout.session.completed":
#                 session = event["data"]["object"]
#                 metadata = session.get("metadata", {})
#                 user_id = metadata.get("user_id")
#                 plan_name = metadata.get("plan_name")
#                 customer_id = session.get("customer")
#                 subscription_id = session.get("subscription")

#                 if not all([user_id, plan_name, customer_id, subscription_id]):
#                     logger.warning("⚠️ Missing data in checkout.session.completed")
#                     return Response(status=400)

#                 plan = SubscriptionPlan.objects.filter(name=plan_name).first()
#                 if not plan:
#                     logger.warning(f"⚠️ Plan not found: {plan_name}")
#                     return Response(status=404)

#                 stripe_subscription = stripe.Subscription.retrieve(subscription_id)
#                 items = stripe_subscription.get("items", {}).get("data", [])

#                 if not items:
#                     logger.warning("⚠️ No items in Stripe subscription.")
#                     return Response(status=400)

#                 item = items[0]
#                 start_dt = make_aware(datetime.fromtimestamp(item["current_period_start"]))
#                 end_dt = make_aware(datetime.fromtimestamp(item["current_period_end"]))
#                 cancel_at_period_end = stripe_subscription.get("cancel_at_period_end", False)

#                 Subscription.objects.update_or_create(
#                     user_id=user_id,
#                     defaults={
#                         "plan": plan,
#                         "stripe_customer_id": customer_id,
#                         "stripe_subscription_id": subscription_id,
#                         "status": "active",
#                         "current_period_start": start_dt,
#                         "current_period_end": end_dt,
#                         "cancel_at_period_end": cancel_at_period_end,
#                     }
#                 )
#                 logger.info(f"✅ Subscription created/updated for user: {user_id}")

#             # elif event_type == "invoice.payment_succeeded":
#             #     invoice = event["data"]["object"]
#             #     customer_id = invoice.get("customer")
#             #     subscription = Subscription.objects.filter(stripe_customer_id=customer_id).first()

#             #     if not subscription:
#             #         logger.warning(f"⚠️ No subscription for customer {customer_id}")
#             #         return Response(status=200)

#             #     user = subscription.user
#             #     plan = subscription.plan
#             #     line = invoice["lines"]["data"][0]
#             #     price = line.get("price", {})
#             #     paid_ts = invoice.get("status_transitions", {}).get("paid_at")
#             #     paid_at = make_aware(datetime.fromtimestamp(paid_ts)) if paid_ts else now()

#             #     SubscriptionHistory.objects.create(
#             #         user=user,
#             #         stripe_invoice_id=invoice["id"],
#             #         amount_paid=invoice.get("amount_paid") / 100,
#             #         currency=invoice.get("currency"),
#             #         paid_at=paid_at,
#             #         plan=plan,
#             #     )
#             #     logger.info(f"🧾 Invoice saved for user: {user.email}")
#             elif event_type == "invoice.payment_succeeded":
#                 invoice = event["data"]["object"]
#                 customer_id = invoice.get("customer")

#                 subscription = Subscription.objects.filter(stripe_customer_id=customer_id).first()

#                 # Retry lookup after short delay if subscription not found (race condition)
#                 if not subscription:
#                     logger.warning(f"⏳ Subscription not found yet for customer {customer_id}. Retrying...")
#                     import time
#                     time.sleep(2)  # Wait 2 seconds
#                     subscription = Subscription.objects.filter(stripe_customer_id=customer_id).first()

#                 if not subscription:
#                     logger.error(f"❌ Still no subscription found for customer {customer_id} after retry.")
#                     return Response(status=200)

#                 user = subscription.user
#                 plan = subscription.plan

#                 line = invoice["lines"]["data"][0]
#                 price = line.get("price", {})
#                 paid_ts = invoice.get("status_transitions", {}).get("paid_at")
#                 paid_at = make_aware(datetime.fromtimestamp(paid_ts)) if paid_ts else now()

#                 SubscriptionHistory.objects.create(
#                     user=user,
#                     stripe_invoice_id=invoice["id"],
#                     amount_paid=invoice.get("amount_paid") / 100,
#                     currency=invoice.get("currency"),
#                     paid_at=paid_at,
#                     plan=plan,
#                 )
#                 logger.info(f"🧾 Invoice saved for user: {user.email}")

#             elif event_type == "invoice.payment_failed":
#                 invoice = event["data"]["object"]
#                 customer_id = invoice.get("customer")
#                 subscription = Subscription.objects.filter(stripe_customer_id=customer_id).first()

#                 if subscription:
#                     subscription.status = "incomplete"
#                     subscription.save()
#                     logger.warning(f"⚠️ Payment failed. Marked subscription incomplete for {customer_id}")

#             elif event_type == "customer.subscription.deleted":
#                 stripe_data = event["data"]["object"]
#                 subscription_id = stripe_data.get("id")
#                 sub = Subscription.objects.filter(stripe_subscription_id=subscription_id).first()

#                 if sub:
#                     sub.status = "canceled"
#                     sub.save()
#                     logger.info(f"🗑️ Subscription marked as canceled: {subscription_id}")

#         except Exception as e:
#             logger.error(f"❌ Error processing {event_type}: {str(e)}", exc_info=True)
#             return Response(status=500)

#         return Response(status=200)



# Version 1 Working Code
# logger = logging.getLogger("stripe_webhooks")
# User = get_user_model()

# ALLOWED_EVENTS = {
#     "checkout.session.completed",
#     "invoice.payment_succeeded",
#     "invoice.created",
#     "invoice.finalized",
#     "customer.subscription.created",
#     "customer.subscription.updated",
# }

# @method_decorator(csrf_exempt, name='dispatch')
# class StripeWebhookView(APIView):
#     def post(self, request, *args, **kwargs):
#         settings_obj = SystemSettings.get_solo()
#         webhook_secret = settings_obj.stripe_webhook_secret
#         stripe.api_key = settings_obj.stripe_api_key

#         payload = request.body
#         sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

#         try:
#             event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
#         except (ValueError, stripe.error.SignatureVerificationError) as e:
#             logger.error(f"❌ Webhook signature verification failed: {e}")
#             return Response(status=400)

#         event_type = event.get("type")
#         logger.info(f"📨 Stripe event received: {event_type}")

#         if event_type not in ALLOWED_EVENTS:
#             logger.info(f"🔕 Ignoring untracked event type: {event_type}")
#             return Response(status=200)

#         try:
            
#             if event_type == "checkout.session.completed":
#                 session = event["data"]["object"]
#                 metadata = session.get("metadata", {})
#                 user_id = metadata.get("user_id")
#                 plan_name = metadata.get("plan_name")
#                 customer_id = session.get("customer")
#                 subscription_id = session.get("subscription")

#                 if not all([user_id, plan_name, customer_id, subscription_id]):
#                     logger.warning("Missing metadata or IDs in checkout.session.completed")
#                     return Response(status=400)

#                 plan = SubscriptionPlan.objects.filter(name=plan_name).first()
#                 if not plan:
#                     logger.warning(f"Plan not found: {plan_name}")
#                     return Response(status=404)

#                 try:
#                     stripe.api_key = SystemSettings.get_solo().stripe_api_key
#                     stripe_subscription = stripe.Subscription.retrieve(subscription_id)

#                     # ✅ Extract period_start/end from the first subscription item
#                     items = stripe_subscription.get("items", {}).get("data", [])
#                     if not items:
#                         logger.warning("No items found in Stripe subscription.")
#                         return Response(status=400)

#                     item = items[0]
#                     current_period_start = item.get("current_period_start")
#                     current_period_end = item.get("current_period_end")

#                     if not (current_period_start and current_period_end):
#                         logger.warning("Missing period dates in subscription item.")
#                         return Response(status=400)

#                     # Convert to timezone-aware datetime
#                     # from datetime import datetime
#                     # from django.utils.timezone import make_aware

#                     start_dt = make_aware(datetime.fromtimestamp(current_period_start))
#                     end_dt = make_aware(datetime.fromtimestamp(current_period_end))

#                     cancel_at_period_end = stripe_subscription.get("cancel_at_period_end", False)

#                     # ✅ Save or update Subscription
#                     Subscription.objects.update_or_create(
#                         user_id=user_id,
#                         defaults={
#                             "plan": plan,
#                             "stripe_customer_id": customer_id,
#                             "stripe_subscription_id": subscription_id,
#                             "status": "active",
#                             "current_period_start": start_dt,
#                             "current_period_end": end_dt,
#                             "cancel_at_period_end": cancel_at_period_end,
#                         }
#                     )

#                     logger.info(f"✅ Subscription saved for user_id: {user_id}")

#                 except Exception as e:
#                     logger.error(f"❌ Error processing checkout.session.completed: {str(e)}", exc_info=True)
#                     return Response(status=500)

#             # ✅ Handle Invoice Payment Success (Record History)
#             elif event_type == "invoice.payment_succeeded":
#                 invoice = event["data"]["object"]
#                 customer_id = invoice.get("customer")
#                 subscription = Subscription.objects.filter(stripe_customer_id=customer_id).first()

#                 if not subscription:
#                     logger.warning(f"⚠️ No subscription found for customer {customer_id}")
#                     return Response(status=200)

#                 user = subscription.user
#                 plan = subscription.plan

#                 line = invoice["lines"]["data"][0]
#                 price = line.get("price", {})
#                 price_id = price.get("id")
#                 product_id = price.get("product")

#                 paid_ts = invoice.get("status_transitions", {}).get("paid_at")
#                 paid_at = make_aware(datetime.fromtimestamp(paid_ts)) if paid_ts else now()

#                 SubscriptionHistory.objects.create(
#                     user=user,
#                     stripe_invoice_id=invoice["id"],
#                     amount_paid=invoice.get("amount_paid") / 100,
#                     currency=invoice.get("currency"),
#                     paid_at=paid_at,
#                     plan=plan
#                 )
#                 logger.info(f"🧾 Invoice history saved for user: {user.email}")

#             elif event_type == "customer.subscription.updated":
#                 logger.info("ℹ️ Subscription updated event received — not handled yet.")

#         except Exception as e:
#             logger.error(f"❌ Error processing {event_type}: {str(e)}", exc_info=True)
#             return Response(status=500)

#         return Response(status=200)


