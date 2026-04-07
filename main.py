"""
NanoApp Stat - Application principale
Point d'entrée de l'application
"""

import os
import sys


def _configure_runtime_io() -> None:
    """Empêche les sorties console/log de planter sur des caractères Unicode."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(errors="backslashreplace")
            except Exception:
                pass


def _default_log_path():
    from pathlib import Path

    # Demande utilisateur: log à la racine de "Documents"
    # (fallback propre si le dossier n'existe pas / permissions)
    try:
        user_home = Path(os.environ.get("USERPROFILE") or str(Path.home()))
        docs = user_home / "Documents"
        base = docs if docs.exists() else user_home
        return str(base / "NanoAppStat_debug.log")
    except Exception:
        return str(Path(os.getcwd()) / "debug.log")


def _is_safe_mode(argv: list[str]) -> bool:
    # Supporte: --safe
    # + support env: NANOAPPSTAT_SAFE_MODE=1
    flag = any(a.strip().lower() == "--safe" for a in argv)
    env = os.environ.get("NANOAPPSTAT_SAFE_MODE", "").strip().lower() in ("1", "true", "yes", "on")
    return bool(flag or env)


def main():
    import logging
    remote_server = None

    _configure_runtime_io()

    safe_mode = _is_safe_mode(sys.argv[1:])
    if safe_mode:
        # Important: le module UI lit l'env au moment de l'import
        os.environ["NANOAPPSTAT_SAFE_MODE"] = "1"

    logging.basicConfig(
        filename=_default_log_path(),
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        encoding='utf-8',
        errors='backslashreplace',
    )
    logger = logging.getLogger('NanoAppStat')
    logger.info('=== Démarrage NanoApp Stat ===')
    logger.info(f"SAFE_MODE={safe_mode}")
    try:
        import tkinter as tk
        from tkinter import messagebox as tk_messagebox

        # Thème moderne (optionnel) : ttkbootstrap
        # ttkbootstrap.Window reste compatible avec un root Tk classique.
        root = None
        try:
            import ttkbootstrap as tb
            logger.info('Création de la fenêtre ttkbootstrap (thème clair)...')
            # Thèmes clairs populaires: flatly, cosmo, litera, lumen, simplex
            root = tb.Window(themename='flatly')
        except Exception:
            logger.info('ttkbootstrap indisponible, fallback Tkinter...')
            root = tk.Tk()

        # Titre et dimensions de base
        root.title('NanoApp Stat')
        # Maximiser la fenêtre au démarrage
        root.state('zoomed')

        def _report_callback_exception(exc_type, exc_value, exc_traceback):
            logger.error(
                "Exception callback Tkinter",
                exc_info=(exc_type, exc_value, exc_traceback),
            )
            try:
                tk_messagebox.showerror("Erreur", str(exc_value))
            except Exception:
                pass

        root.report_callback_exception = _report_callback_exception

        # Police par défaut un peu plus moderne (impact immédiat sur l'app)
        # Important: ne pas utiliser une chaîne "Segoe UI 10" (Tk la découpe et plante sur "UI").
        try:
            import tkinter.font as tkfont

            preferred_family = "Inter"
            fallback_family = "Segoe UI"
            try:
                families = set(tkfont.families(root))
                font_family = preferred_family if preferred_family in families else fallback_family
                logger.info(f"Police UI: {font_family}")
            except Exception:
                font_family = fallback_family

            for font_name in (
                "TkDefaultFont",
                "TkTextFont",
                "TkMenuFont",
                "TkHeadingFont",
                "TkCaptionFont",
                "TkSmallCaptionFont",
                "TkIconFont",
                "TkTooltipFont",
            ):
                try:
                    f = tkfont.nametofont(font_name)
                    f.configure(family=font_family)
                except Exception:
                    pass

            # Amplifie l'effet sur les widgets Tk qui n'ont pas de font explicite
            try:
                # Tk split sur les espaces; utiliser des accolades pour les familles type "Segoe UI"
                root.option_add("*Font", f"{{{font_family}}} 10")
            except Exception:
                pass
        except Exception:
            pass

        # Charger l'icône si disponible (optionnel)
        try:
            root.iconbitmap("assets/icon.ico")
        except Exception:
            pass
        
        # Lancer l'app
        from app.ui.main_window import MainWindow
        from app.control.remote_control import PadelRemoteControlServer

        app = MainWindow(root, safe_mode=safe_mode)
        remote_server = PadelRemoteControlServer(root, app)
        remote_server.start()
        logger.info('Service local démarré sur localhost:8766')
        logger.info('Entrée dans mainloop')
        root.mainloop()
    except Exception as e:
        logger.error('Erreur au démarrage', exc_info=True)
        # Rester simple: log et quitter proprement
        print('Erreur:', type(e).__name__, str(e))
        sys.exit(1)
    finally:
        if remote_server is not None:
            try:
                remote_server.stop()
            except Exception:
                pass


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Dernier recours: quitter sans interaction bloquante
        sys.exit(1)

