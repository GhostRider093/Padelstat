"""Create portable PFPADEL packages."""

from __future__ import annotations

import os
import shutil
import struct
import sys
import sysconfig
import zipfile
from pathlib import Path


def _expected_dll_architecture() -> str:
    """Return the expected DLL architecture for the current Python process."""
    return "64-bit" if sys.maxsize > 2**32 else "32-bit"


def _read_pe_machine(dll_path: Path) -> int | None:
    """Read the PE Machine field of a Windows DLL."""
    try:
        with dll_path.open("rb") as fh:
            if fh.read(2) != b"MZ":
                return None
            fh.seek(0x3C)
            pe_offset = struct.unpack("<I", fh.read(4))[0]
            fh.seek(pe_offset)
            if fh.read(4) != b"PE\x00\x00":
                return None
            return struct.unpack("<H", fh.read(2))[0]
    except Exception:
        return None


def _dll_architecture(dll_path: Path) -> str | None:
    """Return a human-readable architecture from a PE DLL."""
    machine = _read_pe_machine(dll_path)
    if machine == 0x14C:
        return "32-bit"
    if machine == 0x8664:
        return "64-bit"
    return None


def find_vlc_runtime_dir() -> tuple[Path | None, str | None]:
    """Return a compatible VLC folder and an optional incompatibility reason."""
    candidates: list[Path] = []
    incompatible_reason: str | None = None

    env_vlc = os.environ.get("VLC_DIR", "").strip()
    if env_vlc:
        candidates.append(Path(env_vlc))

    project_root = Path(__file__).parent.resolve()
    candidates.extend([project_root / "vlc", project_root / "VLC"])

    if os.name == "nt":
        for env_name in ("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432"):
            base = os.environ.get(env_name, "").strip()
            if base:
                candidates.append(Path(base) / "VideoLAN" / "VLC")

    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate).lower()
        if key in seen:
            continue
        seen.add(key)
        dll_path = candidate / "libvlc.dll"
        if not (dll_path.exists() and (candidate / "plugins").exists()):
            continue

        dll_arch = _dll_architecture(dll_path)
        expected_arch = _expected_dll_architecture()
        if dll_arch and dll_arch != expected_arch:
            if incompatible_reason is None:
                incompatible_reason = (
                    f"VLC {dll_arch} détecté dans {candidate}, incompatible avec "
                    f"Python {expected_arch}"
                )
            continue

        return candidate, None
    return None, incompatible_reason


def _copy_python_runtime(portable_dir: Path) -> None:
    python_embed = portable_dir / "python"
    python_embed.mkdir(exist_ok=True)

    version_tag = f"{sys.version_info.major}{sys.version_info.minor}"
    candidate_names = [f"python{version_tag}.dll", "python3.dll"]
    search_dirs: list[Path] = []
    for value in (getattr(sys, "base_prefix", None), getattr(sys, "prefix", None)):
        if value:
            search_dirs.append(Path(value))
    search_dirs.append(Path(sys.executable).parent)
    libdir = sysconfig.get_config_var("LIBDIR")
    if libdir:
        search_dirs.append(Path(libdir))

    unique_dirs: list[Path] = []
    seen: set[str] = set()
    for directory in search_dirs:
        key = str(directory).lower()
        if key in seen:
            continue
        seen.add(key)
        unique_dirs.append(directory)

    python_dll: Path | None = None
    for directory in unique_dirs:
        for name in candidate_names:
            candidate = directory / name
            if candidate.exists():
                python_dll = candidate
                break
        if python_dll:
            break

    if python_dll:
        shutil.copy(python_dll, python_embed / python_dll.name)
    else:
        print("[WARN] DLL Python introuvable, dossier python/ laisse vide.")


def _write_readme(portable_dir: Path, simple_mode: bool, video_simple_mode: bool) -> None:
    if video_simple_mode:
        content = """PFPADEL - Package Portable Video Simple
=======================================

Pour lancer l'application:
1. Double-cliquer sur PFPADEL.exe
2. Charger une video
3. Renommer les joueurs si besoin
4. Choisir la stat puis valider avec Entree

Contenu:
- PFPADEL.exe : application video simple
- app/config/ : joueurs par defaut modifiables
- vlc/ : runtime VLC embarque
- data/ : exports et rapports
- assets/ : ressources graphiques

Version video simple:
- tout est dans le dossier
- aucune installation requise
- video + saisie minimale
- rapport HTML simple
"""
    elif simple_mode:
        content = """PFPADEL - Package Portable Simple
=================================

Pour lancer l'application:
1. Double-cliquer sur PFPADEL.exe
2. Saisir les joueurs
3. Remplir les lignes puis exporter en JSON / CSV / HTML

Contenu:
- PFPADEL.exe : application portable simple
- app/config/ : joueurs par defaut modifiables
- data/ : exports et rapports
- assets/ : ressources graphiques

Version portable simple:
- tout est dans le dossier
- aucune installation requise
- pas de video
- pas de commandes vocales
"""
    else:
        content = """PFPADEL - Package Portable
=========================

Pour lancer l'application:
1. Double-cliquer sur PFPADEL.exe
2. L'application s'ouvrira automatiquement

Contenu:
- PFPADEL.exe : application principale
- app/ : modules de l'application
- data/ : dossier pour vos donnees de match
- ffmpeg/ : outils de traitement video
- vlc/ : runtime VLC embarque
- assets/ : ressources graphiques

Version portable - Fonctionne sans installation
"""

    (portable_dir / "README.txt").write_text(content, encoding="utf-8")


def _write_launchers(portable_dir: Path, simple_mode: bool, video_simple_mode: bool, lite_mode: bool) -> None:
    launcher_lines = [
        "@echo off",
        "cd /d %~dp0",
    ]
    if video_simple_mode or not simple_mode:
        launcher_lines.append('set "VLC_DIR=%~dp0vlc"')
    launcher_lines.append('start "" /b PFPADEL.exe')
    (portable_dir / "LANCER_PFPADEL.bat").write_text("\r\n".join(launcher_lines) + "\r\n", encoding="utf-8")

    debug_exe = portable_dir / "PFPADEL_Debug.exe"
    if simple_mode or video_simple_mode or lite_mode or not debug_exe.exists():
        return

    (portable_dir / "LANCER_DEBUG.bat").write_text(
        "@echo off\r\n"
        "cd /d %~dp0\r\n"
        'set "VLC_DIR=%~dp0vlc"\r\n'
        "echo Lancement en mode debug...\r\n"
        "PFPADEL_Debug.exe\r\n"
        "echo.\r\n"
        "echo Code retour: %ERRORLEVEL%\r\n"
        "pause\r\n",
        encoding="utf-8",
    )


def create_portable_package(
    lite_mode: bool = False,
    simple_mode: bool = False,
    video_simple_mode: bool = False,
) -> None:
    """Create a portable package directory and ZIP archive."""
    if video_simple_mode:
        mode_label = "VIDEO SIMPLE"
        portable_dir = Path("dist/PFPADEL_Portable_Video_Simple")
        source_exe = Path("dist/PFPADEL_Portable_Video_Simple.exe")
        zip_path = Path("dist/PFPADEL_Portable_Video_Simple.zip")
    elif simple_mode:
        mode_label = "SIMPLE"
        portable_dir = Path("dist/PFPADEL_Portable_Simple")
        source_exe = Path("dist/PFPADEL_Portable_Simple.exe")
        zip_path = Path("dist/PFPADEL_Portable_Simple.zip")
    elif lite_mode:
        mode_label = "LITE"
        portable_dir = Path("dist/PFPADEL_Portable_Lite")
        source_exe = Path("dist/NanoApp_Stat_Lite.exe")
        zip_path = Path("dist/PFPADEL_Portable_Lite.zip")
    else:
        mode_label = "STANDARD"
        portable_dir = Path("dist/PFPADEL_Portable")
        source_exe = Path("dist/NanoApp_Stat.exe")
        zip_path = Path("dist/PFPADEL_Portable.zip")

    print(f"\n[BUILD] Creation du package portable PFPADEL ({mode_label})...")
    if portable_dir.exists():
        shutil.rmtree(portable_dir)
    portable_dir.mkdir(parents=True)

    print("[1/5] Copie de l'application...")
    if not source_exe.exists():
        raise FileNotFoundError(f"Executable introuvable: {source_exe}")
    shutil.copy(source_exe, portable_dir / "PFPADEL.exe")

    if not lite_mode and not simple_mode and not video_simple_mode:
        debug_exe = Path("dist/NanoApp_Stat_Debug.exe")
        if debug_exe.exists():
            shutil.copy(debug_exe, portable_dir / "PFPADEL_Debug.exe")

    if simple_mode or video_simple_mode:
        config_src = Path("app/config")
        if config_src.exists():
            (portable_dir / "app").mkdir(exist_ok=True)
            shutil.copytree(config_src, portable_dir / "app" / "config")
    else:
        dist_app = Path("dist/app")
        if dist_app.exists():
            shutil.copytree(dist_app, portable_dir / "app")

    for relative in ("data", "data/exports", "data/reports", "data/backups"):
        (portable_dir / relative).mkdir(parents=True, exist_ok=True)

    if simple_mode or video_simple_mode:
        print("[2/5] Mode simple: pas de FFmpeg a copier.")
    else:
        print("[2/5] Copie de FFmpeg...")
        ffmpeg_src = Path("ffmpeg")
        if ffmpeg_src.exists():
            shutil.copytree(ffmpeg_src, portable_dir / "ffmpeg")

    if simple_mode:
        print("[3/5] Mode simple: pas de VLC ni runtime Python externe.")
    elif video_simple_mode:
        print("[3/5] Mode video simple: copie du runtime VLC uniquement.")
        vlc_src, vlc_issue = find_vlc_runtime_dir()
        if vlc_src:
            shutil.copytree(
                vlc_src,
                portable_dir / "vlc",
                ignore=shutil.ignore_patterns("cache", "lua", "sdk", "skins"),
            )
            print(f"[OK] VLC copie depuis: {vlc_src}")
        else:
            raise RuntimeError(
                vlc_issue or "Runtime VLC compatible introuvable. Installez un VLC de meme architecture que Python."
            )
    else:
        print("[2b/5] Copie du runtime VLC...")
        vlc_src, vlc_issue = find_vlc_runtime_dir()
        if vlc_src:
            shutil.copytree(
                vlc_src,
                portable_dir / "vlc",
                ignore=shutil.ignore_patterns("cache", "lua", "sdk", "skins"),
            )
            print(f"[OK] VLC copie depuis: {vlc_src}")
        else:
            raise RuntimeError(
                vlc_issue or "Runtime VLC compatible introuvable. Installez un VLC de meme architecture que Python."
            )

        print("[3/5] Ajout du runtime Python...")
        _copy_python_runtime(portable_dir)

    print("[4/5] Copie des assets...")
    assets_src = Path("assets")
    if assets_src.exists():
        shutil.copytree(assets_src, portable_dir / "assets")

    _write_readme(portable_dir, simple_mode=simple_mode, video_simple_mode=video_simple_mode)
    _write_launchers(
        portable_dir,
        simple_mode=simple_mode,
        video_simple_mode=video_simple_mode,
        lite_mode=lite_mode,
    )

    print("[5/5] Creation de l'archive ZIP...")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _dirs, files in os.walk(portable_dir):
            for filename in files:
                file_path = Path(root) / filename
                arcname = file_path.relative_to(portable_dir.parent)
                zipf.write(file_path, arcname)

    print("\n[OK] Package portable cree.")
    print(f"Dossier : {portable_dir}")
    print(f"Archive : {zip_path}")
    print(f"Copiez le dossier '{portable_dir.name}' ou l'archive ZIP sur l'autre PC.")


if __name__ == "__main__":
    args = {arg.strip().lower() for arg in sys.argv[1:]}
    lite_mode = bool(args.intersection({"--lite", "--portable-lite"}))
    simple_mode = bool(args.intersection({"--portable-simple", "--simple", "--simple-portable"}))
    video_simple_mode = bool(args.intersection({"--portable-video-simple", "--video-simple"}))
    create_portable_package(
        lite_mode=lite_mode,
        simple_mode=simple_mode,
        video_simple_mode=video_simple_mode,
    )
