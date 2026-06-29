from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import asyncio

from enseignant.models import Lecon
from mlt_quiz.models import ScoreQuiz
from .models import Notification, ResultatExercice, SuiviLecture, Message
from Uauth.models import SuiviEnseignantEnfant, SuiviParentEnfant


def send_live_notification(user_id, data):
    """Envoie l'alerte temps réel via WebSocket de manière sécurisée sans bloquer le thread pool"""
    channel_layer = get_channel_layer()
    try:
        async_to_sync(channel_layer.group_send)(
            f'notify_{user_id}',
            {'type': 'send_notification', 'data': data}
        )
    except RuntimeError:
        # Si le thread est coincé ou n'a pas de boucle d'événement propre
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(channel_layer.group_send(
            f'notify_{user_id}',
            {'type': 'send_notification', 'data': data}
        ))
        loop.close()


def format_notif_payload(notif_instance):
    """Formate la notification pour qu'elle corresponde exactement à ce qu'attend React"""
    return {
        "id": notif_instance.id,
        "type_notif": notif_instance.type_notif,
        "titre": notif_instance.titre,
        "message": notif_instance.message,
        "est_lu": notif_instance.est_lu,
        "date_creation": notif_instance.date_creation.isoformat() if hasattr(notif_instance.date_creation,
                                                                             'isoformat') else str(
            notif_instance.date_creation)
    }


def alerter_adultes(enfant, type_n, titre, message):
    """
    Notifie tous les adultes (Parents et Enseignants) liés à l'enfant.
    Crée une Notification en base + envoie en temps réel via WebSocket.
    """
    # Notifier les Parents
    for sp in SuiviParentEnfant.objects.filter(enfant=enfant):
        user_p = sp.parent.utilisateur
        notif = Notification.objects.create(receveur=user_p, type_notif=type_n, titre=titre, message=message)
        data = format_notif_payload(notif)
        send_live_notification(user_p.id, data)

    # Notifier les Enseignants
    for se in SuiviEnseignantEnfant.objects.filter(enfant=enfant):
        user_e = se.enseignant.utilisateur
        notif = Notification.objects.create(receveur=user_e, type_notif=type_n, titre=titre, message=message)
        data = format_notif_payload(notif)
        send_live_notification(user_e.id, data)


# 1. Alerte : Nouvelle Leçon publiée (Pour les Enfants)
@receiver(post_save, sender=Lecon)
def notifier_lecon_publiee(sender, instance, created, **kwargs):
    if instance.statut == 'publie':
        deja_notifie = Notification.objects.filter(
            lecon_liee=instance,
            type_notif='LECON_PUBLIEE'
        ).exists()
        if deja_notifie:
            return

        suivis = SuiviEnseignantEnfant.objects.filter(enseignant=instance.enseignant)
        for s in suivis:
            user = s.enfant.utilisateur
            notif = Notification.objects.create(
                receveur=user,
                type_notif='LECON_PUBLIEE',
                titre="Nouveau cours !",
                message=f"Le prof a publié : {instance.titre}",
                lecon_liee=instance
            )
            data = format_notif_payload(notif)
            send_live_notification(user.id, data)


# 2. Alerte : Quiz Terminé (Pour les Parents et Enseignants)
@receiver(post_save, sender=ScoreQuiz)
def notifier_score_quiz(sender, instance, created, **kwargs):
    if created:
        e = instance.enfant
        alerter_adultes(e, 'QUIZ_FINI', "Score Quiz", f"{e.utilisateur.first_name} a fini son quiz : {instance.theme}")


# 4. Alerte : Cours Lu (Pour les Parents et Enseignants)
@receiver(post_save, sender=SuiviLecture)
def notifier_lecture_cours(sender, instance, created, **kwargs):
    if created:
        e = instance.enfant
        alerter_adultes(e, 'LECTURE_COURS', "Cours lu",
                        f"{e.utilisateur.first_name} a lu le cours : {instance.lecon.titre}")


# 5. Alerte : Nouveau Message Reçu (Gère le Privé, les Salons de Classe et Famille)
@receiver(post_save, sender=Message)
def notifier_nouveau_message(sender, instance, created, **kwargs):
    if not created:
        return

    nom_expediteur = instance.expediteur.first_name or instance.expediteur.username
    titre = "Nouveau message"
    message_text = f"De : {nom_expediteur}"

    # Pile dynamique de destinataires pour éviter les crashs si receveur est None
    destinataires = []

    # --- CAS 1 : MESSAGE PRIVÉ ---
    if instance.receveur:
        destinataires.append(instance.receveur)

    # --- CAS 2 : MESSAGE DANS LE SALON DE CLASSE ---
    elif instance.classe_enseignant:
        enseignant = instance.classe_enseignant
        # Si c'est l'enseignant qui écrit -> On alerte tous ses élèves
        if instance.expediteur == enseignant.utilisateur:
            suivis = SuiviEnseignantEnfant.objects.filter(enseignant=enseignant)
            destinataires.extend([s.enfant.utilisateur for s in suivis])
        # Si c'est un élève qui écrit -> On alerte l'enseignant
        else:
            destinataires.append(enseignant.utilisateur)

    # --- CAS 3 : MESSAGE DANS LE SALON FAMILLE ---
    elif instance.groupe_parent:
        parent = instance.groupe_parent
        # Si c'est le parent qui écrit -> On alerte tous ses enfants
        if instance.expediteur == parent.utilisateur:
            suivis = SuiviParentEnfant.objects.filter(parent=parent)
            destinataires.extend([s.enfant.utilisateur for s in suivis])
        # Si c'est un enfant qui écrit -> On alerte le parent
        else:
            destinataires.append(parent.utilisateur)

    # Dispatch final des notifications (BDD + WebSocket)
    for u in destinataires:
        # Sécurité : On s'assure de ne jamais envoyer une notification à l'expéditeur lui-même
        if u != instance.expediteur:
            notif = Notification.objects.create(
                receveur=u,
                type_notif='MESSAGE_RECU',
                titre=titre,
                message=message_text
            )
            data = format_notif_payload(notif)
            send_live_notification(u.id, data)