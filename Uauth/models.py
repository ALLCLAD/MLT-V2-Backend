from django.db import models
from django.contrib.auth.models import AbstractUser

# MODÈLE : Utilisateur

class Utilisateur(AbstractUser):
    """
    Modèle de base pour tous les utilisateurs de la plateforme.
    Hérite d'AbstractUser pour garder toutes les fonctionnalités
    de Django (authentification, permissions, etc.)
    """

    class Role(models.TextChoices):
        """
        Choix du rôle de l'utilisateur.
        Détermine l'espace auquel il a accès après connexion.
        """
        ENFANT     = 'ENFANT',     'Enfant'
        PARENT     = 'PARENT',     'Parent'
        ENSEIGNANT = 'ENSEIGNANT', 'Enseignant'

    # Rôle de l'utilisateur — obligatoire à l'inscription
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        verbose_name="Rôle"
    )

    # Email unique pour éviter les doublons entre comptes
    email = models.EmailField(
        unique=True,
        null=True,
        blank=True,
        verbose_name="Adresse email"
    )

    def __str__(self):
        return f"{self.username} ({self.role})"

# MODÈLE : Classe (TextChoices)


class Classe(models.TextChoices):
    """
    Niveaux scolaires disponibles sur la plateforme.
    Du CP1 au CM2 (école primaire).
    """
    CP1 = 'CP1', 'CP1'
    CP2 = 'CP2', 'CP2'
    CE1 = 'CE1', 'CE1'
    CE2 = 'CE2', 'CE2'
    CM1 = 'CM1', 'CM1'
    CM2 = 'CM2', 'CM2'

# MODÈLE : Enfant

class Enfant(models.Model):
    """
    Profil d'un enfant sur la plateforme.
    Lié en OneToOne à un Utilisateur de rôle ENFANT.
    """

    # Lien vers le compte utilisateur de l'enfant
    utilisateur = models.OneToOneField(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='profil_enfant',
        verbose_name="Compte utilisateur"
    )

    # Niveau scolaire de l'enfant
    classe = models.CharField(
        max_length=20,
        choices=Classe.choices,
        verbose_name="Classe"
    )

    def __str__(self):
        return f"{self.utilisateur.first_name} {self.utilisateur.last_name} ({self.classe})"

# MODÈLE : Parent

class Parent(models.Model):
    """
    Profil d'un parent sur la plateforme.
    Lié en OneToOne à un Utilisateur de rôle PARENT.
    Peut suivre plusieurs enfants.
    """

    # Lien vers le compte utilisateur du parent
    utilisateur = models.OneToOneField(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='profil_parent',
        verbose_name="Compte utilisateur"
    )

    # Relation ManyToMany avec les enfants via la table intermédiaire
    enfants = models.ManyToManyField(
        'Enfant',
        through='SuiviParentEnfant',
        related_name='parents',
        blank=True,
        verbose_name="Enfants suivis"
    )

    def __str__(self):
        return f"Parent : {self.utilisateur.first_name} {self.utilisateur.last_name}"


# MODÈLE : Enseignant

class Enseignant(models.Model):
    """
    Profil d'un enseignant sur la plateforme.
    Lié en OneToOne à un Utilisateur de rôle ENSEIGNANT.
    Peut avoir plusieurs élèves via SuiviEnseignantEnfant.
    """

    # Lien vers le compte utilisateur de l'enseignant
    utilisateur = models.OneToOneField(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='profil_enseignant',
        verbose_name="Compte utilisateur"
    )

    # Établissement scolaire de l'enseignant (optionnel)
    etablissement = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        default="Non spécifié",
        verbose_name="Établissement"
    )

    # Niveau scolaire enseigné par le professeur
    classe_enseignement = models.CharField(
        max_length=20,
        choices=Classe.choices,
        verbose_name="Classe enseignée"
    )

    # Relation ManyToMany avec les enfants via la table intermédiaire
    eleves = models.ManyToManyField(
        'Enfant',
        through='SuiviEnseignantEnfant',
        related_name='enseignants',
        blank=True,
        verbose_name="Élèves de la classe"
    )

    def __str__(self):
        return f"Prof. {self.utilisateur.first_name} {self.utilisateur.last_name} ({self.classe_enseignement})"

# MODÈLE : SuiviParentEnfant

class SuiviParentEnfant(models.Model):
    """
    Table intermédiaire pour le suivi parent-enfant.
    Enregistre la date à laquelle le parent a inscrit l'enfant.
    """

    # Le parent qui suit l'enfant
    parent = models.ForeignKey(
        Parent,
        on_delete=models.CASCADE,
        verbose_name="Parent"
    )

    # L'enfant suivi par le parent
    enfant = models.ForeignKey(
        Enfant,
        on_delete=models.CASCADE,
        verbose_name="Enfant"
    )

    # Date automatique de l'inscription de l'enfant par le parent
    date_inscription = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date d'inscription"
    )

    class Meta:
        verbose_name = "Suivi Parent-Enfant"
        verbose_name_plural = "Suivis Parent-Enfant"

    def __str__(self):
        return f"{self.parent} → {self.enfant}"


# MODÈLE : SuiviEnseignantEnfant

class SuiviEnseignantEnfant(models.Model):
    """
    Table intermédiaire pour le suivi enseignant-élève.
    Enregistre la date à laquelle l'enseignant a ajouté l'élève.
    """

    # L'enseignant qui a ajouté l'élève
    enseignant = models.ForeignKey(
        Enseignant,
        on_delete=models.CASCADE,
        verbose_name="Enseignant"
    )

    # L'élève ajouté à la classe
    enfant = models.ForeignKey(
        Enfant,
        on_delete=models.CASCADE,
        verbose_name="Élève"
    )

    # Date automatique de l'ajout de l'élève à la classe
    date_ajout = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date d'ajout"
    )

    class Meta:
        verbose_name = "Suivi Enseignant-Élève"
        verbose_name_plural = "Suivis Enseignant-Élève"

    def __str__(self):
        return f"{self.enseignant} → {self.enfant}"
