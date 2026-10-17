from django.urls import path

from .views import WeatherCurrentView

urlpatterns = [
    path("weather/current/", WeatherCurrentView.as_view(), name="weather-current"),
]
