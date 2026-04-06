"""Build helper for PFPADEL Windows executables."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def check_pyinstaller() -> bool:
    """Return True when PyInstaller is available."""
    try:
        import PyInstaller  # noqa: F401

        return True
    except ImportError:
        return False


def install_pyinstaller() -> None:
    """Install PyInstaller in the current interpreter."""
    print("[INFO] Installation de PyInstaller...")
    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)


def ensure_ffmpeg() -> None:
    """Download FFmpeg when a video build needs it."""
    ffmpeg_path = Path("ffmpeg/ffmpeg.exe")
    if ffmpeg_path.exists():
        return

    print("[WARN] FFmpeg non trouve, telechargement...")
    import download_ffmpeg

    download_ffmpeg.download_ffmpeg()


def build_executable() -> None:
    """Create the requested executable with PyInstaller."""
    print("\n[BUILD] Creation de l'executable PFPADEL...")

    if not check_pyinstaller():
        install_pyinstaller()

    args = {arg.strip().lower() for arg in sys.argv[1:]}
    lite_mode = bool(args.intersection({"--lite", "--portable-lite"}))
    portable_simple_mode = bool(args.intersection({"--portable-simple", "--simple", "--simple-portable"}))
    portable_video_simple_mode = bool(args.intersection({"--portable-video-simple", "--video-simple"}))
    debug_console = bool(args.intersection({"--debug", "--debug-console"}))

    if not portable_simple_mode and not portable_video_simple_mode:
        ensure_ffmpeg()

    if portable_video_simple_mode:
        spec_file = "PFPADEL_portable_video_simple.spec"
        description = "portable video simple"
    elif portable_simple_mode:
        spec_file = "PFPADEL_portable_simple.spec"
        description = "portable simple"
    elif lite_mode:
        spec_file = "PFPADEL_lite.spec"
        description = "lite"
    elif debug_console:
        spec_file = "PFPADEL_debug.spec"
        description = "debug"
    else:
        spec_file = "PFPADEL.spec"
        description = "standard"

    spec_path = Path(spec_file)
    if not spec_path.exists():
        raise FileNotFoundError(f"Fichier spec introuvable: {spec_file}")

    print(f"[INFO] Utilisation de {spec_file} ({description})...")
    subprocess.run([sys.executable, "-m", "PyInstaller", spec_file], check=True)

    print("\n[OK] Build termine.")
    if portable_video_simple_mode:
        print("Executable : dist/PFPADEL_Portable_Video_Simple.exe")
        print("Mode : lecteur video + saisie minimale")
    elif portable_simple_mode:
        print("Executable : dist/PFPADEL_Portable_Simple.exe")
        print("Mode : saisie manuelle, sans video ni vocal")
    elif lite_mode:
        print("Executable : dist/NanoApp_Stat_Lite.exe")
        print("Mode : lite")
    elif debug_console:
        print("Executable : dist/NanoApp_Stat_Debug.exe")
        print("Mode : debug console")
    else:
        print("Executable : dist/NanoApp_Stat.exe")
        print("Mode : standard")


if __name__ == "__main__":
    try:
        build_executable()
    except Exception as exc:
        print(f"\n[ERROR] {exc}")
        sys.exit(1)
