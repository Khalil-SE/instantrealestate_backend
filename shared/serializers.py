from rest_framework import serializers
from shared.models import Keyword

class KeywordSerializer(serializers.ModelSerializer):
    class Meta:
        model = Keyword
        fields = ['id', 'text', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


# This function is used for updation of the keyword field in the InstaBotSerializer
class WritableKeywordField(serializers.Field):
    def to_internal_value(self, data):
        text = data.get("text", "").strip().lower()
        if not text:
            raise serializers.ValidationError("Keyword text is required.")
        keyword_obj, created = Keyword.objects.get_or_create(text=text)
        return keyword_obj

    def to_representation(self, obj):
        return {"text": obj.text} if obj else None