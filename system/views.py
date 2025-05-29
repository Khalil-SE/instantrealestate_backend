from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .models import SystemSettings
from .serializers import SystemSettingsSerializer

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
