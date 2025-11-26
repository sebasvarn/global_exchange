from django.urls import path
from . import views

app_name = 'mfa'

urlpatterns = [
    path('generate/', views.generate_otp_view, name='generate_otp'),
    path('verify/', views.verify_otp, name='verify_otp'),
    path('api/generate/', views.generate_otp_view, name='generate_otp_api'),
    path('api/verify-tauser-transaction/', views.verify_tauser_transaction_otp, name='api_verify_tauser_otp'),
    path('generate/<int:transaction_id>/', views.generate_otp_for_transaction, name='generate_otp_transaction'),
    path('api/verify/', views.verify_otp_api, name='verify_otp_api'),
]
