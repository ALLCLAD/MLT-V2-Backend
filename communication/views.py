from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model

# Importations pour la diffusion temps-réel avec Django Channels
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from Uauth.models import Enfant, Parent, Enseignant, SuiviParentEnfant, SuiviEnseignantEnfant
from .models import Message, Notification
from .serializers import MessageSerializer, NotificationSerializer, UserMinimalSerializer

User = get_user_model()


# --- VUE : Liste structurée des salons de discussions par Rôle ---
class ContactListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        response_data = {
            "chats_groupe": [],
            "chats_prives": []
        }

        if user.role == 'ENFANT':
            enfant_profil = getattr(user, 'profil_enfant', None)
            if enfant_profil:
                enseignants = Enseignant.objects.filter(eleves=enfant_profil).select_related('utilisateur')
                for ens in enseignants:
                    response_data["chats_groupe"].append({
                        "type": "classe",
                        "enseignant_id": ens.utilisateur.id,
                        "titre": f"Mon Chat de Classe ({ens.utilisateur.first_name})"
                    })
                parents = Parent.objects.filter(enfants=enfant_profil).select_related('utilisateur')
                for par in parents:
                    response_data["chats_groupe"].append({
                        "type": "famille",
                        "parent_id": par.utilisateur.id,
                        "titre": f"Ma Famille ({par.utilisateur.last_name})"
                    })

        elif user.role == 'PARENT':
            parent_profil = getattr(user, 'profil_parent', None)
            if parent_profil:
                response_data["chats_groupe"].append({
                    "type": "famille",
                    "parent_id": user.id,
                    "titre": f"Espace Familial ({user.first_name})"
                })
                mes_enfants = Enfant.objects.filter(parents=parent_profil)
                profs = Enseignant.objects.filter(eleves__in=mes_enfants).select_related('utilisateur').distinct()
                for prof in profs:
                    response_data["chats_prives"].append({
                        "contact": UserMinimalSerializer(prof.utilisateur).data,
                        "contexte": "Enseignant de votre enfant"
                    })

        elif user.role == 'ENSEIGNANT':
            enseignant_profil = getattr(user, 'profil_enseignant', None)
            if enseignant_profil:
                response_data["chats_groupe"].append({
                    "type": "classe",
                    "enseignant_id": user.id,
                    "titre": "Ma Classe (Tous les élèves)"
                })
                eleves = Enfant.objects.filter(enseignants=enseignant_profil)
                suivis_parents = SuiviParentEnfant.objects.filter(enfant__in=eleves).select_related(
                    'parent__utilisateur', 'enfant__utilisateur')

                parents_visites = set()
                for sp in suivis_parents:
                    parent_user = sp.parent.utilisateur
                    if parent_user.id not in parents_visites:
                        parents_visites.add(parent_user.id)
                        response_data["chats_prives"].append({
                            "contact": UserMinimalSerializer(parent_user).data,
                            "contexte": f"Parent de {sp.enfant.utilisateur.first_name}"
                        })

        return Response(response_data, status=status.HTTP_200_OK)


# --- VUE : Historique Chat Privé (1-à-1) ---
class PrivateMessageView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, contact_id):
        messages = Message.objects.filter(
            (Q(expediteur=request.user) & Q(receveur_id=contact_id)) |
            (Q(expediteur_id=contact_id) & Q(receveur=request.user))
        ).order_by('date_envoi')

        Message.objects.filter(expediteur_id=contact_id, receveur=request.user, est_lu=False).update(est_lu=True)
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# --- VUE : Historique Chat Salon de Classe ---
class ClasseMessageView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, enseignant_id):
        enseignant_prof = get_object_or_404(Enseignant, utilisateur_id=enseignant_id)
        messages = Message.objects.filter(classe_enseignant=enseignant_prof).order_by('date_envoi')
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# --- VUE : Historique Chat Salon Famille ---
class FamilleMessageView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, parent_id):
        parent_prof = get_object_or_404(Parent, utilisateur_id=parent_id)
        messages = Message.objects.filter(groupe_parent=parent_prof).order_by('date_envoi')
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# --- VUE DETAIL : Mise à jour & Suppression d'un Message (Avec WebSockets) ---
class MessageDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, message_id):
        message = get_object_or_404(Message, id=message_id)

        # Sécurité : Vérifier que c'est l'auteur du message
        if message.expediteur != request.user:
            return Response({"error": "Action interdite."}, status=status.HTTP_403_FORBIDDEN)

        nouveau_contenu = request.data.get('contenu', '').strip()
        if not nouveau_contenu:
            return Response({"error": "Le contenu ne peut pas être vide."}, status=status.HTTP_400_BAD_REQUEST)

        message.contenu = nouveau_contenu
        message.est_modifie = True
        message.save()

        # --- ÉMISSION WEBSOCKET : MODIFICATION EN LIVE ---
        channel_layer = get_channel_layer()
        if message.receveur:
            ids = sorted([message.expediteur.id, message.receveur.id])
            room_group_name = f"chat_private_{ids[0]}_{ids[1]}"
        elif message.classe_enseignant:
            room_group_name = f"chat_classe_{message.classe_enseignant.utilisateur.id}"
        else:
            room_group_name = f"chat_famille_{message.groupe_parent.utilisateur.id}"

        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                "type": "chat_message_update",
                "message_id": message.id,
                "contenu": message.contenu,
                "est_modifie": True
            }
        )

        return Response(MessageSerializer(message).data, status=status.HTTP_200_OK)

    def delete(self, request, message_id):
        message = get_object_or_404(Message, id=message_id)

        if message.expediteur != request.user:
            return Response({"error": "Action interdite."}, status=status.HTTP_403_FORBIDDEN)

        id_supprime = message.id

        # --- ÉMISSION WEBSOCKET : SUPPRESSION EN LIVE ---
        channel_layer = get_channel_layer()
        if message.receveur:
            ids = sorted([message.expediteur.id, message.receveur.id])
            room_group_name = f"chat_private_{ids[0]}_{ids[1]}"
        elif message.classe_enseignant:
            room_group_name = f"chat_classe_{message.classe_enseignant.utilisateur.id}"
        else:
            room_group_name = f"chat_famille_{message.groupe_parent.utilisateur.id}"

        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                "type": "chat_message_delete",
                "message_id": id_supprime
            }
        )

        message.delete()
        return Response({"message": "Message supprimé.", "id": id_supprime}, status=status.HTTP_200_OK)


# --- VUE : Liste des Notifications et Actions Globales ---
class NotificationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        notifs = Notification.objects.filter(receveur=request.user)
        return Response(NotificationSerializer(notifs, many=True).data)

    def post(self, request):
        action = request.data.get('action')
        if action == 'tout-lire':
            Notification.objects.filter(receveur=request.user, est_lu=False).update(est_lu=True)
            return Response({"message": "Toutes les notifications ont été marquées comme lues"})
        elif action == 'tout-supprimer':
            Notification.objects.filter(receveur=request.user).delete()
            return Response({"message": "Toutes les notifications ont été supprimées"})
        return Response({"error": "Action non reconnue ou manquante"}, status=status.HTTP_400_BAD_REQUEST)


class NotificationLireView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, notif_id):
        notif = get_object_or_404(Notification, id=notif_id, receveur=request.user)
        notif.est_lu = True
        notif.save()
        return Response({"message": "Marquée comme lue"})


class NotificationSupprimerView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, notif_id):
        notif = get_object_or_404(Notification, id=notif_id, receveur=request.user)
        notif.delete()
        return Response({"message": "Notification supprimée"})


class EnregistrerLectureView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, lecon_id):
        if request.user.role != 'ENFANT':
            return Response(status=status.HTTP_403_FORBIDDEN)
        from .models import SuiviLecture
        from enseignant.models import Lecon
        obj, created = SuiviLecture.objects.get_or_create(enfant=request.user.profil_enfant, lecon_id=lecon_id)
        return Response({"message": "Enregistré"}, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class FinExercicesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.role != 'ENFANT':
            return Response(status=status.HTTP_403_FORBIDDEN)

        from mlt_quiz.models import ScoreQuiz
        from enseignant.models import Lecon
        from .signals import send_live_notification

        enfant = request.user.profil_enfant
        score, total = int(request.data.get('score', 0)), int(request.data.get('total', 1))
        lecon_id = request.data.get('lecon_id')
        note = round((score / total) * 20, 1) if total > 0 else 0

        if lecon_id:
            try:
                lecon = Lecon.objects.get(id=lecon_id)
                ScoreQuiz.objects.create(enfant=enfant, theme=lecon.theme, points=score, total_questions=total, temps=0)
            except Lecon.DoesNotExist:
                pass

        type_n, titre = 'EXERCICE_FINI', "Exercices terminés" if note >= 10 else "Exercices non terminés"
        message = f"{enfant.utilisateur.first_name} — « {request.data.get('lecon_titre', '')} » — {note}/20"

        for sp in SuiviParentEnfant.objects.filter(enfant=enfant):
            Notification.objects.create(receveur=sp.parent.utilisateur, type_notif=type_n, titre=titre, message=message)
            send_live_notification(sp.parent.utilisateur.id, {"type": type_n, "titre": titre, "message": message})

        for se in SuiviEnseignantEnfant.objects.filter(enfant=enfant):
            Notification.objects.create(receveur=se.enseignant.utilisateur, type_notif=type_n, titre=titre,
                                        message=message)
            send_live_notification(se.enseignant.utilisateur.id, {"type": type_n, "titre": titre, "message": message})

        return Response({"message": "OK"}, status=status.HTTP_201_CREATED)