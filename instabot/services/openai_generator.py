from openai import OpenAI
from system.models import SystemSettings

def generate_social_media_post(ai_post_description: str, keyword: str) -> str:
    settings = SystemSettings.get_solo()
    prompt_template = settings.instabot_ai_prompt
    api_key = settings.openAI_api_key

    if not (prompt_template and api_key):
        return "AI generation not configured properly."

    # Inject variables into prompt
    prompt = prompt_template.replace("#AI_Post_Description#", ai_post_description).replace("#keyword#", keyword.upper())

    try:
        client = OpenAI(api_key=api_key)

        # Use responses.create as per latest OpenAI SDK
        response = client.responses.create(
            model="gpt-4o-mini",
            # model="gpt-4.1",
            input=prompt
        )

        return response.output_text.strip()

    except Exception as e:
        # You can log this exception if needed
        return "AI generation failed. Please edit manually." + str(e) 
