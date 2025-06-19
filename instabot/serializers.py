from rest_framework import serializers
from instabot.models import PublicReplyTemplate, PublicReplyContent, InstaBot
from shared.serializers import KeywordSerializer
from shared.models import Keyword
from shared.serializers import WritableKeywordField

class PublicReplyContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PublicReplyContent
        fields = ['id', 'text']
        read_only_fields = ['id']

class PublicReplyTemplateSerializer(serializers.ModelSerializer):
    replies = PublicReplyContentSerializer(many=True, required=False)

    class Meta:
        model = PublicReplyTemplate
        fields = ['id', 'name', 'created_at', 'replies']
        read_only_fields = ['id', 'created_at']

    def create(self, validated_data):
        replies_data = validated_data.pop('replies', [])
        template = PublicReplyTemplate.objects.create(**validated_data)
        for reply_data in replies_data:
            PublicReplyContent.objects.create(template=template, **reply_data)
        return template

    def update(self, instance, validated_data):
        replies_data = validated_data.pop('replies', None)
        instance.name = validated_data.get('name', instance.name)
        instance.save()
        if replies_data is not None:
            instance.replies.all().delete()
            for reply_data in replies_data:
                PublicReplyContent.objects.create(template=instance, **reply_data)
        return instance



class InstaBotSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    # Use custom field instead of nested serializer
    keyword = WritableKeywordField()

    public_reply_template_id = serializers.PrimaryKeyRelatedField(
        queryset=PublicReplyTemplate.objects.all(),
        source='public_reply_template',
        write_only=True,
        required=False,
        allow_null=True,
    )
    public_reply_template = PublicReplyTemplateSerializer(read_only=True)

    email_recipients = serializers.ListField(child=serializers.EmailField(), required=False)

    class Meta:
        model = InstaBot
        fields = [
            'id', 'user', 'keyword', 'status',
            'message_type', 'image_url',
            'title', 'message',
            'button1_text', 'button1_url',
            'button2_text', 'button2_url',
            'button3_text', 'button3_url',
            'public_reply_template', 'public_reply_template_id',
            'ai_post_description','email_recipients',
            'comment_count', 'click_count', 'created_at',
        ]
        read_only_fields = ['id', 'comment_count', 'click_count', 'created_at']

    def create(self, validated_data):
        keyword_obj = validated_data.pop('keyword')

        if hasattr(keyword_obj, 'instabot'):
            raise serializers.ValidationError("This keyword is already associated with an InstaBot.")

        validated_data['keyword'] = keyword_obj
        return InstaBot.objects.create(**validated_data)

    def update(self, instance, validated_data):
        keyword_obj = validated_data.pop("keyword", None)

        if keyword_obj:
            # Allow keyword reuse only if it's linked to the same instance
            if hasattr(keyword_obj, 'instabot') and keyword_obj.instabot.id != instance.id:
                raise serializers.ValidationError("This keyword is already associated with another InstaBot.")
            instance.keyword = keyword_obj

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance



# class InstaBotSerializer(serializers.ModelSerializer):
#     user = serializers.HiddenField(default=serializers.CurrentUserDefault())

#     # keyword = KeywordSerializer()
#     keyword = WritableKeywordField()

#     public_reply_template_id = serializers.PrimaryKeyRelatedField(
#         queryset=PublicReplyTemplate.objects.all(),
#         source='public_reply_template',
#         write_only=True,
#         required=False,
#         allow_null=True,
#     )
#     public_reply_template = PublicReplyTemplateSerializer(read_only=True)

#     class Meta:
#         model = InstaBot
#         fields = [
#             'id', 'user', 'keyword', 'status',
#             'message_type', 'image_url',
#             'title', 'message',
#             'button1_text', 'button1_url',
#             'button2_text', 'button2_url',
#             'button3_text', 'button3_url',
#             'public_reply_template', 'public_reply_template_id',
#             'ai_post_description',
#             'comment_count', 'click_count', 'created_at',
#         ]
#         read_only_fields = ['id', 'comment_count', 'click_count', 'created_at']

#     def create(self, validated_data):
#         keyword_data = validated_data.pop('keyword')
#         keyword_text = keyword_data['text'].strip().lower()

#         keyword_obj, created = Keyword.objects.get_or_create(text=keyword_text)
#         # if keyword_obj.instabot_set.exists():
#         #     raise serializers.ValidationError("Keyword already linked to another InstaBot.")

#         if hasattr(keyword_obj, 'instabot'):
#             raise serializers.ValidationError("This keyword is already associated with an InstaBot.")


#         validated_data['keyword'] = keyword_obj
#         return InstaBot.objects.create(**validated_data)

#     def update(self, instance, validated_data):

#         print("Point came here for update")

#         keyword_data = validated_data.pop('keyword', None)
#         if keyword_data:
#             keyword_text = keyword_data['text'].strip().lower()
#             keyword_obj, created = Keyword.objects.get_or_create(text=keyword_text)
#             if hasattr(keyword_obj, 'instabot') and keyword_obj.instabot.id != instance.id:
#                 raise serializers.ValidationError("Keyword already linked to another InstaBot.")
#             instance.keyword = keyword_obj

#         for attr, value in validated_data.items():
#             setattr(instance, attr, value)

#         instance.save()
#         return instance

# class InstaBotSerializer(serializers.ModelSerializer):
#     keyword = KeywordSerializer()
#     public_reply_template = serializers.PrimaryKeyRelatedField(
#         queryset=PublicReplyTemplate.objects.all(),
#         required=False,
#         allow_null=True
#     )

#     class Meta:
#         model = InstaBot
#         fields = [
#             'id', 'user', 'keyword', 'status',
#             'message_type', 'image_url',
#             'title', 'message',
#             'button1_text', 'button1_url',
#             'button2_text', 'button2_url',
#             'button3_text', 'button3_url',
#             'public_reply_template', 'ai_post_description',
#             'comment_count', 'click_count', 'created_at',
#         ]
#         read_only_fields = ['id', 'comment_count', 'click_count', 'created_at', 'user']

#     def create(self, validated_data):
#         keyword_data = validated_data.pop("keyword")
#         keyword_text = keyword_data.get("text").strip().lower()

#         keyword_obj, _ = Keyword.objects.get_or_create(text=keyword_text)

#         validated_data["keyword"] = keyword_obj
#         return InstaBot.objects.create(**validated_data)

#     def update(self, instance, validated_data):
#         keyword_data = validated_data.pop("keyword", None)
#         if keyword_data:
#             keyword_text = keyword_data.get("text").strip().lower()
#             keyword_obj, _ = Keyword.objects.get_or_create(text=keyword_text)
#             instance.keyword = keyword_obj

#         for field, value in validated_data.items():
#             setattr(instance, field, value)

#         instance.save()
#         return instance


# class InstaBotSerializer(serializers.ModelSerializer):
#     keyword = KeywordSerializer()

#     public_reply_template = PublicReplyTemplateSerializer(read_only=True)

#     class Meta:
#         model = InstaBot
#         fields = [
#             'id', 'user', 'keyword', 'status',
#             'message_type', 'image_url',
#             'title', 'message',
#             'button1_text', 'button1_url',
#             'button2_text', 'button2_url',
#             'button3_text', 'button3_url',
#             'public_reply_template', 'ai_post_description',
#             'comment_count', 'click_count', 'created_at',
#         ]
#         read_only_fields = ['id', 'comment_count', 'click_count', 'created_at', 'user']

#     def create(self, validated_data):
#         keyword_data = validated_data.pop('keyword', None)

#         if not keyword_data or not keyword_data.get("text"):
#             raise serializers.ValidationError({"keyword": "Keyword text is required."})

#         keyword_text = keyword_data["text"].strip().lower()

#         keyword_obj, created = Keyword.objects.get_or_create(text=keyword_text)

#         # Check if this keyword is already assigned to another InstaBot
#         if hasattr(keyword_obj, 'instabot'):
#             raise serializers.ValidationError({"keyword": f"The keyword '{keyword_text}' is already in use."})

#         instabot = InstaBot.objects.create(keyword=keyword_obj, **validated_data)
#         return instabot
# class InstaBotSerializer(serializers.ModelSerializer):
#     keyword = KeywordSerializer()
#     public_reply_template = PublicReplyTemplateSerializer(read_only=True)

#     class Meta:
#         model = InstaBot
#         fields = [
#             'id', 'user', 'keyword', 'status',
#             'message_type', 'image_url',
#             'title', 'message',
#             'button1_text', 'button1_url',
#             'button2_text', 'button2_url',
#             'button3_text', 'button3_url',
#             'public_reply_template', 'ai_post_description',
#             'comment_count', 'click_count', 'created_at',
#         ]
#         read_only_fields = ['id', 'comment_count', 'click_count', 'created_at']
