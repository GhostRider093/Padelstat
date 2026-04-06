"""
Script pour télécharger FFmpeg automatiquement
"""
import os
import sys
import urllib.request
import zipfile
import shutil
from pathlib import Path

FFMPEG_VERSION = "7.1"
FFMPEG_URL = f"https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-n{FFMPEG_VERSION}-latest-win64-gpl-shared-{FFMPEG_VERSION}.zip"
# URL alternative plus stable
FFMPEG_URL_ESSENTIALS = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

def download_ffmpeg():
    """Télécharge et extrait FFmpeg dans le dossier ffmpeg/"""
    ffmpeg_dir = Path(__file__).parent / "ffmpeg"
    ffmpeg_exe = ffmpeg_dir / "ffmpeg.exe"
    
    # Vérifier si FFmpeg existe déjà
    if ffmpeg_exe.exists():
        print(f"✅ FFmpeg déjà présent : {ffmpeg_exe}")
        return str(ffmpeg_exe)
    
    print("📥 Téléchargement de FFmpeg...")
    zip_path = ffmpeg_dir / "ffmpeg.zip"
    
    try:
        # Téléchargement avec barre de progression
        def show_progress(block_num, block_size, total_size):
            downloaded = block_num * block_size
            percent = min(downloaded * 100 / total_size, 100)
            sys.stdout.write(f"\r  Téléchargement... {percent:.1f}%")
            sys.stdout.flush()
        
        urllib.request.urlretrieve(FFMPEG_URL_ESSENTIALS, zip_path, show_progress)
        print("\n✅ Téléchargement terminé")
        
        # Extraction
        print("📦 Extraction...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Trouver le dossier bin dans l'archive
            for file_info in zip_ref.namelist():
                if file_info.endswith('bin/ffmpeg.exe'):
                    # Extraire uniquement ffmpeg.exe
                    source = zip_ref.open(file_info)
                    target = open(ffmpeg_exe, 'wb')
                    with source, target:
                        shutil.copyfileobj(source, target)
                    break
        
        # Nettoyage
        zip_path.unlink()
        print(f"✅ FFmpeg installé : {ffmpeg_exe}")
        return str(ffmpeg_exe)
        
    except Exception as e:
        print(f"❌ Erreur lors du téléchargement : {e}")
        print("\n🔧 Solution manuelle :")
        print("1. Téléchargez FFmpeg depuis : https://www.gyan.dev/ffmpeg/builds/")
        print("2. Extrayez ffmpeg.exe dans le dossier : ffmpeg/")
        return None

if __name__ == "__main__":
    result = download_ffmpeg()
    if result:
        print("\n✅ Installation réussie !")
    else:
        print("\n❌ Installation échouée")
        sys.exit(1)
