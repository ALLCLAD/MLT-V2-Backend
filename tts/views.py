import subprocess
import tempfile
import os

from django.conf import settings
from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .math_preprocessor import preprocess_math_text


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def synthesize_speech(request):
    """
    Reçoit un texte, le pré-traite (symboles math → mots),
    puis le convertit en audio WAV via Piper TTS.

    Body JSON attendu :
        { "text": "Combien font 3 × 4 ?" }

    Retourne : fichier audio WAV (content-type: audio/wav)
    """
    text = request.data.get('text', '').strip()

    if not text:
        return Response(
            {'error': 'Le champ "text" est requis.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Limite de sécurité (éviter les abus)
    if len(text) > 1000:
        return Response(
            {'error': 'Le texte est trop long (max 1000 caractères).'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 1. Pré-traiter le texte mathématique
    processed_text = preprocess_math_text(text)

    output_path = None
    try:
        # 2. Créer un fichier temporaire pour la sortie audio
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            output_path = tmp_file.name

        # 3. Appeler Piper en ligne de commande (en binaire UTF-8 pour éviter les erreurs d'encodage CP1252 sur Windows)
        process = subprocess.run(
            [
                settings.PIPER_EXECUTABLE,
                '--model', settings.PIPER_MODEL,
                '--output_file', output_path,
                '--length_scale', '1.15',  # Rend la voix légèrement plus lente et articulée pour les enfants
                '--noise_scale', '0.75',   # Augmente la variation de ton pour la rendre plus expressive / vivante
                '--noise_w', '0.85',       # Augmente la variation de rythme pour la rendre plus humaine
            ],
            input=processed_text.encode('utf-8'),
            capture_output=True,
            timeout=15,  # 15 secondes suffisent amplement
        )

        if process.returncode != 0:
            stderr_msg = process.stderr.decode('utf-8', errors='ignore')
            return Response(
                {'error': f'Erreur Piper: {stderr_msg}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 4. Lire le fichier audio et le retourner
        with open(output_path, 'rb') as audio_file:
            audio_data = audio_file.read()

        response = HttpResponse(audio_data, content_type='audio/wav')
        response['Content-Disposition'] = 'inline; filename="speech.wav"'
        return response

    except subprocess.TimeoutExpired:
        return Response(
            {'error': 'Le TTS a pris trop de temps.'},
            status=status.HTTP_504_GATEWAY_TIMEOUT
        )
    except FileNotFoundError:
        return Response(
            {'error': 'Piper TTS introuvable. Vérifiez PIPER_EXECUTABLE dans settings.py.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as e:
        return Response(
            {'error': f'Erreur interne: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    finally:
        # 5. Nettoyer le fichier temporaire
        if output_path and os.path.exists(output_path):
            os.remove(output_path)
