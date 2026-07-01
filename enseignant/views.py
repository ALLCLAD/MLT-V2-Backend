from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.db.models import Avg, Count, ExpressionWrapper, FloatField, F, Sum
from django.utils import timezone
from datetime import timedelta, date
from django.http import HttpResponse
from Uauth.models import Enfant, SuiviEnseignantEnfant
from .models import Lecon, Exercice, EvenementCalendrier
from .serializers import (RechercheEleveSerializer,EleveEnseignantSerializer,LeconCreateSerializer,LeconListSerializer,LeconDetailSerializer,ExerciceSerializer,EvenementCalendrierSerializer,)
from mlt_quiz.models import ScoreQuiz, ThemeQuiz
import io
import re


# VUE : GESTION DES ÉLÈVES (Ajout / Suppression)
# Note : Dépendances d'importation (docx, pypdf, reportlab) installées avec succès.


class RechercheEleveView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        # Vérification du rôle
        if request.user.role != 'ENSEIGNANT':
            return Response({"error": "Action non autorisée."}, status=status.HTTP_403_FORBIDDEN)
            
        query = request.GET.get('q', '')
        enseignant = request.user.profil_enseignant
        classe_enseignant = enseignant.classe_enseignement
        
        # Filtre les élèves n'appartenant pas encore à sa classe logicielle
        eleves = Enfant.objects.filter(classe=classe_enseignant)
        deja_ajoutes = SuiviEnseignantEnfant.objects.filter(enseignant=enseignant).values_list('enfant_id', flat=True)
        eleves = eleves.exclude(id__in=deja_ajoutes)
        
        if len(query) >= 2:
            from django.db import models as db_models
            eleves = eleves.filter(db_models.Q(utilisateur__first_name__icontains=query) | db_models.Q(utilisateur__last_name__icontains=query) | db_models.Q(utilisateur__username__icontains=query))
        serializer = RechercheEleveSerializer(eleves, many=True)
        return Response(serializer.data)

class EnseignantElevesView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        if request.user.role != 'ENSEIGNANT':
            return Response({"error": "Action non autorisée."}, status=status.HTTP_403_FORBIDDEN)
        eleves = Enfant.objects.filter(suivienseignantenfant__enseignant__utilisateur=request.user)
        serializer = EleveEnseignantSerializer(eleves, many=True)
        return Response(serializer.data)

    def post(self, request):
        if request.user.role != 'ENSEIGNANT':
            return Response({"error": "Action non autorisée."}, status=status.HTTP_403_FORBIDDEN)
        eleve_id = request.data.get('eleve_id')
        if not eleve_id:
            return Response({"error": "L'id de l'élève est requis."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            eleve = Enfant.objects.get(id=eleve_id)
        except Enfant.DoesNotExist:
            return Response({"error": "Élève introuvable."}, status=status.HTTP_404_NOT_FOUND)
        enseignant = request.user.profil_enseignant
        if SuiviEnseignantEnfant.objects.filter(enseignant=enseignant, enfant=eleve).exists():
            return Response({"message": "Cet élève est déjà dans votre classe."}, status=status.HTTP_400_BAD_REQUEST)
        SuiviEnseignantEnfant.objects.create(enseignant=enseignant, enfant=eleve)
        return Response({"message": f"{eleve.utilisateur.first_name} {eleve.utilisateur.last_name} a été ajouté à votre classe !"}, status=status.HTTP_201_CREATED)

class SupprimerEleveView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def delete(self, request, eleve_id):
        if request.user.role != 'ENSEIGNANT':
            return Response({"error": "Action non autorisée."}, status=status.HTTP_403_FORBIDDEN)
        try:
            suivi = SuiviEnseignantEnfant.objects.get(enseignant__utilisateur=request.user, enfant_id=eleve_id)
        except SuiviEnseignantEnfant.DoesNotExist:
            return Response({"error": "Élève introuvable dans votre classe."}, status=status.HTTP_404_NOT_FOUND)
        suivi.delete()
        return Response({"message": "Élève retiré de votre classe."}, status=status.HTTP_204_NO_CONTENT)

# VUE : STATISTIQUES GLOBAL POUR L'ENSEIGNANT (TABLEAU DE BORD)

class EnseignantStatsView(APIView):
    """
    Donne le résumé de tout ce qui se passe dans la classe : Liste d'élèves, leçons, moyenne de tout le monde.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        if request.user.role != 'ENSEIGNANT':
            return Response({"error": "Action non autorisée."}, status=status.HTTP_403_FORBIDDEN)
            
        enseignant = request.user.profil_enseignant
        eleves = Enfant.objects.filter(suivienseignantenfant__enseignant=enseignant)
        eleves_ids = eleves.values_list('id', flat=True)
        scores = ScoreQuiz.objects.filter(enfant_id__in=eleves_ids)
        
        # Moyenne globale de toute la classe
        stats_globales = scores.aggregate(moyenne=Avg(ExpressionWrapper(F('points') * 20.0 / F('total_questions'), output_field=FloatField())))
        moyenne_val = round(stats_globales['moyenne'] or 0, 1)
        
        jours_labels = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
        today = timezone.now().date()
        start_of_week = today - timedelta(days=today.weekday())
        graph_data = []
        
        for i in range(7):
            date_cible = start_of_week + timedelta(days=i)
            entry = {"name": jours_labels[i]}
            for enf in eleves:
                count = scores.filter(enfant=enf, date_realisation=date_cible).count()
                entry[enf.utilisateur.first_name] = count
            graph_data.append(entry)
            
        recent_scores = scores.select_related('enfant__utilisateur').order_by('-date_realisation', '-id')[:5]
        recent_activity = [{"prenom": s.enfant.utilisateur.first_name, "theme": s.get_theme_display(), "score": round((s.points / s.total_questions) * 20, 1), "date": s.date_realisation} for s in recent_scores]
        
        return Response({
            "totalEleves": eleves.count(),
            "totalLecons": Lecon.objects.filter(enseignant=enseignant).count(),
            "totalExercices": Exercice.objects.filter(lecon__enseignant=enseignant).count(),
            "moyenneGenerale": moyenne_val,
            "graphData": graph_data,
            "recentActivity": recent_activity
        }, status=status.HTTP_200_OK)



# VUE : GESTION DES LEÇONS ET EXERCICES

class LeconView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        if request.user.role != 'ENSEIGNANT': return Response({"error": "Action non autorisée."}, status=status.HTTP_403_FORBIDDEN)
        lecons = Lecon.objects.filter(enseignant__utilisateur=request.user).order_by('-date_creation')
        serializer = LeconListSerializer(lecons, many=True)
        return Response(serializer.data)
        
    def post(self, request):
        if request.user.role != 'ENSEIGNANT': return Response({"error": "Action non autorisée."}, status=status.HTTP_403_FORBIDDEN)
        serializer = LeconCreateSerializer(data=request.data)
        if serializer.is_valid():
            lecon = serializer.save(enseignant=request.user.profil_enseignant)
            return Response({"message": "Leçon créée avec succès !", "id": lecon.id}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LeconDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def _get_lecon(self, request, lecon_id):
        try: return Lecon.objects.get(id=lecon_id, enseignant__utilisateur=request.user)
        except Lecon.DoesNotExist: return None
        
    def get(self, request, lecon_id):
        lecon = self._get_lecon(request, lecon_id)
        if not lecon: return Response({"error": "Leçon introuvable."}, status=status.HTTP_404_NOT_FOUND)
        return Response(LeconDetailSerializer(lecon).data)
        
    def patch(self, request, lecon_id):
        lecon = self._get_lecon(request, lecon_id)
        if not lecon: return Response({"error": "Leçon introuvable."}, status=status.HTTP_404_NOT_FOUND)
        serializer = LeconListSerializer(lecon, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    def delete(self, request, lecon_id):
        lecon = self._get_lecon(request, lecon_id)
        if not lecon: return Response({"error": "Leçon introuvable."}, status=status.HTTP_404_NOT_FOUND)
        lecon.delete()
        return Response({"message": "Leçon supprimée."}, status=status.HTTP_204_NO_CONTENT)

class ExerciceView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def _get_lecon(self, request, lecon_id):
        try: return Lecon.objects.get(id=lecon_id, enseignant__utilisateur=request.user)
        except Lecon.DoesNotExist: return None
    def get(self, request, lecon_id):
        lecon = self._get_lecon(request, lecon_id)
        if not lecon: return Response({"error": "Leçon introuvable."}, status=status.HTTP_404_NOT_FOUND)
        exercices = Exercice.objects.filter(lecon=lecon)
        serializer = ExerciceSerializer(exercices, many=True)
        return Response(serializer.data)
    def post(self, request, lecon_id):
        lecon = self._get_lecon(request, lecon_id)
        if not lecon: return Response({"error": "Leçon introuvable."}, status=status.HTTP_404_NOT_FOUND)
        serializer = ExerciceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(lecon=lecon)
            return Response({"message": "Exercice ajouté !"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ExerciceDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def delete(self, request, exercice_id):
        try: exercice = Exercice.objects.get(id=exercice_id, lecon__enseignant__utilisateur=request.user)
        except Exercice.DoesNotExist: return Response({"error": "Exercice introuvable."}, status=status.HTTP_404_NOT_FOUND)
        exercice.delete()
        return Response({"message": "Exercice supprimé."}, status=status.HTTP_204_NO_CONTENT)


# VUE : EXTRACTION DE TEXTE DEPUIS UN PDF OU WORD

class ExtraireTexteView(APIView):
    """
    Reçoit un fichier PDF ou DOCX en multipart/form-data.
    Extrait le texte brut et le retourne en JSON.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.role != 'ENSEIGNANT':
            return Response({"error": "Action non autorisée."}, status=status.HTTP_403_FORBIDDEN)

        fichier = request.FILES.get('fichier')
        if not fichier:
            return Response({"error": "Aucun fichier fourni."}, status=status.HTTP_400_BAD_REQUEST)

        nom = fichier.name.lower()
        texte = ""

        try:
            if nom.endswith('.pdf'):
                from pypdf import PdfReader
                reader = PdfReader(fichier)
                pages = []
                for page in reader.pages:
                    t = page.extract_text()
                    if t:
                        pages.append(t.strip())
                texte = "\n\n".join(pages)

            elif nom.endswith('.docx') or nom.endswith('.doc'):
                import docx
                doc = docx.Document(fichier)
                paragraphes = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
                texte = "\n\n".join(paragraphes)

            else:
                return Response({"error": "Format non supporté. Utilisez PDF ou DOCX."}, status=status.HTTP_400_BAD_REQUEST)

            if not texte.strip():
                return Response({"error": "Impossible d'extraire du texte de ce fichier."}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

            # Nettoyer le texte (espaces multiples, lignes vides successives)
            texte = re.sub(r'\n{3,}', '\n\n', texte)
            texte = re.sub(r' {2,}', ' ', texte)

            return Response({"texte": texte, "nb_caracteres": len(texte)}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": f"Erreur lors de l'extraction : {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# VUE : TÉLÉCHARGEMENT D'UNE LEÇON EN PDF OU WORD

class TelechargementLeconView(APIView):
    """
    Génère et retourne un fichier PDF ou DOCX du contenu d'une leçon.
    Paramètre URL : format = 'pdf' ou 'docx' (défaut: pdf)
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, lecon_id):
        if request.user.role != 'ENSEIGNANT':
            return Response({"error": "Action non autorisée."}, status=status.HTTP_403_FORBIDDEN)

        try:
            lecon = Lecon.objects.get(id=lecon_id, enseignant__utilisateur=request.user)
        except Lecon.DoesNotExist:
            return Response({"error": "Leçon introuvable."}, status=status.HTTP_404_NOT_FOUND)

        format_export = request.GET.get('format', 'pdf').lower()
        contenu_brut = lecon.contenu or "Aucun contenu disponible."
        # Supprimer la syntaxe Markdown de base pour le texte brut
        contenu_txt = re.sub(r'#{1,6}\s?', '', contenu_brut)
        contenu_txt = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', contenu_txt)
        contenu_txt = re.sub(r'`([^`]+)`', r'\1', contenu_txt)

        nom_fichier = f"{lecon.titre.replace(' ', '_')}_{lecon.classe}"

        if format_export == 'pdf':
            try:
                from reportlab.lib.pagesizes import A4
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.lib.units import cm
                from reportlab.lib import colors
                from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
                from reportlab.lib.enums import TA_LEFT, TA_CENTER

                buffer = io.BytesIO()
                doc = SimpleDocTemplate(
                    buffer,
                    pagesize=A4,
                    rightMargin=2*cm,
                    leftMargin=2*cm,
                    topMargin=2*cm,
                    bottomMargin=2*cm
                )

                styles = getSampleStyleSheet()
                story = []

                # Style titre
                titre_style = ParagraphStyle(
                    'TitreLecon',
                    parent=styles['Title'],
                    fontSize=22,
                    spaceAfter=6,
                    textColor=colors.HexColor('#4F46E5'),
                    fontName='Helvetica-Bold'
                )
                # Style sous-titre
                sous_titre_style = ParagraphStyle(
                    'SousTitre',
                    parent=styles['Normal'],
                    fontSize=10,
                    textColor=colors.HexColor('#6B7280'),
                    spaceAfter=20
                )
                # Style corps
                corps_style = ParagraphStyle(
                    'Corps',
                    parent=styles['Normal'],
                    fontSize=11,
                    leading=18,
                    spaceAfter=8,
                    fontName='Helvetica'
                )
                # Style titre de section
                section_style = ParagraphStyle(
                    'Section',
                    parent=styles['Heading2'],
                    fontSize=13,
                    spaceBefore=14,
                    spaceAfter=6,
                    textColor=colors.HexColor('#1E293B'),
                    fontName='Helvetica-Bold'
                )

                story.append(Paragraph(lecon.titre, titre_style))
                story.append(Paragraph(f"Classe : {lecon.classe}  •  Thème : {lecon.theme}  •  Durée : {lecon.duree or '45 min'}", sous_titre_style))
                story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#E0E7FF'), spaceAfter=16))

                if lecon.description:
                    story.append(Paragraph(f"<i>{lecon.description}</i>", corps_style))
                    story.append(Spacer(1, 10))

                # Parcourir les lignes du contenu
                for ligne in contenu_brut.split('\n'):
                    ligne_stripped = ligne.strip()
                    if not ligne_stripped:
                        story.append(Spacer(1, 6))
                    elif ligne_stripped.startswith('## '):
                        story.append(Paragraph(ligne_stripped[3:], section_style))
                    elif ligne_stripped.startswith('# '):
                        story.append(Paragraph(ligne_stripped[2:], section_style))
                    elif ligne_stripped.startswith('- ') or ligne_stripped.startswith('* '):
                        story.append(Paragraph(f"• {ligne_stripped[2:]}", corps_style))
                    else:
                        # Convertir le gras Markdown en tags ReportLab
                        ligne_formatee = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', ligne_stripped)
                        story.append(Paragraph(ligne_formatee, corps_style))

                doc.build(story)
                buffer.seek(0)

                response = HttpResponse(buffer, content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="{nom_fichier}.pdf"'
                return response

            except Exception as e:
                return Response({"error": f"Erreur génération PDF: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        elif format_export == 'docx':
            try:
                import docx
                from docx.shared import Pt, RGBColor, Cm
                from docx.enum.text import WD_ALIGN_PARAGRAPH

                doc_word = docx.Document()

                # Marges
                for section in doc_word.sections:
                    section.top_margin = Cm(2)
                    section.bottom_margin = Cm(2)
                    section.left_margin = Cm(2.5)
                    section.right_margin = Cm(2.5)

                # Titre
                titre_para = doc_word.add_heading(lecon.titre, level=1)
                titre_para.runs[0].font.color.rgb = RGBColor(0x4F, 0x46, 0xE5)

                # Sous-titre
                sous = doc_word.add_paragraph(f"Classe : {lecon.classe}  •  Thème : {lecon.theme}  •  Durée : {lecon.duree or '45 min'}")
                sous.runs[0].font.size = Pt(10)
                sous.runs[0].font.color.rgb = RGBColor(0x6B, 0x72, 0x80)
                doc_word.add_paragraph()

                if lecon.description:
                    desc_para = doc_word.add_paragraph(lecon.description)
                    desc_para.runs[0].italic = True
                    doc_word.add_paragraph()

                # Parcourir les lignes du contenu
                for ligne in contenu_brut.split('\n'):
                    ligne_stripped = ligne.strip()
                    if not ligne_stripped:
                        doc_word.add_paragraph()
                    elif ligne_stripped.startswith('## ') or ligne_stripped.startswith('# '):
                        niveau = 2 if ligne_stripped.startswith('## ') else 1
                        texte_titre = ligne_stripped.lstrip('#').strip()
                        doc_word.add_heading(texte_titre, level=niveau)
                    elif ligne_stripped.startswith('- ') or ligne_stripped.startswith('* '):
                        p = doc_word.add_paragraph(style='List Bullet')
                        p.add_run(ligne_stripped[2:])
                    else:
                        # Traiter le gras
                        p = doc_word.add_paragraph()
                        parties = re.split(r'(\*\*.+?\*\*)', ligne_stripped)
                        for partie in parties:
                            if partie.startswith('**') and partie.endswith('**'):
                                run = p.add_run(partie[2:-2])
                                run.bold = True
                            else:
                                p.add_run(partie)

                buffer = io.BytesIO()
                doc_word.save(buffer)
                buffer.seek(0)

                response = HttpResponse(
                    buffer,
                    content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                )
                response['Content-Disposition'] = f'attachment; filename="{nom_fichier}.docx"'
                return response

            except Exception as e:
                return Response({"error": f"Erreur génération Word: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        else:
            return Response({"error": "Format non supporté. Utilisez 'pdf' ou 'docx'."}, status=status.HTTP_400_BAD_REQUEST)



class EleveDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request, eleve_id):
        if request.user.role != 'ENSEIGNANT': return Response({"error": "Action non autorisée."}, status=status.HTTP_403_FORBIDDEN)
        try: eleve = Enfant.objects.get(id=eleve_id, suivienseignantenfant__enseignant__utilisateur=request.user)
        except Enfant.DoesNotExist: return Response({"error": "Élève introuvable."}, status=status.HTTP_404_NOT_FOUND)
        serializer = EleveEnseignantSerializer(eleve)
        return Response(serializer.data)

class EleveScoresView(APIView):
    """
    VUE CRITIQUE UNIFIÉE. 
    Retourne exactement la même structure de données statistiques que le composant de parent (`EnfantDetailStatsView`).
    Ceci assure que l'affichage des graphiques est parfait des deux côtés.
    """
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request, eleve_id):
        if request.user.role != 'ENSEIGNANT': return Response({"error": "Action non autorisée."}, status=status.HTTP_403_FORBIDDEN)
        try:
            # Vérifie que l'élève demandé est bien dans la classe de ce prof
            eleve = Enfant.objects.get(id=eleve_id, suivienseignantenfant__enseignant__utilisateur=request.user)
        except Enfant.DoesNotExist:
            return Response({"error": "Élève introuvable."}, status=status.HTTP_404_NOT_FOUND)

        # 1. Barre de progressions
        stats_themes = ScoreQuiz.objects.filter(enfant=eleve).annotate(
            note_sur_20=ExpressionWrapper(F('points') * 20.0 / F('total_questions'), output_field=FloatField())
        ).values('theme').annotate(moyenne=Avg('note_sur_20'), nb_exercices=Count('id'), temps_moyen=Avg('temps'))

        for stat in stats_themes:
            stat['moyenne'] = round(stat['moyenne'], 2)
            stat['temps_moyen'] = round(stat['temps_moyen'] or 0, 1)
            # CORRECTION DE L'ERREUR 500: Lecture du dictionnaire
            stat['theme_label'] = dict(ThemeQuiz.choices).get(stat['theme'], stat['theme'].capitalize())

        # 2. Construction de l'historique de la page
        scores_query = ScoreQuiz.objects.filter(enfant=eleve).order_by('-date_realisation', '-id')
        historique = [{"id": s.id, "theme": s.get_theme_display(), "note": round((s.points / s.total_questions) * 20, 1), "date": s.date_realisation, "points": s.points, "total": s.total_questions} for s in scores_query]
        
        # 3. Graphique: Ligne (Évolution des notes sur 20)
        progression_notes = [{"date": s.date_realisation.strftime("%d/%m"), "note": round((s.points / s.total_questions) * 20, 1), "theme": s.get_theme_display()} for s in reversed(scores_query[:20])]
        
        # 4. Graphique: Zone (Activité hebdomadaire / Nombre de quiz)
        jours_labels = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
        today = timezone.now().date()
        start_of_week = today - timedelta(days=today.weekday())
        progression_exercices = []
        for i in range(7):
            date_cible = start_of_week + timedelta(days=i)
            count = scores_query.filter(date_realisation=date_cible).count()
            progression_exercices.append({"name": jours_labels[i], "count": count})

        return Response({
            "enfant": f"{eleve.utilisateur.first_name} {eleve.utilisateur.last_name}",
            "classe": eleve.classe,
            "stats_par_theme": list(stats_themes),
            "historique": historique,
            "progression_notes": progression_notes,
            "progression_exercices": progression_exercices
        }, status=status.HTTP_200_OK)



# VUE : CALENDRIER ENSEIGNANT

class CalendrierView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        if request.user.role != 'ENSEIGNANT': return Response({"error": "Action non autorisée."}, status=status.HTTP_403_FORBIDDEN)
        evenements = EvenementCalendrier.objects.filter(enseignant__utilisateur=request.user)
        serializer = EvenementCalendrierSerializer(evenements, many=True)
        return Response(serializer.data)
    def post(self, request):
        if request.user.role != 'ENSEIGNANT': return Response({"error": "Action non autorisée."}, status=status.HTTP_403_FORBIDDEN)
        serializer = EvenementCalendrierSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(enseignant=request.user.profil_enseignant)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CalendrierDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def delete(self, request, evenement_id):
        if request.user.role != 'ENSEIGNANT': return Response({"error": "Action non autorisée."}, status=status.HTTP_403_FORBIDDEN)
        try: evenement = EvenementCalendrier.objects.get(id=evenement_id, enseignant__utilisateur=request.user)
        except EvenementCalendrier.DoesNotExist: return Response({"error": "Événement introuvable."}, status=status.HTTP_404_NOT_FOUND)
        evenement.delete()
        return Response({"message": "Événement supprimé."}, status=status.HTTP_204_NO_CONTENT)


# VUE : EnfantLeconsView

class EnfantLeconsView(APIView):
    """
    Vue pour qu'un enfant puisse voir les leçons
    publiées par son enseignant.
    Filtre : statut = 'publie' + enseignant lié via SuiviEnseignantEnfant.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):

        if request.user.role != 'ENFANT':
            return Response(
                {"error": "Action non autorisée."},
                status=status.HTTP_403_FORBIDDEN
            )


        # Leçons publiées des enseignants liés à cet enfant
        lecons = Lecon.objects.filter(
            enseignant__eleves__utilisateur=request.user,
            statut='publie'
        ).order_by('-date_creation')

        serializer = LeconListSerializer(lecons, many=True)
        return Response(serializer.data)

# VUE : EnfantLeconDetailView

class EnfantLeconDetailView(APIView):
    """
    Vue pour qu'un enfant puisse voir le détail d'une leçon publiée.
    Vérifie que la leçon appartient bien à son enseignant.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, lecon_id):

        if request.user.role != 'ENFANT':
            return Response(
                {"error": "Action non autorisée."},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            lecon = Lecon.objects.get(
                id=lecon_id,
                enseignant__eleves__utilisateur=request.user,
                statut='publie'
            )
        except Lecon.DoesNotExist:
            return Response(
                {"error": "Leçon introuvable."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = LeconDetailSerializer(lecon)
        return Response(serializer.data)


# VUE : EnfantExercicesView

class EnfantExercicesView(APIView):
    """
    Vue pour qu'un enfant puisse accéder aux exercices
    d'une leçon publiée par son enseignant.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, lecon_id):

        if request.user.role != 'ENFANT':
            return Response(
                {"error": "Action non autorisée."},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            lecon = Lecon.objects.get(
                id=lecon_id,
                enseignant__eleves__utilisateur=request.user,
                statut='publie'
            )
        except Lecon.DoesNotExist:
            return Response(
                {"error": "Leçon introuvable."},
                status=status.HTTP_404_NOT_FOUND
            )

        exercices = Exercice.objects.filter(lecon=lecon)
        serializer = ExerciceSerializer(exercices, many=True)
        return Response(serializer.data)

