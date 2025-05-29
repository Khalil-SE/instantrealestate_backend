import requests
from rest_framework.response import Response
from rest_framework import status
from system.models import SystemSettings, ChatbotIntegrationLog 

def create_chatbot_user_and_account(user):
    settings = SystemSettings.get_solo()
    headers = {
        "X-ACCESS-TOKEN": settings.admin_chatBot_key,
        "Content-Type": "application/json"
    }

    try:
        # Step 1: Create user
        create_user_resp = requests.post(
            settings.chatbot_create_user_url,
            json={"email": user.email, "full_name": user.first_name + " " + user.last_name,
                    "first_name": user.first_name,
                    "last_name": user.last_name},
            headers=headers,
            timeout=10
        )

        ChatbotIntegrationLog.objects.create(
            user_email=user.email,
            action="create_user",
            status_code=create_user_resp.status_code,
            success=create_user_resp.status_code == 200,
            response_text=create_user_resp.text,
        )

        if create_user_resp.status_code != 200:
            return Response({
                "detail": "Signup successful, but chatbot user creation failed.",
                "chatbot_error": create_user_resp.text
            }, status=status.HTTP_201_CREATED)

        chatbot_user_id = create_user_resp.json().get("id")
        if not chatbot_user_id:
            return Response({
                "detail": "Signup successful, but chatbot response missing user ID."
            }, status=status.HTTP_201_CREATED)

        user.chatBot_user_id = chatbot_user_id
        user.save()

        # Step 2: Create business account
        create_account_resp = requests.post(
            settings.chatbot_create_account_url,
            json={"user_id": chatbot_user_id, "name": user.first_name + " " + user.last_name},
            headers=headers,
            timeout=10
        )

        ChatbotIntegrationLog.objects.create(
            user_email=user.email,
            chatbot_user_id=chatbot_user_id,
            action="create_account",
            status_code=create_account_resp.status_code,
            success=create_account_resp.status_code == 200,
            response_text=create_account_resp.text,
        )

        if create_account_resp.status_code != 200:
            return Response({
                "detail": "Signup successful. Chatbot user created, but business account creation failed.",
                "chatbot_error": create_account_resp.text
            }, status=status.HTTP_201_CREATED)

    except Exception as e:
        ChatbotIntegrationLog.objects.create(
            user_email=user.email,
            action="exception",
            status_code=0,
            success=False,
            response_text=str(e),
        )
        return Response({
            "detail": "Signup successful, but chatbot integration failed.",
            "chatbot_error": str(e)
        }, status=status.HTTP_201_CREATED)

    #  If all succeeded, return None
    return None
