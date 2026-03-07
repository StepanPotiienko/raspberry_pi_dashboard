from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.dashboard, name="main"),
    path("api/stats/", views.api_system_stats, name="api_stats"),
    path("api/processes/", views.api_processes, name="api_processes"),
    path("api/historical/", views.api_historical_data, name="api_historical"),
]
