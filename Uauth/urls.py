from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [

    # AUTHENTIFICATION
    # Inscription d'un parent ou d'un enseignant
    path(
        'inscription/',
        views.InscriptionView.as_view(),
        name='inscription'
    ),

    # Connexion unique pour tous les utilisateurs
    # Retourne un token JWT avec le rôle
    path(
        'Login/',
        views.LoginTokenView.as_view(),
        name='loginToken'
    ),

    # Rafraîchissement du token JWT expiré
    path(
        'token/refresh/',
        TokenRefreshView.as_view(),
        name='refreshToken'
    ),

    # Profil de l'utilisateur connecté
    # Retourne les infos communes + infos spécifiques au rôle
    path(
        'user-profile/',
        views.UserProfileView.as_view(),
        name='user-profile'
    ),

    # ESPACE PARENT
    # Inscription d'un enfant par le parent connecté
    path(
        'ajouterEnfant/',
        views.InscriptionEnfantParParentView.as_view(),
        name='ajouterEnfant'
    ),

    # NOUVELLE ROUTE : Pour supprimer un enfant spécifique (DELETE)
    # On ajoute <int:pk>/ pour que la vue reçoive l'ID de l'enfant
    path(
        'ajouterEnfant/<int:pk>/',
        views.InscriptionEnfantParParentView.as_view(),
        name='modifier-supprimer-enfant'
    ),



]
