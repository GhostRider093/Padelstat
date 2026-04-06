"""
Générateur de voix pour les analyses IA
Utilise Edge-TTS pour une voix naturelle en français
"""

import asyncio
import edge_tts
import pygame
import os
import re
from pathlib import Path


class VoiceGenerator:
    """Génère et lit les analyses avec une voix naturelle"""
    
    def __init__(self, voice="fr-FR-DeniseNeural"):
        """
        Initialise le générateur de voix
        
        Args:
            voice: Voix à utiliser (fr-FR-DeniseNeural par défaut - voix féminine naturelle)
                   Autres options: fr-FR-HenriNeural (masculine)
        """
        self.voice = voice
        self.output_folder = Path("data/audio")
        self.output_folder.mkdir(exist_ok=True)
        
        # Initialiser pygame pour la lecture audio
        pygame.mixer.init()
    
    def clean_html(self, html_text: str) -> str:
        """Nettoie le HTML pour ne garder que le texte"""
        # Supprimer les balises HTML
        text = re.sub(r'<[^>]+>', '', html_text)
        
        # Supprimer les emojis (optionnel - on peut les garder, Edge-TTS les gère)
        # text = re.sub(r'[^\w\s,.!?;:àâäéèêëïîôùûüÿçÀÂÄÉÈÊËÏÎÔÙÛÜŸÇ-]', '', text)
        
        # Nettoyer les espaces multiples
        text = re.sub(r'\s+', ' ', text)
        
        # Nettoyer les caractères spéciaux
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&quot;', '"')
        text = text.replace('&amp;', '&')
        
        return text.strip()
    
    async def generate_audio_async(self, text: str, output_file: str):
        """Génère le fichier audio (async)"""
        communicate = edge_tts.Communicate(text, self.voice)
        await communicate.save(output_file)
    
    def generate_audio(self, text: str, output_file: str = None) -> str:
        """
        Génère un fichier audio à partir du texte
        
        Args:
            text: Texte à convertir (peut contenir du HTML)
            output_file: Chemin du fichier de sortie (optionnel)
            
        Returns:
            Chemin du fichier audio généré
        """
        # Nettoyer le texte
        clean_text = self.clean_html(text)
        
        # Générer un nom de fichier si non fourni
        if output_file is None:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.output_folder / f"analyse_{timestamp}.mp3"
        
        # Générer l'audio
        print("🔊 Génération de l'audio...")
        asyncio.run(self.generate_audio_async(clean_text, str(output_file)))
        print(f"✓ Audio généré: {output_file}")
        
        return str(output_file)
    
    def play_audio(self, audio_file: str):
        """Lit un fichier audio"""
        try:
            print(f"▶️ Lecture de {os.path.basename(audio_file)}...")
            pygame.mixer.music.load(audio_file)
            pygame.mixer.music.play()
            
            # Attendre la fin de la lecture
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            
            print("✓ Lecture terminée")
            
        except Exception as e:
            print(f"❌ Erreur de lecture: {e}")
    
    def generate_and_play(self, text: str) -> str:
        """Génère et lit directement le texte"""
        audio_file = self.generate_audio(text)
        self.play_audio(audio_file)
        return audio_file
    
    def stop(self):
        """Arrête la lecture en cours"""
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
            print("⏹️ Lecture arrêtée")
    
    @staticmethod
    def list_voices():
        """Liste les voix françaises disponibles"""
        print("Voix françaises disponibles:")
        print("  fr-FR-DeniseNeural  (Féminine - naturelle)")
        print("  fr-FR-HenriNeural   (Masculine - naturelle)")
        print("  fr-FR-EloiseNeural  (Féminine - jeune)")
        print("  fr-FR-AlainNeural   (Masculine - grave)")


# Test simple
if __name__ == "__main__":
    # Afficher les voix disponibles
    VoiceGenerator.list_voices()
    
    # Tester avec un texte simple
    print("\n" + "="*60)
    print("TEST DE GÉNÉRATION VOCALE")
    print("="*60)
    
    generator = VoiceGenerator(voice="fr-FR-DeniseNeural")
    
    test_text = """
    <h2>📊 RÉSUMÉ GLOBAL</h2>
    <p>Ce match oppose Arnaud et Fabrice contre Laurent et Alex.</p>
    <p>L'équipe de gauche montre une meilleure efficacité avec 52% de points gagnés.</p>
    
    <h2>🎯 ANALYSE PAR JOUEUR</h2>
    <p>Arnaud est le plus régulier avec 8 points gagnants et seulement 11 fautes directes.</p>
    """
    
    print("Texte à lire:")
    print(test_text)
    print("\n" + "="*60)
    
    # Générer et lire
    audio_file = generator.generate_and_play(test_text)
    print(f"\nFichier sauvegardé: {audio_file}")
