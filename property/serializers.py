"property/serializers.py"
from rest_framework import serializers
from property.models import Property, LoftyProperty
from shared.serializers import WritableKeywordField
from shared.models import Keyword

class PropertySerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    keyword = WritableKeywordField()

    email_recipients = serializers.ListField(child=serializers.EmailField(), required=False)

    class Meta:
        model = Property
        fields = [
            'id', 'user', 'keyword', 'url', 'address', 'city', 'state', 'zip_code', 'price',
            'home_type', 'beds', 'baths', 'sqft', 'lot_size', 'description', 'ai_generated_description',
            'button1_text', 'button1_url', 'button2_text', 'button2_url',
            'image_url', 'email_recipients', 'created_at', 'status'
        ]
        read_only_fields = ['id', 'created_at']

    def create(self, validated_data):
        keyword_obj = validated_data.pop('keyword')
        if hasattr(keyword_obj, 'instabot') or hasattr(keyword_obj, 'property'):
            raise serializers.ValidationError("This keyword is already associated with another object.")
        validated_data['keyword'] = keyword_obj
        return Property.objects.create(**validated_data)

    def update(self, instance, validated_data):
        keyword_obj = validated_data.pop('keyword', None)
        if keyword_obj:
            # Allow reuse only if it's linked to this instance
            if hasattr(keyword_obj, 'instabot') or (hasattr(keyword_obj, 'property') and keyword_obj.property.id != instance.id):
                raise serializers.ValidationError("This keyword is already associated with another object.")
            instance.keyword = keyword_obj

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance



class LoftyPropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = LoftyProperty
        fields = ['id', 'listing_id', 'address', 'city', 'state', 'zip_code',
                  'price', 'beds', 'baths', 'sqft', 'description', 'image_url',
                  'fetched_at', 'is_selected']
        read_only_fields = ['id', 'fetched_at', 'is_selected']

    