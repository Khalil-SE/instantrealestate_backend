from rest_framework.routers import DefaultRouter
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import UserSignupView, VerifyEmailView, ResendVerificationCodeView, CustomTokenObtainPairView, PasswordResetRequestView, PasswordResetConfirmView, MeView, MeUpdateView, UserAdminViewSet, UserDataByKeyView, UploadUserPictureView, GoogleLoginView, FacebookLoginView, LogoutView
from users.views import CheckEmailExistsView



router = DefaultRouter()


urlpatterns = [
    path("check-email/", CheckEmailExistsView.as_view(), name="check-email"),

    path('signup/', UserSignupView.as_view(), name='user-signup'),
    path('verify-email/', VerifyEmailView.as_view(), name='verify-email'),
    path('resend-verification-code/', ResendVerificationCodeView.as_view(), name='resend-verification'),
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),

    path('social-login/google/', GoogleLoginView.as_view(), name='google-login'),
    path('social-login/facebook/', FacebookLoginView.as_view(), name='facebook-login'),

    path('request-reset-password/', PasswordResetRequestView.as_view(), name='request-reset-password'),
    path('reset-password/', PasswordResetConfirmView.as_view(), name='reset-password'),
    
    path('me/', MeView.as_view(), name='me'),
    path('me/update/', MeUpdateView.as_view(), name='me-update'),
    path('upload-picture/', UploadUserPictureView.as_view(), name='upload-picture'),

    path('data-by-key/<str:api_key>/', UserDataByKeyView.as_view(), name='data-by-key'),
]


router.register(r'admin/users', UserAdminViewSet, basename='admin-users')
urlpatterns += router.urls
