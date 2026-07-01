from django.contrib import admin
from django.urls    import path, include

urlpatterns = [

    # Interface d'administration Django
    path('admin/', admin.site.urls),

    # Authentification, parents, enfants
    # Préfixe : /auth/
    path('auth/', include('Uauth.urls')),

    # Espace enseignant : élèves, leçons, exercices, calendrier
    # Préfixe : /enseignant/
    path('enseignant/', include('enseignant.urls')),

    # Quiz, scores, statistiques des enfants
    # Préfixe : /quiz/
    path('quiz/', include('mlt_quiz.urls')),
    
    # Application de communication
    path('communication/', include('communication.urls')),

    # Synthèse vocale (Piper TTS)
    path('tts/', include('tts.urls')),
]

