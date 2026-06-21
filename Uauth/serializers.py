import re  # Pour les expressions régulières de validation
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import Utilisateur, SuiviParentEnfant, Enfant



# FONCTIONS DE VALIDATION COMMUNES
# Réutilisées dans les deux serializers d'inscription (adulte + enfant)


def valider_email_gmail(email):
    """
    Vérifie que l'email respecte le format attendu :
      - prenomnom@gmail.com
      - nomprenoms@gmail.com
    Lettres et chiffres COLLÉS, sans point ni espace avant @gmail.com.
    Tout autre domaine ou format sera rejeté avec un message précis.
    """
    # Regex : une suite de lettres/chiffres sans séparateur + @gmail.com
    pattern = r'^[a-zA-ZÀ-ÿ0-9]+@gmail\.com$'

    if not re.match(pattern, email):
        # On donne un message précis selon le problème détecté
        if '@' not in email:
            raise serializers.ValidationError(
                "Email invalide : le symbole '@' est manquant."
            )
        if not email.endswith('@gmail.com'):
            raise serializers.ValidationError(
                "Email invalide : seules les adresses @gmail.com sont acceptées."
            )
        raise serializers.ValidationError(
            "Email invalide : le format attendu est prenomnom@gmail.com "
            "(sans point ni espace avant le @)."
        )


def valider_complexite_mot_de_passe(password):
    """
    Vérifie que le mot de passe respecte les règles de complexité :
      - Au moins 8 caractères
      - Au moins une lettre majuscule
      - Au moins une lettre minuscule
      - Au moins un chiffre
      - Au moins un caractère spécial (@, #, !, ?, etc.)
    Ne vérifie PAS si c'est un "vrai" bon mot de passe,
    juste que le format est respecté.
    """
    if len(password) < 8:
        raise serializers.ValidationError(
            "Le mot de passe doit contenir au moins 8 caractères."
        )
    if not re.search(r'[A-Z]', password):
        raise serializers.ValidationError(
            "Le mot de passe doit contenir au moins une lettre majuscule (ex: A, B...)."
        )
    if not re.search(r'[a-z]', password):
        raise serializers.ValidationError(
            "Le mot de passe doit contenir au moins une lettre minuscule (ex: a, b...)."
        )
    if not re.search(r'[0-9]', password):
        raise serializers.ValidationError(
            "Le mot de passe doit contenir au moins un chiffre (ex: 1, 2...)."
        )
    if not re.search(r'[@#$%^&*!?.,;:\-_+=]', password):
        raise serializers.ValidationError(
            "Le mot de passe doit contenir au moins un caractère spécial "
            "(ex: @, #, !, ?, ...)."
        )



# SERIALIZER : InscriptionAdulteSerializer


class InscriptionAdulteSerializer(serializers.ModelSerializer):
    """
    Serializer pour l'inscription d'un adulte (parent ou enseignant).
    Valide les données et crée le compte utilisateur.
    Le profil lié (Parent ou Enseignant) est créé via un signal Django.
    """

    # Champ de confirmation de mot de passe (non stocké en BDD)
    password_confirm = serializers.CharField(write_only=True)

    # Champs optionnels réservés à l'enseignant
    # Ils sont transmis au signal via des attributs temporaires
    etablissement_inscription = serializers.CharField(
        required=False,
        write_only=True,
        help_text="Établissement de l'enseignant (optionnel)"
    )
    classe_enseignement_inscription = serializers.CharField(
        required=False,
        write_only=True,
        help_text="Classe enseignée (CP1 à CM2)"
    )

    class Meta:
        model = Utilisateur
        fields = [
            'username',
            'email',
            'first_name',
            'last_name',
            'password',
            'password_confirm',
            'role',
            'etablissement_inscription',
            'classe_enseignement_inscription',
        ]

    def validate_email(self, value):
        """
        Validation du champ email (appelée automatiquement par DRF).
        Vérifie le format prenomnom@gmail.com avec la fonction commune.
        """
        valider_email_gmail(value)
        return value

    def validate_password(self, value):
        """
        Validation du champ password (appelée automatiquement par DRF).
        Vérifie la complexité avec la fonction commune.
        """
        valider_complexite_mot_de_passe(value)
        return value

    def validate(self, data):
        """
        Validation croisée : vérifie que le mot de passe
        et sa confirmation sont identiques.
        Appelée après validate_email et validate_password.
        """
        if data.get('password') != data.get('password_confirm'):
            raise serializers.ValidationError(
                "Les mots de passe ne correspondent pas."
            )
        return data

    def create(self, validated_data):
        """
        Crée le compte utilisateur.
        Les infos spécifiques à l'enseignant sont étiquetées sur l'objet
        user pour être interceptées par le signal post_save.
        """
        # On retire les champs non présents dans le modèle Utilisateur
        validated_data.pop('password_confirm')
        password            = validated_data.pop('password')
        etablissement       = validated_data.pop('etablissement_inscription', None)
        classe_enseignement = validated_data.pop('classe_enseignement_inscription', None)

        # Création de l'utilisateur (sans encore hacher le mot de passe)
        user = Utilisateur(**validated_data)
        user.set_password(password)  # Hachage sécurisé du mot de passe

        # On étiquette les attributs enseignant pour le signal post_save
        if etablissement:
            user.etablissement_inscription = etablissement
        if classe_enseignement:
            user.classe_enseignement_inscription = classe_enseignement

        user.save()
        return user



# SERIALIZER : InscriptionEnfantParParentSerializer


class InscriptionEnfantParParentSerializer(serializers.ModelSerializer):
    """
    Serializer pour l'inscription d'un enfant par son parent.
    Force le rôle à ENFANT et crée automatiquement
    le lien de parenté via SuiviParentEnfant.
    """

    # Classe de l'enfant (CP1 à CM2) — non stockée dans Utilisateur
    classe_inscription = serializers.CharField(write_only=True)

    # Confirmation du mot de passe (non stockée en BDD)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = Utilisateur
        fields = [
            'username',
            'email',
            'first_name',
            'last_name',
            'password',
            'password_confirm',
            'classe_inscription',
        ]
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def validate_email(self, value):
        """
        Validation de l'email de l'enfant.
        Même règle que pour l'adulte : doit être prenomnom@gmail.com.
        """
        valider_email_gmail(value)
        return value

    def validate_password(self, value):
        """
        Validation du mot de passe de l'enfant.
        Même règle de complexité que pour l'adulte.
        """
        valider_complexite_mot_de_passe(value)
        return value

    def validate(self, data):
        """
        Vérifie que le mot de passe et sa confirmation sont identiques.
        """
        if data.get('password') != data.get('password_confirm'):
            raise serializers.ValidationError(
                "Les mots de passe ne correspondent pas."
            )
        return data

    def create(self, validated_data):
        """
        Crée le compte enfant, son profil Enfant via signal,
        et crée le lien SuiviParentEnfant avec le parent connecté.
        """
        # On retire les champs non présents dans le modèle Utilisateur
        validated_data.pop('password_confirm')
        classe   = validated_data.pop('classe_inscription')
        password = validated_data.pop('password')

        # On force le rôle à ENFANT peu importe ce qui est envoyé
        user = Utilisateur(
            **validated_data,
            role=Utilisateur.Role.ENFANT
        )
        user.set_password(password)  # Hachage sécurisé du mot de passe

        # On étiquette la classe pour le signal post_save
        user.classe_inscription = classe
        user.save()

        # Liaison automatique avec le parent connecté
        request = self.context.get('request')
        if request and request.user.role == Utilisateur.Role.PARENT:
            SuiviParentEnfant.objects.create(
                parent=request.user.profil_parent,
                enfant=user.profil_enfant
            )

        return user



# SERIALIZER : EnfantSerializer


class EnfantSerializer(serializers.ModelSerializer):
    """
    Serializer pour lister les enfants d'un parent.
    Récupère les infos depuis le modèle Utilisateur lié.
    """

    # Infos issues du modèle Utilisateur lié au profil Enfant
    nom      = serializers.CharField(source='utilisateur.last_name',  read_only=True)
    prenom   = serializers.CharField(source='utilisateur.first_name', read_only=True)
    username = serializers.CharField(source='utilisateur.username',   read_only=True)

    class Meta:
        model  = Enfant
        fields = ['id', 'username', 'nom', 'prenom', 'classe']



# SERIALIZER : TokenSerializer


class TokenSerializer(TokenObtainPairSerializer):
    """
    Serializer JWT personnalisé.
    Ajoute des données supplémentaires dans le token
    ET dans la réponse de login pour le frontend.
    """

    @classmethod
    def get_token(cls, user):
        """
        Encode des données supplémentaires dans le token JWT.
        Ces données sont lisibles côté frontend via jwtDecode().
        """
        token = super().get_token(user)
        token['role']     = user.role
        token['username'] = user.username
        return token

    def validate(self, attrs):
        """
        Ajoute des données supplémentaires dans la réponse HTTP du login.
        Permet au frontend d'accéder directement au rôle et au nom.
        """
        data = super().validate(attrs)
        data['role']      = self.user.role
        data['username']  = self.user.username
        data['full_name'] = f"{self.user.first_name} {self.user.last_name}"
        return data
