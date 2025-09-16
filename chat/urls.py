# chat/urls.py
from django.urls import path
from .views import chat_view, reset_view, set_provider_view

urlpatterns = [
    path("", chat_view, name="chat"),
    path("reset/", reset_view, name="reset"),
     path("provider/", set_provider_view, name="set_provider"),
]
