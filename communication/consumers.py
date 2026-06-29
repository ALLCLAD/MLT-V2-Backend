import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from Uauth.models import Enseignant, Parent
from .models import Message

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]

        # Vérification de l'authentification de l'utilisateur
        if not self.user.is_authenticated:
            await self.close()
            return

        url_route = self.scope['url_route']['kwargs']

        # --- CAS 1 : SALON PRIVÉ ---
        if 'contact_id' in url_route:
            self.room_type = 'private'
            self.contact_id = int(url_route['contact_id'])
            ids = sorted([self.user.id, self.contact_id])
            self.room_group_name = f"chat_private_{ids[0]}_{ids[1]}"

        # --- CAS 2 : SALON CLASSE ---
        elif 'enseignant_id' in url_route:
            self.room_type = 'classe'
            self.enseignant_user_id = int(url_route['enseignant_id'])
            self.room_group_name = f"chat_classe_{self.enseignant_user_id}"

        # --- CAS 3 : SALON FAMILLE ---
        elif 'parent_id' in url_route:
            self.room_type = 'famille'
            self.parent_user_id = int(url_route['parent_id'])
            self.room_group_name = f"chat_famille_{self.parent_user_id}"

        else:
            await self.close()
            return

        # Rejoindre le canal de discussion ciblé
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        data = json.loads(text_data)
        contenu = data.get('message', '').strip()

        if not contenu:
            return

        # Sauvegarde asynchrone du message en Base de Données
        msg_obj = await self.save_message(contenu)

        if msg_obj:
            # Envoi du message formaté à l'ensemble du groupe Channel
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'id': msg_obj['id'],
                    'expediteur': self.user.id,
                    'expediteur_nom': f"{self.user.first_name} {self.user.last_name}".strip() or self.user.username,
                    'contenu': contenu,
                    'date_envoi': msg_obj['date_envoi'],
                }
            )

    # --- 1. GESTION : NOUVEAU MESSAGE ---
    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'action': 'message_new',
            'id': event['id'],
            'expediteur': event['expediteur'],
            'expediteur_nom': event['expediteur_nom'],
            'message': event['contenu'],
            'date_envoi': event['date_envoi'],
            'est_modifie': False
        }))

    # --- 2. GESTION : MODIFICATION DE MESSAGE (LIVE) ---
    async def chat_message_update(self, event):
        await self.send(text_data=json.dumps({
            'action': 'message_update',
            'id': event['message_id'],
            'message': event['contenu'],
            'est_modifie': True
        }))

    # --- 3. GESTION : SUPPRESSION DE MESSAGE (LIVE) ---
    async def chat_message_delete(self, event):
        await self.send(text_data=json.dumps({
            'action': 'message_delete',
            'id': event['message_id']
        }))

    @database_sync_to_async
    def save_message(self, contenu):
        """Persiste le message avec les relations appropriées au salon"""
        try:
            msg = Message(expediteur=self.user, contenu=contenu)

            if self.room_type == 'private':
                msg.receveur_id = self.contact_id

            elif self.room_type == 'classe':
                enseignant_prof = Enseignant.objects.get(utilisateur_id=self.enseignant_user_id)
                msg.classe_enseignant = enseignant_prof

            elif self.room_type == 'famille':
                parent_prof = Parent.objects.get(utilisateur_id=self.parent_user_id)
                msg.groupe_parent = parent_prof

            msg.save()

            return {
                'id': msg.id,
                'date_envoi': msg.date_envoi.isoformat()
            }
        except Exception:
            return None


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if not self.user.is_authenticated:
            await self.close()
            return

        self.room_group_name = f"notify_{self.user.id}"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def send_notification(self, event):
        await self.send(text_data=json.dumps(event['data']))