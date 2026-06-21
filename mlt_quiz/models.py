from django.db import models

# importation des models Enfant et Classe de Uauth
from Uauth.models import Enfant, Classe

# Model ou classe pour gérer la catégorie ou encore le thème sur lequel porte le quiz
class ThemeQuiz(models.TextChoices):
    """
    Classe pour gérer les catégories ou thèmes d'un quiz à savoir :
    - Calcul : tout ce qui est opérations et calculs
    - Géométrie : tout ce qui est géométrie pour reconnaitre les figures et autres
    - Dénombrement : pour apprendre à compter et autres
    - Grandeurs : un peu des problèmes pour l'application des calculs avec des objets de la vie réelle
    """
    CALCUL = 'CALCUL', 'Calcul et Opérations'
    GEOMETRIE = 'GEOMETRIE', 'Géométrie et Formes'
    DENOMBREMENT = 'DENOMBREMENT', 'Dénombrement et Nombres'
    GRANDEURS = 'GRANDEURS', 'Grandeurs ET Mésures'


# Model ou classe pour le Score du quiz réalisé par l'enfant
class ScoreQuiz(models.Model):
    """
    Stocke les performances d'un enfant pour chaque session de quiz terminée.
    Permet au parent de suivre l'évolution (points et rapidité).
    """

    # liaison avec le model enfant de Uauth via une foreign key
    enfant = models.ForeignKey(Enfant, on_delete=models.CASCADE, related_name='score_quiz')

    # choix pour le thème
    theme = models.CharField(max_length=50, choices=ThemeQuiz.choices)

    # points obtenus après le quiz
    points = models.IntegerField()

    # nombre de questions
    total_questions = models.IntegerField()

    # temps mis par l'enfant pour l'exercice (mésuré par le front react)
    temps = models.IntegerField()

    # la date de realisation du quiz
    date_realisation = models.DateField(auto_now_add=True)

    # classe méta pour la personnalisation
    class Meta:
        verbose_name = 'Score quiz'
        ordering = ['-date_realisation']



    # méthode d'affichage
    def __str__(self):
        return f"{self.enfant.utilisateur.username} - {self.get_theme_display()} ({self.points}/{self.total_questions})"






