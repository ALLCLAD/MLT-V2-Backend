# Migration générée manuellement : ajout des champs de publication programmée

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('enseignant', '0001_initial'),
    ]

    operations = [
        # Champ sur Lecon : date/heure à laquelle la leçon sera auto-publiée
        migrations.AddField(
            model_name='lecon',
            name='date_publication_programmee',
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name='Publication programmée le'
            ),
        ),

        # Rendre heure optionnel dans EvenementCalendrier
        migrations.AlterField(
            model_name='evenementcalendrier',
            name='heure',
            field=models.TimeField(
                blank=True,
                null=True,
                verbose_name='Heure'
            ),
        ),

        # Champ sur EvenementCalendrier : publier la leçon liée automatiquement
        migrations.AddField(
            model_name='evenementcalendrier',
            name='publier_automatiquement',
            field=models.BooleanField(
                default=False,
                verbose_name='Publier la leçon automatiquement à cet horaire'
            ),
        ),
    ]
