from django.urls import path
from . import views

app_name = 'mfa'

urlpatterns = [
    path('generate/', views.generate_otp_view, name='generate_otp'),
    path('verify/', views.verify_otp, name='verify_otp'),
    path('api/generate/', views.generate_otp_view, name='generate_otp_api'),
    path('api/verify-tauser-transaction/', views.verify_tauser_transaction_otp, name='api_verify_tauser_otp'),
]
