from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
import uuid
import secrets

ROLE_CHOICES = (
    ('admin', 'Admin'),
    ('user', 'User'),
)

STATUS_CHOICES = (
    ('active', 'Active'),
    ('inactive', 'Inactive'),
)

SIZE_CHOICES = (
    ('xs', 'XS'),
    ('s', 'S'),
    ('m', 'M'),
    ('l', 'L'),
)

class CustomUserManager(BaseUserManager):
    def create_user(self, email, first_name, last_name, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)

        # Social logins won't send these
        is_social = extra_fields.pop("is_social", False)
        is_admin_created = extra_fields.pop("is_admin_created", False)

        size = extra_fields.pop("sizeOfCompany", None)
        terms = extra_fields.pop("opt_terms", False)

        if not is_social and not is_admin_created:
            if size not in dict(SIZE_CHOICES).keys():
                raise ValueError("Invalid size of company")
            if terms not in [True, False]:
                raise ValueError("Invalid terms of service")

        user = self.model(
            email=email,
            first_name=first_name,
            last_name=last_name,
            sizeOfCompany=size if not is_social else None,
            opt_terms=terms if not is_social else False,
            **extra_fields
        )
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)
        return user

    # def create_user(self, email, first_name, last_name, password=None, **extra_fields):
    #     if not email:
    #         raise ValueError("Email is required")
    #     email = self.normalize_email(email)
    #     # Extract optional fields with defaults
    #     size = extra_fields.get("sizeOfCompany")
    #     terms = extra_fields.get("opt_terms", False)
    #     if size not in dict(SIZE_CHOICES).keys():
    #         raise ValueError("Invalid size of company")
    #     if terms not in [True, False]:
    #         raise ValueError("Invalid terms of service")

    #     print("Creating user with email:", email)
    #     user = self.model(
    #         email=email,
    #         first_name=first_name,
    #         last_name=last_name,
    #         sizeOfCompany=size,
    #         opt_terms=terms,
    #         email_verified = False,
    #         **extra_fields
    #     )
    #     user.set_password(password)
    #     user.save(using=self._db)

    #     return user

    def create_superuser(self, email, first_name, last_name, password=None, **extra_fields):
        extra_fields.setdefault('role', 'admin')
        extra_fields.setdefault('status', 'active')
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        print("Creating superuser with email:", email)

        return self.create_user(email, first_name, last_name, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False)

    # Common Fields
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    picture = models.URLField(blank=True, null=True)
    email_verified = models.BooleanField(default=False)
    email_verification_code = models.CharField(max_length=6, blank=True, null=True)
    email_code_created_at = models.DateTimeField(blank=True, null=True)


    # Role & Status
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')

    # API Access
    api_key = models.CharField(max_length=100, unique=True, null=True)

    # Chatbot Key: role-specific
    chatBot_key = models.TextField(blank=True, null=True)  # For users only
    chatBot_user_id = models.TextField(blank=True, null=True)  # For users only
    #admin_chatBot_key = models.TextField(blank=True, null=True)  # For admins only

    # User-specific
    sizeOfCompany = models.CharField(max_length=2, choices=SIZE_CHOICES, blank=True, null=True)
    opt_terms = models.BooleanField(default=False)

    # Django admin related
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)


    # Lofty Related Fields
    lofty_user_id = models.CharField(max_length=255, blank=True, null=True)
    lofty_access_token = models.CharField(max_length=255, blank=True, null=True)
    lofty_refresh_token = models.CharField(max_length=255, blank=True, null=True)
    lofty_token_expires_at = models.DateTimeField(blank=True, null=True)

    

    # Manager & Auth
    objects = CustomUserManager()
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    def save(self, *args, **kwargs):
        if not self.api_key:
            self.api_key = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)
    def __str__(self):
        return self.email
