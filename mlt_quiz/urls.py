from django.urls import path

# importation des vues
from . import views

urlpatterns = [

    # --- PARTIE PARENT (STATISTIQUES) ---

    # Chemin vers notre vue renvoyant les statistiques globales (total enfants, moyenne générale) pour le dashboard parent
    path('stats-global/', views.ParentGlobalStatsView.as_view(), name='stats-global'),

    # Chemin renvoyant les statistiques détaillées (par thème, temps moyen) pour un enfant spécifique
    path('stats-par-enfant/<int:enfant_id>/', views.EnfantDetailStatsView.as_view(), name='stats-enfant'),

    # --- PARTIE ENFANT (EXERCICES) ---

    # Chemin vers notre vue permettant d'enregistrer le score, le temps et les stats de l'enfant après un quiz
    path('save-score/', views.SaveScoreView.as_view(), name='savescore'),

    path('enfant-dashboard/', views.EnfantDashboardView.as_view(), name='enfant_dashboard'),

    # Chemin vers notre vue permettant de récupérer une liste de questions aléatoires selon le thème et le niveau de l'enfant
    path('<str:theme>/', views.GetQuizView.as_view(), name='quiz'),

]