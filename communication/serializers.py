from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Message, Notification

User = get_user_model()

# 1. Serializer pour les contacts (Infos minimales pour la liste)
class ContactSerializer(serializers.ModelSerializer):
    nom_complet = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'nom_complet', 'role']

    def get_nom_complet(self, obj):
        return f"{obj.first_name} {obj.last_name}"

# 2. Serializer pour les Messages
class MessageSerializer(serializers.ModelSerializer):
    expediteur_nom = serializers.ReadOnlyField(source='expediteur.username')
    
    class Meta:
        model = Message
        fields = ['id', 'expediteur', 'expediteur_nom', 'receveur', 'contenu', 'date_envoi', 'est_lu']
        read_only_fields = ['expediteur', 'date_envoi']

# 3. Serializer pour les Notifications
class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'type_notif', 'titre', 'message', 'date_creation', 'est_lu', 'lecon_liee']
        read_only_fields = ['type_notif', 'titre', 'message', 'date_creation', 'lecon_liee']
        