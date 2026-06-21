from rest_framework import serializers
from Uauth.models import Enfant
from .models import Lecon, Exercice, EvenementCalendrier



# SERIALIZER : RechercheEleveSerializer

class RechercheEleveSerializer(serializers.ModelSerializer):
    """
    Serializer pour afficher les infos d'un élève
    lors de la recherche par l'enseignant.
    Récupère les données depuis le modèle Utilisateur lié.
    """

    nom      = serializers.CharField(source='utilisateur.last_name',  read_only=True)
    prenom   = serializers.CharField(source='utilisateur.first_name', read_only=True)
    username = serializers.CharField(source='utilisateur.username',   read_only=True)

    class Meta:
        model  = Enfant
        fields = ['id', 'username', 'nom', 'prenom', 'classe']



# SERIALIZER : EleveEnseignantSerializer

class EleveEnseignantSerializer(serializers.ModelSerializer):
    """
    Serializer pour lister les élèves inscrits dans
    la classe de l'enseignant connecté.
    """

    nom      = serializers.CharField(source='utilisateur.last_name',  read_only=True)
    prenom   = serializers.CharField(source='utilisateur.first_name', read_only=True)
    username = serializers.CharField(source='utilisateur.username',   read_only=True)

    class Meta:
        model  = Enfant
        fields = ['id', 'username', 'nom', 'prenom', 'classe']



# SERIALIZER : ExerciceSerializer

class ExerciceSerializer(serializers.ModelSerializer):
    """
    Serializer complet pour un exercice QCM.
    Contient la question, la bonne réponse, les mauvaises réponses
    et l'explication affichée après la réponse de l'élève.
    """

    class Meta:
        model  = Exercice
        fields = [
            'id',
            'question',           # La question posée à l'élève
            'reponse_correcte',   # La bonne réponse (visible enseignant + validation côté enfant)
            'mauvaises_reponses', # Mauvaises réponses séparées par des virgules
            'explication',        # Explication affichée après la réponse
            'ordre',              # Ordre d'affichage dans la leçon
        ]



# SERIALIZER : LeconCreateSerializer

class LeconCreateSerializer(serializers.ModelSerializer):
    """
    Serializer pour créer une nouvelle leçon.
    L'enseignant fournit le titre, la description et le thème.
    Le contenu est généré côté frontend par l'IA Groq,
    puis envoyé ici pour être sauvegardé.
    """

    class Meta:
        model  = Lecon
        fields = [
            'titre',       # Titre saisi par l'enseignant
            'description', # Description courte pour guider l'IA
            'classe',      # Classe cible (synchronisée avec profil enseignant)
            'duree',       # Durée estimée (ex: "45 min")
            'contenu',     # Contenu généré par l'IA côté frontend
            'theme',       # Thème mathématique (CALCUL, GEOMETRIE, etc.)
        ]



# SERIALIZER : LeconListSerializer

class LeconListSerializer(serializers.ModelSerializer):
    """
    Serializer pour la liste des leçons.
    Affiche les infos essentielles + le nombre d'exercices.
    Utilisé aussi pour changer le statut (brouillon ↔ publié).
    """

    # Propriété calculée depuis le modèle Lecon
    nombre_exercices = serializers.IntegerField(read_only=True)

    class Meta:
        model  = Lecon
        fields = [
            'id',
            'titre',
            'description',
            'classe',
            'duree',
            'statut',            # brouillon ou publie
            'theme',
            'nombre_exercices',  # Nombre d'exercices liés
            'date_creation',
        ]



# SERIALIZER : LeconDetailSerializer

class LeconDetailSerializer(serializers.ModelSerializer):
    """
    Serializer détaillé pour une leçon.
    Inclut le contenu complet + la liste des exercices imbriqués.
    """

    # Exercices imbriqués directement dans la leçon
    exercices        = ExerciceSerializer(many=True, read_only=True)

    # Propriété calculée depuis le modèle Lecon
    nombre_exercices = serializers.IntegerField(read_only=True)

    class Meta:
        model  = Lecon
        fields = [
            'id',
            'titre',
            'description',
            'contenu',           # Contenu généré par l'IA
            'classe',
            'duree',
            'statut',
            'theme',
            'nombre_exercices',
            'exercices',         # Liste des exercices imbriqués
            'date_creation',
            'date_modification',
        ]



# SERIALIZER : EvenementCalendrierSerializer

class EvenementCalendrierSerializer(serializers.ModelSerializer):
    """
    Serializer pour les événements du calendrier enseignant.
    Permet de créer, lister et supprimer des événements
    liés à des leçons ou à d'autres activités.
    """

    class Meta:
        model  = EvenementCalendrier
        fields = [
            'id',
            'titre',           # Titre de l'événement
            'type_evenement',  # cours, reunion ou autre
            'date',            # Date 
            'heure',           # Heure 
            'lecon',           # Leçon liée 
        ]
        # L'enseignant est assigné automatiquement dans la vue
       
