from rest_framework import serializers
from .models import ScoreQuiz


class ScoreQuizSerializer(serializers.ModelSerializer):
    """
    Sérialiseur pour valider et enregistrer les résultats d'un quiz.

    Ce sérialiseur fait le lien entre les performances mesurées par React
    et le profil de l'enfant stocké dans la base de données.
    """

    # Champ calculé pour renvoyer le libellé lisible du thème au front
    theme_display = serializers.CharField(source='get_theme_display', read_only=True)

    class Meta:
        model = ScoreQuiz
        fields = [
            'id', 'theme', 'theme_display', 'points',
            'total_questions', 'temps', 'date_realisation'
        ]
        read_only_fields = ['date_realisation']

    def create(self, validated_data):
        """
        Surcharge de la création pour lier automatiquement le score
        à l'enfant qui est actuellement connecté.
        """
        request = self.context.get('request')

        # On récupère le profil enfant via la relation OneToOne définie dans Uauth
        enfant = request.user.profil_enfant

        return ScoreQuiz.objects.create(enfant=enfant, **validated_data)


class StatistiqueParThemeSerializer(serializers.Serializer):
    """
    Sérialiseur pour formater les moyennes par thème (Calcul, Géométrie, etc.)
    """
    theme = serializers.CharField()
    theme_display = serializers.CharField(source='get_theme_display', read_only=True)
    moyenne = serializers.FloatField()
    nb_exercices = serializers.IntegerField()
    temps_moyen = serializers.FloatField()

class RecentActivitySerializer(serializers.Serializer):
    """Petit sérialiseur pour formater chaque ligne d'activité"""
    prenom = serializers.CharField()
    theme = serializers.CharField()
    score = serializers.IntegerField()
    date = serializers.IntegerField()

