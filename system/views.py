from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .models import SystemSettings, ContactMessage
from .serializers import SystemSettingsSerializer, ContactUsSerializer
from django.core.mail import send_mail

class SystemSettingsView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        settings = SystemSettings.get_solo()
        serializer = SystemSettingsSerializer(settings)
        return Response(serializer.data)

    def patch(self, request):
        settings = SystemSettings.get_solo()
        serializer = SystemSettingsSerializer(settings, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)




class ContactUsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ContactUsSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        subject = serializer.validated_data['subject']
        message = serializer.validated_data['message']
        settings = SystemSettings.get_solo()

        support_email = settings.email_support or settings.email_from
        if not support_email:
            return Response({"error": "Support email not configured."}, status=500)

        full_message = f"From: {user.first_name + " " + user.last_name} <{user.email}>\n\n{message}"

        contact_record = ContactMessage.objects.create(
            user=user,
            subject=subject,
            message=message
        )

        try:
            send_mail(
                subject=subject,
                message=full_message,
                from_email=settings.email_from,
                recipient_list=[support_email],
                fail_silently=False,
            )
            contact_record.email_sent = True
            contact_record.save()
            return Response({"detail": "Message sent successfully!"}, status=200)
        except Exception as e:
            contact_record.email_sent = False
            contact_record.save()
            return Response({"error": "Failed to send message."}, status=500)



