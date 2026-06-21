from django.db import models
from Uauth.models import Enseignant, Enfant, Classe

# MODÈLE : Lecon

class Lecon(models.Model):
    """
    Leçon créée par un enseignant.
    Contient le contenu généré par l'IA et les exercices liés.
    """

    class Statut(models.TextChoices):
        """
        Statut de la leçon.
        BROUILLON : visible uniquement par l'enseignant
        PUBLIE    : visible par les élèves de la classe
        """
        BROUILLON = 'brouillon', 'Brouillon'
        PUBLIE    = 'publie',    'Publiée'

    class Theme(models.TextChoices):
        """
        Thème mathématique de la leçon.
        Utilisé pour lier les scores des exercices aux statistiques.
        """
        CALCUL        = 'CALCUL',        'Calcul et Opérations'
        GEOMETRIE     = 'GEOMETRIE',     'Géométrie et Formes'
        DENOMBREMENT  = 'DENOMBREMENT',  'Dénombrement et Nombres'
        GRANDEURS     = 'GRANDEURS',     'Grandeurs et Mesures'

    # L'enseignant qui a créé cette leçon
    # Si l'enseignant est supprimé, toutes ses leçons le sont aussi
    enseignant = models.ForeignKey(
        Enseignant,
        on_delete=models.CASCADE,
        related_name='lecons',
        verbose_name="Enseignant"
    )

    # Titre de la leçon saisi par l'enseignant
    titre = models.CharField(
        max_length=255,
        verbose_name="Titre de la leçon"
    )

    # Description courte utilisée par l'IA pour générer le contenu
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Description"
    )

    # Contenu complet généré par l'IA Groq
    contenu = models.TextField(
        blank=True,
        null=True,
        verbose_name="Contenu généré par l'IA"
    )

    # Classe cible de la leçon (CP1 à CM2)
    # Synchronisée avec la classe d'enseignement du professeur
    classe = models.CharField(
        max_length=20,
        choices=Classe.choices,
        verbose_name="Classe cible"
    )

    # Durée estimée de la leçon
    duree = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        default="45 min",
        verbose_name="Durée estimée"
    )

    # Statut de publication (brouillon par défaut)
    statut = models.CharField(
        max_length=20,
        choices=Statut.choices,
        default=Statut.BROUILLON,
        verbose_name="Statut"
    )

    # Thème mathématique de la leçon
    # Utilisé pour catégoriser les scores des exercices
    theme = models.CharField(
        max_length=50,
        choices=Theme.choices,
        verbose_name="Thème mathématique"
    )

    # Date de création (automatique)
    date_creation = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de création"
    )

    # Date de dernière modification (automatique)
    date_modification = models.DateTimeField(
        auto_now=True,
        verbose_name="Dernière modification"
    )

    class Meta:
        verbose_name        = "Leçon"
        verbose_name_plural = "Leçons"
        ordering            = ['-date_creation']

    def __str__(self):
        return f"{self.titre} — {self.classe} ({self.statut})"

    @property
    def nombre_exercices(self):
        """Retourne le nombre d'exercices liés à cette leçon."""
        return self.exercices.count()



# MODÈLE : Exercice

class Exercice(models.Model):
    """
    Exercice QCM lié à une leçon.
    L'élève voit la question et les choix, pas la bonne réponse.
    L'enseignant voit tout depuis son tableau de bord.
    """

    # La leçon parente
    # Si la leçon est supprimée, les exercices le sont aussi
    lecon = models.ForeignKey(
        Lecon,
        on_delete=models.CASCADE,
        related_name='exercices',
        verbose_name="Leçon parente"
    )

    # La question posée à l'élève
    question = models.TextField(
        verbose_name="Question"
    )

    # La bonne réponse (visible uniquement par l'enseignant)
    reponse_correcte = models.CharField(
        max_length=255,
        verbose_name="Bonne réponse"
    )

    # Les mauvaises réponses séparées par des virgules
    # Ex : "12, 15, 8"
    mauvaises_reponses = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Séparez les mauvaises réponses par des virgules",
        verbose_name="Mauvaises réponses"
    )

    # Explication affichée après que l'élève ait répondu
    explication = models.TextField(
        blank=True,
        null=True,
        verbose_name="Explication"
    )

    # Ordre d'affichage dans la leçon
    ordre = models.PositiveIntegerField(
        default=0,
        verbose_name="Ordre d'affichage"
    )

    # Date de création (automatique)
    date_creation = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de création"
    )

    class Meta:
        verbose_name        = "Exercice"
        verbose_name_plural = "Exercices"
        ordering            = ['ordre', 'date_creation']

    def __str__(self):
        return f"Exercice {self.ordre} — {self.lecon.titre}"



# MODÈLE : EvenementCalendrier

class EvenementCalendrier(models.Model):
    """
    Événement du calendrier de l'enseignant.
    Permet à l'enseignant de planifier ses cours,
    réunions et autres activités.
    """

    class TypeEvenement(models.TextChoices):
        """
        Types d'événements disponibles dans le calendrier.
        """
        COURS   = 'cours',   'Cours'
        REUNION = 'reunion', 'Réunion'
        AUTRE   = 'autre',   'Autre'

    # L'enseignant propriétaire de l'événement
    enseignant = models.ForeignKey(
        Enseignant,
        on_delete=models.CASCADE,
        related_name='evenements',
        verbose_name="Enseignant"
    )

    # Titre de l'événement
    titre = models.CharField(
        max_length=255,
        verbose_name="Titre"
    )

    # Type de l'événement (cours, réunion, autre)
    type_evenement = models.CharField(
        max_length=50,
        choices=TypeEvenement.choices,
        default=TypeEvenement.COURS,
        verbose_name="Type d'événement"
    )

    # Date de l'événement
    date = models.DateField(
        verbose_name="Date"
    )

    # Heure de l'événement
    heure = models.TimeField(
        verbose_name="Heure"
    )

    # Leçon liée à cet événement (optionnel)
    # Si la leçon est supprimée, le lien est mis à NULL
    lecon = models.ForeignKey(
        Lecon,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='evenements',
        verbose_name="Leçon liée"
    )

    class Meta:
        verbose_name        = "Événement du calendrier"
        verbose_name_plural = "Événements du calendrier"
        ordering            = ['date', 'heure']

    def __str__(self):
        return f"{self.titre} — {self.date} à {self.heure}"
