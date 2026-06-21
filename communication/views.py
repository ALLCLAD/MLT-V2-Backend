from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.db.models import Q
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from Uauth.models import Enfant, Parent, Enseignant, SuiviParentEnfant, SuiviEnseignantEnfant
from enseignant.models import Lecon, Exercice
from mlt_quiz.models import ScoreQuiz   # ← Import ajouté pour sauvegarder le score
from .models import Message, Notification, SuiviLecture, ResultatExercice
from .serializers import MessageSerializer, NotificationSerializer, ContactSerializer


def send_live_notification(user_id, data):
    """Envoie l'alerte temps réel via WebSocket"""
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'notify_{user_id}',
        {'type': 'send_notification', 'data': data}
    )


# VUE : Liste des contacts autorisés selon le rôle
class ContactListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        contacts = []

        # --- CAS 1 : L'ENFANT ---
        if user.role == 'ENFANT':
            enfant_profil = user.profil_enfant
            parents = Parent.objects.filter(enfants=enfant_profil)
            for p in parents: contacts.append(p.utilisateur)
            enseignants = Enseignant.objects.filter(eleves=enfant_profil)
            for e in enseignants: contacts.append(e.utilisateur)
            # Camarades = élèves du MÊME enseignant uniquement (pas juste même niveau)
            camarades_ids = SuiviEnseignantEnfant.objects.filter(
                enseignant__in=enseignants
            ).values_list('enfant_id', flat=True)
            camarades = Enfant.objects.filter(id__in=camarades_ids).exclude(id=enfant_profil.id)
            for c in camarades: contacts.append(c.utilisateur)

        # --- CAS 2 : L'ENSEIGNANT ---
        elif user.role == 'ENSEIGNANT':
            enseignant_profil = user.profil_enseignant
            eleves = Enfant.objects.filter(enseignants=enseignant_profil)
            for e in eleves:
                contacts.append(e.utilisateur)
                parents = Parent.objects.filter(enfants=e)
                for p in parents: contacts.append(p.utilisateur)

        # --- CAS 3 : LE PARENT ---
        elif user.role == 'PARENT':
            parent_profil = user.profil_parent
            mes_enfants = Enfant.objects.filter(parents=parent_profil)
            for e in mes_enfants:
                contacts.append(e.utilisateur)
                profs = Enseignant.objects.filter(eleves=e)
                for p in profs: contacts.append(p.utilisateur)

        # Suppression des doublons + exclusion de l'utilisateur lui-même
        contacts = list({c.id: c for c in contacts if c.id != user.id}.values())
        serializer = ContactSerializer(contacts, many=True)
        return Response(serializer.data)


# VUE : Lire et Envoyer des messages
class MessageView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, contact_id):
        messages = Message.objects.filter(
            (Q(expediteur=request.user) & Q(receveur_id=contact_id)) |
            (Q(expediteur_id=contact_id) & Q(receveur=request.user))
        ).order_by('date_envoi')
        Message.objects.filter(expediteur_id=contact_id, receveur=request.user, est_lu=False).update(est_lu=True)
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = MessageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(expediteur=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# VUE : Supprimer une notification précise (DELETE) ---
class NotificationSupprimerView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, notif_id):
        try:
            notif = Notification.objects.get(id=notif_id, receveur=request.user)
            notif.delete()
            return Response({"message": "Notification supprimée"}, status=status.HTTP_200_OK)
        except Notification.DoesNotExist:
            return Response({"error": "Notification introuvable"}, status=status.HTTP_404_NOT_FOUND)

# VUE : Liste des notifications
class NotificationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        notifs = Notification.objects.filter(receveur=request.user)
        serializer = NotificationSerializer(notifs, many=True)
        return Response(serializer.data)

    def post(self, request):
        """Marque toutes les notifications de l'utilisateur comme lues"""
        # On cherche l'URL pour savoir si c'est une demande de "tout-lire"
        if 'tout-lire' in request.path:
            Notification.objects.filter(receveur=request.user, est_lu=False).update(est_lu=True)
            return Response({"message": "Toutes les notifications ont été marquées comme lues"}, status=status.HTTP_200_OK)

        # NOUVELLE LOGIQUE : Tout supprimer
        elif 'tout-supprimer' in request.path:
            Notification.objects.filter(receveur=request.user).delete()
            return Response({"message": "Toutes les notifications ont été supprimées"}, status=status.HTTP_200_OK)

        return Response({"error": "Action non reconnue"}, status=status.HTTP_400_BAD_REQUEST)



# VUE : Marquer une notification comme lue (PATCH)
class NotificationLireView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, notif_id):
        try:
            notif = Notification.objects.get(id=notif_id, receveur=request.user)
            notif.est_lu = True
            notif.save()
            return Response({"message": "Marquée comme lue"})
        except Notification.DoesNotExist:
            return Response({"error": "Notif introuvable"}, status=status.HTTP_404_NOT_FOUND)


# VUE : Enregistrer la lecture d'un cours (POST)
class EnregistrerLectureView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, lecon_id):
        if request.user.role != 'ENFANT':
            return Response({"error": "Action non autorisée."}, status=status.HTTP_403_FORBIDDEN)
        try:
            enfant = request.user.profil_enfant
        except Exception:
            return Response({"error": "Profil enfant introuvable."}, status=status.HTTP_404_NOT_FOUND)
        try:
            lecon = Lecon.objects.get(id=lecon_id)
        except Lecon.DoesNotExist:
            return Response({"error": "Leçon introuvable."}, status=status.HTTP_404_NOT_FOUND)

        obj, created = SuiviLecture.objects.get_or_create(enfant=enfant, lecon=lecon)
        if created:
            return Response({"message": "Lecture enregistrée."}, status=status.HTTP_201_CREATED)
        return Response({"message": "Déjà lu."}, status=status.HTTP_200_OK)


# VUE : Fin de tous les exercices d'une leçon (POST)
# Appelée UNE SEULE FOIS quand l'enfant finit TOUS les exercices
# Fait deux choses :
#   1. Sauvegarde UN ScoreQuiz (réutilise le modèle existant → graphes mis à jour automatiquement)
#   2. Envoie UNE notification groupée aux Parents et Enseignants
class FinExercicesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.role != 'ENFANT':
            return Response({"error": "Action non autorisée."}, status=status.HTTP_403_FORBIDDEN)

        try:
            enfant = request.user.profil_enfant
        except Exception:
            return Response({"error": "Profil enfant introuvable."}, status=status.HTTP_404_NOT_FOUND)

        # Données reçues depuis FaireExercice.jsx
        score       = int(request.data.get('score', 0))
        total       = int(request.data.get('total', 1))
        lecon_titre = request.data.get('lecon_titre', 'une leçon')
        lecon_id    = request.data.get('lecon_id')

        # Calcul de la note sur 20
        note = round((score / total) * 20, 1) if total > 0 else 0

        
        # ÉTAPE 1 : Sauvegarder UN ScoreQuiz avec le thème de la leçon
        # → Tous les graphes (parent + enseignant) et les stats par thème
        #   se mettent à jour automatiquement sans aucune modification des vues de stats
        
        if lecon_id:
            try:
                lecon = Lecon.objects.get(id=lecon_id)
                ScoreQuiz.objects.create(
                    enfant=enfant,
                    theme=lecon.theme,      # même valeur que ThemeQuiz (CALCUL, GEOMETRIE...)
                    points=score,
                    total_questions=total,
                    temps=0,                # pas de mesure de temps pour les exercices de leçon
                )
            except Lecon.DoesNotExist:
                pass  # on continue même si la leçon n'est pas trouvée

        
        # ÉTAPE 2 : Envoyer UNE SEULE notification groupée selon le résultat
        
        type_n  = 'EXERCICE_FINI'
        titre   = "Exercices terminés" if note >= 10 else "Exercices non terminés"
        message = f"{enfant.utilisateur.first_name} — « {lecon_titre} » — {note}/20"
        data    = {"type": type_n, "titre": titre, "message": message}

        for sp in SuiviParentEnfant.objects.filter(enfant=enfant):
            u = sp.parent.utilisateur
            Notification.objects.create(receveur=u, type_notif=type_n, titre=titre, message=message)
            send_live_notification(u.id, data)

        for se in SuiviEnseignantEnfant.objects.filter(enfant=enfant):
            u = se.enseignant.utilisateur
            Notification.objects.create(receveur=u, type_notif=type_n, titre=titre, message=message)
            send_live_notification(u.id, data)

        return Response({"message": "Score enregistré et notification envoyée."}, status=status.HTTP_201_CREATED)
