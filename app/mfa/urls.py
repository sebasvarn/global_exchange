from django.urls import path
from . import views

app_name = 'mfa'

urlpatterns = [
    path('generate/', views.generate_otp_view, name='generate_otp'),
    path('verify/', views.verify_otp_view, name='verify'),
]
