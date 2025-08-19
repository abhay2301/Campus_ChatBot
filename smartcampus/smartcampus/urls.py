# smartcampus/smartcampus/urls.py
"""URL configuration for the SmartCampus project."""
from django.contrib import admin
from django.urls import path
from ChatBot import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.chatbot_ui, name='chat_ui'),
    path('api/chatbot/', views.chatbot_view, name='chatbot_api'),
]

