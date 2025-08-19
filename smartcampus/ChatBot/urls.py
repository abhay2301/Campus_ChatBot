# smartcampus/chatbot/urls.py
'''URL configuration for the ChatBot app.'''


from django.urls import path
from .views import chatbot_view, chatbot_ui
from ChatBot import views

urlpatterns = [
    path("", views.chatbot_ui, name="chat_ui"),           # UI frontend
    path("chatbot/", chatbot_view, name="chat_api"), # API backend
    
]
