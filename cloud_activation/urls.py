"""
URL patterns for Cloud Activation app.
"""

from django.urls import path
from . import views

app_name = 'cloud_activation'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('api/status/', views.api_status, name='api_status'),
]
