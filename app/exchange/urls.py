from django.urls import path
from .views import ExchangeRatesView

app_name = 'exchange'

urlpatterns = [
    path('rates/', ExchangeRatesView.as_view(), name='rates'),
]
