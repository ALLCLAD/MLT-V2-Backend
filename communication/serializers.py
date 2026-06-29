from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Message, Notification

User = get_user_model()

# --- 1. User Minimal Serializer ---
class UserMinimalSerializer(serializers.ModelSerializer):
    nom_complet = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'nom_complet', 'role']

    def get_nom_complet(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username


# --- 2. Message Serializer (AJOUT DU CHAMP est_modifie) ---
class MessageSerializer(serializers.ModelSerializer):
    expediteur_nom = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            'id', 'expediteur', 'expediteur_nom', 'receveur',
            'classe_enseignant', 'groupe_parent', 'contenu', 'date_envoi', 'est_lu',
            'est_modifie'  # <- AJOUT INDISPENSABLE ICI
        ]
        read_only_fields = ['expediteur', 'date_envoi', 'est_modifie'] # 'est_modifie' est géré par la vue au moment du PATCH

    def get_expediteur_nom(self, obj):
        return f"{obj.expediteur.first_name} {obj.expediteur.last_name}".strip() or obj.expediteur.username


# --- 3. Notification Serializer ---
class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'type_notif', 'titre', 'message', 'date_creation', 'est_lu', 'lecon_liee']
        read_only_fields = ['type_notif', 'titre', 'message', 'date_creation', 'lecon_liee']