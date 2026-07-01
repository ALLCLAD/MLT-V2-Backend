from django.urls import path
from . import views

urlpatterns = [
    path('synthesize/', views.synthesize_speech, name='tts-synthesize'),
]
