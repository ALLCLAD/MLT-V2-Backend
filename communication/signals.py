from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from enseignant.models import Lecon
from mlt_quiz.models import ScoreQuiz
from .models import Notification, ResultatExercice, SuiviLecture, Message
from Uauth.models import SuiviEnseignantEnfant, SuiviParentEnfant


def send_live_notification(user_id, data):
    """Envoie l'alerte temps réel via WebSocket au canal de l'utilisateur ciblé"""
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'notify_{user_id}',
        {'type': 'send_notification', 'data': data}
    )


def alerter_adultes(enfant, type_n, titre, message):
    """
    Notifie tous les adultes (Parents et Enseignants) liés à l'enfant.
    Crée une Notification en base + envoie en temps réel via WebSocket.
    """
    data = {"type": type_n, "titre": titre, "message": message}
    # Notifier les Parents
    for sp in SuiviParentEnfant.objects.filter(enfant=enfant):
        user_p = sp.parent.utilisateur
        Notification.objects.create(receveur=user_p, type_notif=type_n, titre=titre, message=message)
        send_live_notification(user_p.id, data)
    # Notifier les Enseignants
    for se in SuiviEnseignantEnfant.objects.filter(enfant=enfant):
        user_e = se.enseignant.utilisateur
        Notification.objects.create(receveur=user_e, type_notif=type_n, titre=titre, message=message)
        send_live_notification(user_e.id, data)


# 1. Alerte : Nouvelle Leçon publiée (Pour les Enfants)
@receiver(post_save, sender=Lecon)
def notifier_lecon_publiee(sender, instance, created, **kwargs):
    if instance.statut == 'publie':
        # Anti-spam : on vérifie qu'une notif n'a pas déjà été envoyée pour cette leçon
        deja_notifie = Notification.objects.filter(
            lecon_liee=instance,
            type_notif='LECON_PUBLIEE'
        ).exists()
        if deja_notifie:
            return
        suivis = SuiviEnseignantEnfant.objects.filter(enseignant=instance.enseignant)
        for s in suivis:
            user = s.enfant.utilisateur
            data = {"type": "LECON_PUBLIEE", "titre": "Nouveau cours !", "message": f"Le prof a publié : {instance.titre}"}
            Notification.objects.create(receveur=user, type_notif='LECON_PUBLIEE', titre=data["titre"], message=data["message"], lecon_liee=instance)
            send_live_notification(user.id, data)


# 2. Alerte : Quiz (外部 JSON) Terminé (Pour les Parents et Enseignants)
@receiver(post_save, sender=ScoreQuiz)
def notifier_score_quiz(sender, instance, created, **kwargs):
    # Seulement à la création du score (pas d'update)
    if created:
        e = instance.enfant
        alerter_adultes(e, 'QUIZ_FINI', "Score Quiz", f"{e.utilisateur.first_name} a fini son quiz : {instance.theme}")


# 3. SIGNAL EXERCICE LEÇON DÉSACTIVÉ INTENTIONNELLEMENT
# La notification groupée est maintenant gérée par FinExercicesView (views.py)
# → UNE SEULE notif à la fin de TOUS les exercices (pas une par exercice)
# @receiver(post_save, sender=ResultatExercice)
# def notifier_exercice_fini(...) → SUPPRIMÉ


# 4. Alerte : Cours Lu (Pour les Parents et Enseignants)
@receiver(post_save, sender=SuiviLecture)
def notifier_lecture_cours(sender, instance, created, **kwargs):
    # Seulement à la première lecture (unique_together empêche les doublons)
    if created:
        e = instance.enfant
        alerter_adultes(e, 'LECTURE_COURS', "Cours lu", f"{e.utilisateur.first_name} a lu le cours : {instance.lecon.titre}")


# 5. Alerte : Nouveau Message Reçu
@receiver(post_save, sender=Message)
def notifier_nouveau_message(sender, instance, created, **kwargs):
    if created:
        u = instance.receveur
        data = {"type": "MESSAGE_RECU", "titre": "Nouveau message", "message": f"De : {instance.expediteur.first_name or instance.expediteur.username}"}
        Notification.objects.create(receveur=u, type_notif='MESSAGE_RECU', titre=data["titre"], message=data["message"])
        send_live_notification(u.id, data)
