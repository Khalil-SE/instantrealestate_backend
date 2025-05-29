# shared/views/keyword.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from shared.models import Keyword
from instabot.models import InstaBot  # for now, since only InstaBot is using it

class KeywordAvailabilityView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        keyword_text = request.query_params.get("text", "").strip().lower()

        if not keyword_text:
            return Response({"error": "Keyword is required."}, status=400)

        keyword = Keyword.objects.filter(text=keyword_text).first()

        if not keyword:
            return Response({"available": True})  # keyword not in use

        in_use = InstaBot.objects.filter(keyword=keyword).exists()
        return Response({"available": not in_use})
