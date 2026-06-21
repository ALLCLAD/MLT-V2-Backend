from django.contrib import admin
from .models import Lecon, Exercice, EvenementCalendrier



# Affiche le titre, l'enseignant, la classe, le statut et la date
# Filtre par statut, classe et thème
# Recherche par titre et description

@admin.register(Lecon)
class LeconAdmin(admin.ModelAdmin):
    """
    Configuration de l'affichage des leçons dans l'admin.
    Permet de filtrer par statut/classe et de rechercher par titre.
    """
    list_display   = ('titre', 'enseignant', 'classe', 'theme', 'statut', 'date_creation')
    list_filter    = ('statut', 'classe', 'theme')
    search_fields  = ('titre', 'description')
    ordering       = ('-date_creation',)
    readonly_fields = ('date_creation', 'date_modification')



# Affiche la leçon, la question, la bonne réponse et l'ordre
# Filtre par leçon
# Recherche par question
@admin.register(Exercice)
class ExerciceAdmin(admin.ModelAdmin):
    """
    Configuration de l'affichage des exercices dans l'admin.
    Permet de filtrer par leçon et de rechercher par question.
    """
    list_display  = ('lecon', 'question', 'reponse_correcte', 'ordre')
    list_filter   = ('lecon',)
    search_fields = ('question',)
    ordering      = ('lecon', 'ordre')



# Affiche le titre, la date, l'heure, le type et l'enseignant
# Filtre par type d'événement, date et enseignant
# Recherche par titre

@admin.register(EvenementCalendrier)
class EvenementCalendrierAdmin(admin.ModelAdmin):
    """
    Configuration de l'affichage des événements du calendrier.
    Permet de filtrer par type et par enseignant.
    """
    list_display  = ('titre', 'date', 'heure', 'type_evenement', 'enseignant')
    list_filter   = ('type_evenement', 'date', 'enseignant')
    search_fields = ('titre',)
    ordering      = ('date', 'heure')
