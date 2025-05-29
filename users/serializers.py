import random
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from rest_framework import serializers
from .models import CustomUser

class UserSignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'password', 'sizeOfCompany', 'opt_terms'] 

    def create(self, validated_data):
        return CustomUser.objects.create_user(**validated_data)


class VerifyEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)

    def validate(self, data):
        try:
            user = CustomUser.objects.get(email=data['email'])
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError("User not found.")

        if user.email_verified:
            raise serializers.ValidationError("Email already verified.")

        if user.email_verification_code != data['code']:
            raise serializers.ValidationError("Invalid verification code.")
        # Check expiration
        if user.email_code_created_at and timezone.now() > user.email_code_created_at + timedelta(hours=24):
            raise serializers.ValidationError("Verification code has expired. Please request a new one.")

        return data

    def save(self):
        user = CustomUser.objects.get(email=self.validated_data['email'])
        user.email_verified = True
        user.email_verification_code = None  # Clear it
        user.save()
        return user
    

class ResendVerificationCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            self.user = CustomUser.objects.get(email=value)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError("User not found.")

        if self.user.email_verified:
            raise serializers.ValidationError("Email already verified.")

        return value

    def save(self):
        # from django.utils import timezone
        # import random

        code = str(random.randint(100000, 999999))
        self.user.email_verification_code = code
        self.user.email_code_created_at = timezone.now()
        self.user.save()

        send_mail(
            subject="Resend: Your Email Verification Code",
            message=f"Your new verification code is: {code}",
            from_email=None,
            recipient_list=[self.user.email],
        )
        print(f"New verification code sent to {self.user.email}: {code}")


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            self.user = CustomUser.objects.get(email=value)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError("No user with this email.")
        return value

    def save(self):
        # from django.utils import timezone
        # import random

        code = str(random.randint(100000, 999999))
        user = self.user
        user.email_verification_code = code
        user.email_code_created_at = timezone.now()
        user.save()

        # send_mail(
        #     subject="Password Reset Code",
        #     message=f"Your password reset code is: {code}",
        #     from_email=None,
        #     recipient_list=[user.email],
        # )
        print(f"Password reset code sent to {user.email}: {code}")



class PasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True)

    def validate(self, data):
        try:
            user = CustomUser.objects.get(email=data['email'])
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError("User not found.")

        if user.email_verification_code != data['code']:
            raise serializers.ValidationError("Invalid reset code.")

        if user.email_code_created_at and timezone.now() > user.email_code_created_at + timedelta(hours=24):
            raise serializers.ValidationError("Reset code has expired.")

        self.user = user
        return data

    def save(self):
        self.user.set_password(self.validated_data['new_password'])
        self.user.email_verification_code = None
        self.user.save()

class UserDetailSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    is_lofty_connected = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        exclude = ['email_verification_code', 'email_code_created_at']

    def get_is_lofty_connected(self, obj):
        return bool(obj.lofty_access_token and obj.lofty_user_id)
    
    def create(self, validated_data):
        password = validated_data.pop('password', None)

        user = CustomUser.objects.create_user(
            **validated_data,
            password=password,
            is_admin_created=True  #  Important for skipping opt_terms checks
        )
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()
        return instance

# class UserDetailSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = CustomUser
#         exclude = ['password', 'email_verification_code', 'email_code_created_at']

class PublicUserDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'sizeOfCompany']  #, 'chatBot_key'
