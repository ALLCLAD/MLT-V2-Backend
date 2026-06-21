
from django.contrib import admin
from .models import (Utilisateur,Enfant,Parent,Enseignant,SuiviParentEnfant,SuiviEnseignantEnfant,
)

# ADMIN : Utilisateur
@admin.register(Utilisateur)
class UtilisateurAdmin(admin.ModelAdmin):
    """
    Configuration de l'affichage des utilisateurs dans l'admin.
    Permet de filtrer par rôle et de rechercher par nom ou email.
    """
    list_display   = ('username', 'email', 'role', 'is_staff')
    list_filter    = ('role', 'is_staff')
    search_fields  = ('username', 'email')
    ordering       = ('-date_joined',)

# ADMIN : Enfant

@admin.register(Enfant)
class EnfantAdmin(admin.ModelAdmin):
    """
    Configuration de l'affichage des profils enfants dans l'admin.
    """
    list_display  = ('utilisateur', 'classe')
    list_filter   = ('classe',)
    search_fields = ('utilisateur__username', 'utilisateur__first_name', 'utilisateur__last_name')

# ADMIN : Parent

@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    """
    Configuration de l'affichage des profils parents dans l'admin.
    """
    list_display  = ('utilisateur',)
    search_fields = ('utilisateur__username', 'utilisateur__email')

# ADMIN : Enseignant

@admin.register(Enseignant)
class EnseignantAdmin(admin.ModelAdmin):
    """
    Configuration de l'affichage des profils enseignants dans l'admin.
    """
    list_display  = ('utilisateur', 'etablissement', 'classe_enseignement')
    list_filter   = ('classe_enseignement',)
    search_fields = ('utilisateur__username', 'etablissement')

# ADMIN : SuiviParentEnfant

@admin.register(SuiviParentEnfant)
class SuiviParentEnfantAdmin(admin.ModelAdmin):
    """
    Affichage du lien de parenté parent-enfant dans l'admin.
    """
    list_display = ('parent', 'enfant', 'date_inscription')
    list_filter  = ('date_inscription',)

# ADMIN : SuiviEnseignantEnfant

@admin.register(SuiviEnseignantEnfant)
class SuiviEnseignantEnfantAdmin(admin.ModelAdmin):
    """
    Affichage du lien enseignant-élève dans l'admin.
    """
    list_display = ('enseignant', 'enfant', 'date_ajout')
    list_filter  = ('date_ajout',)
