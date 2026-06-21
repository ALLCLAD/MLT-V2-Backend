# importation de post_save
from django.db.models.signals import post_save

# importation de receiver
from django.dispatch import receiver

# importation des models Utilisateur, Enfant, Parent, Enseignant
from .models import Utilisateur, Enfant, Parent, Enseignant


@receiver(post_save, sender=Utilisateur)
def create_user_profile(sender, instance, created, **kwargs):
    """
        On déclenche la création automatique du profil de l'utilisateur, juste
        après sa sauvegarde.
    """
    if created:
        # si l'utilisateur est un enfant
        if instance.role == Utilisateur.Role.ENFANT:
            """
                On crée un profil pour l'enfant, en vérifiant si la classe de l'enfant a été choisi, sinon on lui attribut CP1
                par défaut
            """
            classe_choisie = getattr(instance, 'classe_inscription', 'CP1')
            Enfant.objects.create(utilisateur=instance, classe=classe_choisie)

        # sinon si l'utilisateur est un parent
        elif instance.role == Utilisateur.Role.PARENT:
            """
                On crée un profil pour le parent
            """
            Parent.objects.create(utilisateur=instance)

        # sinon si l'utilisateur est un enseignant
        elif instance.role == Utilisateur.Role.ENSEIGNANT:
            """
                On crée un profil pour l'enseignant, en vérifiant si la classe d'enseignement et son établissement
                sont présent, sinon on lui attribut CP1 pour la classe d'enseignement et non spécifié pour l'établissement
            """
            classe_enseignement = getattr(instance, 'classe_enseignement_inscription', 'CP1')
            etablissement = getattr(instance, 'etablissement_inscription', 'Non spécifié')
            Enseignant.objects.create(
                utilisateur=instance,
                classe_enseignement=classe_enseignement,
                etablissement=etablissement
            )

