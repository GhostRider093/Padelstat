"""
Découpage et sauvegarde de segments vidéo
"""

import os
import sys
import subprocess
import urllib.request
import zipfile
import shutil
from pathlib import Path
from datetime import datetime


class VideoCutter:
    def __init__(self):
        """Initialise le VideoCutter et télécharge FFmpeg si nécessaire"""
        self.ffmpeg_path = self._find_ffmpeg()
        
        # Vérifier et télécharger si nécessaire
        if not self.check_ffmpeg():
            print("⚠️ FFmpeg non trouvé, téléchargement automatique...")
            self._download_ffmpeg()
            self.ffmpeg_path = self._find_ffmpeg()
    
    def _find_ffmpeg(self):
        """Trouve l'exécutable FFmpeg"""
        # Chercher d'abord dans le dossier ffmpeg/ du projet
        project_ffmpeg = Path(__file__).parent.parent.parent / "ffmpeg" / "ffmpeg.exe"
        if project_ffmpeg.exists():
            return str(project_ffmpeg)
        
        # Sinon utiliser FFmpeg du système (PATH)
        return "ffmpeg"
    
    def _download_ffmpeg(self):
        """Télécharge FFmpeg automatiquement"""
        ffmpeg_dir = Path(__file__).parent.parent.parent / "ffmpeg"
        ffmpeg_dir.mkdir(exist_ok=True)
        ffmpeg_exe = ffmpeg_dir / "ffmpeg.exe"
        
        if ffmpeg_exe.exists():
            return
        
        FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
        zip_path = ffmpeg_dir / "ffmpeg.zip"
        
        try:
            print("📥 Téléchargement de FFmpeg (~90 MB)...")
            
            def show_progress(block_num, block_size, total_size):
                downloaded = block_num * block_size
                percent = min(downloaded * 100 / total_size, 100) if total_size > 0 else 0
                sys.stdout.write(f"\r  Téléchargement... {percent:.1f}%")
                sys.stdout.flush()
            
            urllib.request.urlretrieve(FFMPEG_URL, zip_path, show_progress)
            print("\n✅ Téléchargement terminé")
            
            print("📦 Extraction de ffmpeg.exe...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                for file_info in zip_ref.namelist():
                    if file_info.endswith('bin/ffmpeg.exe'):
                        source = zip_ref.open(file_info)
                        target = open(ffmpeg_exe, 'wb')
                        with source, target:
                            shutil.copyfileobj(source, target)
                        break
            
            zip_path.unlink()
            print(f"✅ FFmpeg installé : {ffmpeg_exe}")
            
        except Exception as e:
            print(f"❌ Erreur téléchargement FFmpeg : {e}")
            print("\n🔧 Solution manuelle :")
            print("1. Téléchargez FFmpeg : https://www.gyan.dev/ffmpeg/builds/")
            print("2. Extrayez ffmpeg.exe dans : ffmpeg/")
    
    def check_ffmpeg(self):
        """Vérifie si ffmpeg est disponible"""
        try:
            result = subprocess.run(
                [self.ffmpeg_path, "-version"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def cut_video(self, input_video, start_time, end_time, output_folder="data/clips"):
        """
        Découpe un segment de vidéo
        
        Args:
            input_video: Chemin de la vidéo source
            start_time: Temps de début en secondes
            end_time: Temps de fin en secondes
            output_folder: Dossier de destination
        
        Returns:
            str: Chemin du clip créé
        """
        if not self.check_ffmpeg():
            raise Exception("FFmpeg n'est pas installé ou introuvable")
        
        # Créer le dossier de sortie
        os.makedirs(output_folder, exist_ok=True)
        
        # Générer le nom du fichier
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        duration = end_time - start_time
        output_file = os.path.join(
            output_folder,
            f"clip_{timestamp}_{int(start_time)}s_{int(duration)}s.mp4"
        )
        
        # Commande ffmpeg pour découper sans réencodage (rapide)
        cmd = [
            self.ffmpeg_path,
            "-i", input_video,
            "-ss", str(start_time),
            "-t", str(duration),
            "-c", "copy",  # Copie sans réencodage
            "-y",  # Overwrite si existe
            output_file
        ]
        
        # Exécuter la commande
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            # Si erreur avec copy, réessayer avec réencodage
            cmd = [
                self.ffmpeg_path,
                "-i", input_video,
                "-ss", str(start_time),
                "-t", str(duration),
                "-c:v", "libx264",
                "-c:a", "aac",
                "-y",
                output_file
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"Erreur ffmpeg: {result.stderr}")
        
        return output_file
    
    def get_relative_path(self, absolute_path, base_folder="data"):
        """Convertit un chemin absolu en relatif pour HTML"""
        try:
            abs_path = os.path.abspath(absolute_path)
            base_path = os.path.abspath(base_folder)
            return os.path.relpath(abs_path, base_path)
        except:
            return absolute_path
