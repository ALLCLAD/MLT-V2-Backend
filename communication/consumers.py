import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Message

User = get_user_model()

# --- CONSUMER POUR LE CHAT ---
class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.mon_id = self.scope['user'].id
        self.contact_id = self.scope['url_route']['kwargs']['contact_id']
        
        # On crée un nom de salle unique pour ces deux personnes
        # Ex: chat_3_5 (toujours dans le même ordre)
        ids = sorted([int(self.mon_id), int(self.contact_id)])
        self.room_group_name = f'chat_{ids[0]}_{ids[1]}'

        # On rejoint la salle
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    # Réception d'un message depuis le navigateur
    async def receive(self, text_data):
        data = json.loads(text_data)
        message_texte = data['message']

        # Enregistrement en base de données (Asynchrone)
        await self.save_message(self.mon_id, self.contact_id, message_texte)

        # Envoi du message à toute la salle (aux deux personnes)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message_texte,
                'expediteur_id': self.mon_id
            }
        )

    # Envoi vers le WebSocket du client
    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'expediteur_id': event['expediteur_id']
        }))

    @database_sync_to_async
    def save_message(self, exp_id, rec_id, text):
        return Message.objects.create(expediteur_id=exp_id, receveur_id=rec_id, contenu=text)


# --- CONSUMER POUR LES NOTIFICATIONS ---
class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = self.scope['user'].id
        self.room_group_name = f'notify_{self.user_id}'

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    # Méthode appelée par les Signaux pour envoyer l'alerte
    async def send_notification(self, event):
        await self.send(text_data=json.dumps(event['data']))
