from django.db import models
from django.conf import settings
from enseignant.models import Lecon, Exercice


# --- 1. MODÈLE : Message (Chat privé & de groupe) ---
class Message(models.Model):
    expediteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='messages_envoyes'
    )
    receveur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='messages_recus',
        null=True,
        blank=True
    )
    classe_enseignant = models.ForeignKey(
        'Uauth.Enseignant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='messages_classe'
    )
    groupe_parent = models.ForeignKey(
        'Uauth.Parent',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='messages_groupe_parent'
    )
    contenu = models.TextField(verbose_name="Message")
    date_envoi = models.DateTimeField(auto_now_add=True)
    est_lu = models.BooleanField(default=False)

    # AJOUT : Suivi de modification
    est_modifie = models.BooleanField(default=False)

    class Meta:
        ordering = ['date_envoi']
        verbose_name = "Message"

    def __str__(self):
        if self.receveur:
            return f"Privé | De {self.expediteur} à {self.receveur} ({self.date_envoi})"
        elif self.classe_enseignant:
            return f"Classe | De {self.expediteur} dans le salon de {self.classe_enseignant.utilisateur} ({self.date_envoi})"
        elif self.groupe_parent:
            return f"Famille | De {self.expediteur} dans la famille de {self.groupe_parent.utilisateur} ({self.date_envoi})"
        return f"Message {self.id}"


# --- 2. MODÈLE : Notification (Alertes) ---
class Notification(models.Model):
    TYPE_CHOICES = [
        ('LECON_PUBLIEE', 'Nouvelle Leçon'),
        ('LECTURE_COURS', 'Cours Lu'),
        ('EXERCICE_FINI', 'Exercice Terminé'),
        ('QUIZ_FINI', 'Quiz Terminé'),
        ('MESSAGE_RECU', 'Nouveau Message'),
    ]

    receveur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    type_notif = models.CharField(max_length=20, choices=TYPE_CHOICES)
    titre = models.CharField(max_length=255)
    message = models.TextField()
    date_creation = models.DateTimeField(auto_now_add=True)
    est_lu = models.BooleanField(default=False)
    lecon_liee = models.ForeignKey(Lecon, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-date_creation']

    def __str__(self):
        return f"{self.titre} pour {self.receveur}"


# --- 3. MODÈLE : Suivi de Lecture ---
class SuiviLecture(models.Model):
    enfant = models.ForeignKey('Uauth.Enfant', on_delete=models.CASCADE)
    lecon = models.ForeignKey(Lecon, on_delete=models.CASCADE)
    date_lecture = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('enfant', 'lecon')
        verbose_name = "Suivi de lecture"


# --- 4. MODÈLE : Résultat d'Exercice ---
class ResultatExercice(models.Model):
    enfant = models.ForeignKey('Uauth.Enfant', on_delete=models.CASCADE, related_name='resultats_exercices')
    exercice = models.ForeignKey(Exercice, on_delete=models.CASCADE, related_name='resultats')
    reponse_eleve = models.CharField(max_length=255)
    est_correct = models.BooleanField()
    date_soumission = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Résultat d'exercice"
        ordering = ['-date_soumission']