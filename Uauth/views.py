from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import (InscriptionAdulteSerializer,InscriptionEnfantParParentSerializer,EnfantSerializer,TokenSerializer,)
from enseignant.serializers import ExerciceSerializer, LeconListSerializer, LeconDetailSerializer
from enseignant.models import Lecon, Exercice
from .models import Enfant, Utilisateur, SuiviParentEnfant

# VUE : InscriptionView

class InscriptionView(APIView):
    """
    Vue publique pour l'inscription d'un parent ou d'un enseignant.
    Le profil spécifique (Parent ou Enseignant) est créé
    automatiquement via un signal Django post_save.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = InscriptionAdulteSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Compte créé avec succès !"},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# VUE : InscriptionEnfantParParentView

class InscriptionEnfantParParentView(APIView):
    """
    Vue pour qu'un parent puisse inscrire ses enfants
    directement depuis son tableau de bord.
    Le lien SuiviParentEnfant est créé automatiquement.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """
        Retourne la liste des enfants liés au parent connecté.
        Utilise la table intermédiaire SuiviParentEnfant.
        """
        if request.user.role != 'PARENT':
            return Response(
                {"error": "Action non autorisée."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Récupération des enfants via la table intermédiaire
        enfants = Enfant.objects.filter(
            suiviparentenfant__parent__utilisateur=request.user
        )
        serializer = EnfantSerializer(enfants, many=True)
        return Response(serializer.data)

    def post(self, request):
        """
        Inscrit un nouvel enfant et le lie au parent connecté.
        """
        if request.user.role != 'PARENT':
            return Response(
                {"error": "Seul un parent peut inscrire un enfant."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = InscriptionEnfantParParentSerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            serializer.save()

            # On retourne la liste mise à jour des enfants
            enfants = Enfant.objects.filter(
                suiviparentenfant__parent__utilisateur=request.user
            )
            liste = EnfantSerializer(enfants, many=True)
            return Response(
                {
                    "message": "Votre enfant est inscrit et lié à votre compte !",
                    "enfants": liste.data
                },
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk=None):
        """
        Supprime un enfant et son compte utilisateur associé.
        L'ID (pk) doit être passé dans l'URL.
        """
        if request.user.role != 'PARENT':
            return Response(
                {"error": "Action non autorisée."},
                status=status.HTTP_403_FORBIDDEN
            )

        # 1. On vérifie que l'enfant appartient bien à ce parent avant de supprimer
        # Cela évite qu'un parent puisse supprimer l'enfant d'un autre via l'API
        enfant = get_object_or_404(
            Enfant,
            id=pk,
            suiviparentenfant__parent__utilisateur=request.user
        )

        try:
            # 2. On récupère l'utilisateur lié (le compte Django)
            user_to_delete = enfant.utilisateur

            # 3. Supprimer l'utilisateur supprimera automatiquement l'Enfant
            # et le SuiviParentEnfant grâce au CASCADE dans tes modèles.
            user_to_delete.delete()

            return Response(
                {"message": "Le compte de l'enfant a été supprimé avec succès."},
                status=status.HTTP_204_NO_CONTENT
            )
        except Exception as e:
            return Response(
                {"error": f"Erreur lors de la suppression : {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

# VUE : LoginTokenView

class LoginTokenView(TokenObtainPairView):
    """
    Vue de connexion unique pour tous les utilisateurs.
    Retourne un token JWT enrichi avec le rôle et le nom.
    Le frontend redirige selon le rôle reçu.
    """
    serializer_class = TokenSerializer


# VUE : UserProfileView

class UserProfileView(APIView):
    """
    Vue pour récupérer le profil complet de l'utilisateur connecté.
    Retourne les infos communes + les infos spécifiques au rôle :
      - PARENT     : pas d'infos supplémentaires
      - ENFANT     : classe de l'enfant
      - ENSEIGNANT : établissement + classe enseignée
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        # Données communes à tous les rôles
        data = {
            "username":   user.username,
            "first_name": user.first_name,
            "last_name":  user.last_name,
            "email":      user.email,
            "role":       user.role,
        }

        # Données supplémentaires pour l'enseignant
        if user.role == 'ENSEIGNANT':
            try:
                profil = user.profil_enseignant
                data["etablissement"]      = profil.etablissement
                data["classe_enseignement"] = profil.classe_enseignement
            except Exception:
                data["etablissement"]      = None
                data["classe_enseignement"] = None

        # Données supplémentaires pour l'enfant
        elif user.role == 'ENFANT':
            try:
                profil = user.profil_enfant
                data["classe"] = profil.classe
            except Exception:
                data["classe"] = None

        return Response(data, status=status.HTTP_200_OK)


