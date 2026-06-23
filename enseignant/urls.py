from django.urls import path
from . import views

urlpatterns = [

   
    # ÉLÈVES
    # Recherche d'un élève par nom/prénom (filtrée par classe)
   
    path(
        'rechercher-eleve/',
        views.RechercheEleveView.as_view(),
        name='rechercher-eleve'
    ),

    # Liste des élèves + ajout d'un élève à la classe
    path(
        'eleves/',
        views.EnseignantElevesView.as_view(),
        name='enseignant-eleves'
    ),

    # Infos détaillées d'un élève spécifique
    
    path(
        'eleves/<int:eleve_id>/',
        views.EleveDetailView.as_view(),
        name='enseignant-eleve-detail'
    ),

    # Scores d'un élève spécifique
   
    path(
        'eleves/<int:eleve_id>/scores/',
        views.EleveScoresView.as_view(),
        name='enseignant-eleve-scores'
    ),

    # Retirer un élève de la classe
    
    path(
        'eleves/<int:eleve_id>/supprimer/',
        views.SupprimerEleveView.as_view(),
        name='supprimer-eleve'
    ),


    # STATISTIQUES
    # Statistiques du tableau de bord enseignant
    
    path(
        'stats/',
        views.EnseignantStatsView.as_view(),
        name='stats-enseignant'
    ),

    # LEÇONS
    

    # Liste des leçons + création d'une nouvelle leçon
    
    path(
        'lecons/',
        views.LeconView.as_view(),
        name='enseignant-lecons'
    ),

    # Détail, modification et suppression d'une leçon
    
    path(
        'lecons/<int:lecon_id>/',
        views.LeconDetailView.as_view(),
        name='enseignant-lecon-detail'
    ),

    # Exercices d'une leçon + ajout d'un exercice
    
    path(
        'lecons/<int:lecon_id>/exercices/',
        views.ExerciceView.as_view(),
        name='enseignant-exercices'
    ),

    # Suppression d'un exercice spécifique
    
    path(
        'exercices/<int:exercice_id>/',
        views.ExerciceDeleteView.as_view(),
        name='enseignant-exercice-delete'
    ),


    # CALENDRIER
    # Liste des événements + création d'un événement
    path(
        'calendrier/',
        views.CalendrierView.as_view(),
        name='enseignant-calendrier'
    ),

    # Suppression d'un événement spécifique
    path(
        'calendrier/<int:evenement_id>/',
        views.CalendrierDeleteView.as_view(),
        name='enseignant-calendrier-delete'
    ),

    # ESPACE ENFANT — Accès aux leçons et exercices
    # Liste des leçons publiées pour l'enfant connecté
    path(
        'enfant/lecons/',
        views.EnfantLeconsView.as_view(),
        name='enfant-lecons'
    ),

    # Détail d'une leçon publiée pour l'enfant
    path(
        'enfant/lecons/<int:lecon_id>/',
        views.EnfantLeconDetailView.as_view(),
        name='enfant-lecon-detail'
    ),

    # Exercices d'une leçon publiée pour l'enfant
    path(
        'enfant/lecons/<int:lecon_id>/exercices/',
        views.EnfantExercicesView.as_view(),
        name='enfant-exercices'
    ),
]
