"""Exemple: session vocale continue pour annotation padel.

Inspiré de PADELST_PROMPT_TOTAL_CHAT_VOCAL.md (NanoCode).
Lance l'écoute continue; les commandes sont reconnues et affichées
sans bloquer la boucle principale.

Arrêt: dire "stop écoute" OU Ctrl+C
"""

from __future__ import annotations

import sys
import time
import os

# Ajouter le dossier parent au path si nécessaire
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from padel_voice import PadelVoiceSession, SessionState


# ─────────────────────────────────────────────────────────────────────────────
# Callbacks (votre application mettra ici son propre code)
# ─────────────────────────────────────────────────────────────────────────────

def on_annotation(cmd: dict):
    """✓ Appelé quand une annotation complète est validée."""
    print(f"\n  ✓ ANNOTATION CRÉÉE")
    print(f"    Action      : {cmd.get('action')}")
    print(f"    Joueur      : {cmd.get('joueur')}")
    if cmd.get("defenseur"):
        print(f"    Défenseur   : {cmd.get('defenseur')}")
    print(f"    Type point  : {cmd.get('type_point')}")
    print(f"    Type coup   : {cmd.get('type_coup')}")
    if cmd.get("label"):
        print(f"    Label       : {cmd.get('label')}")
    if cmd.get("zone"):
        print(f"    Zone        : {cmd.get('zone')}")
    if cmd.get("diagonale"):
        print(f"    Diagonale   : {cmd.get('diagonale')}")
    print(f"    Raw text    : {cmd.get('raw_text')}")


def on_status(state: str, message: str):
    """Appelé à chaque changement d'état."""
    icons = {
        "IDLE":                "⏹ ",
        "LISTENING":           "🎤",
        "PROCESSING":          "⚙ ",
        "WAITING_COMPLETION":  "❓",
    }
    icon = icons.get(state, "  ")
    print(f"  {icon} [{state}] {message}")


def on_video_control(command: str):
    """Appelé quand l'utilisateur veut contrôler la vidéo."""
    labels = {
        "pause":  "⏸  PAUSE vidéo",
        "play":   "▶  LECTURE vidéo",
        "retour": "⏮  RETOUR vidéo",
        "avance": "⏭  AVANCE vidéo",
    }
    print(f"\n  {labels.get(command, command)}")


def on_incomplete(partial_cmd: dict, missing_fields: list):
    """Appelé quand la commande est parsée mais incomplète."""
    print(f"\n  ❓ Commande incomplète.")
    print(f"     Champs manquants: {', '.join(missing_fields)}")
    print(f"     (Complétez vocalement ou dites 'annuler')")


def on_error(msg: str):
    print(f"\n  ✗ Erreur: {msg}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("═" * 60)
    print("  SESSION VOCALE PADEL STAT — continue")
    print("  Inspiré de PADELST_PROMPT_TOTAL_CHAT_VOCAL.md")
    print("═" * 60)
    print()
    print("  Joueurs: Arnaud, Pierre, Thomas, Lucas")
    print()
    print("  Commandes exemples:")
    print("    Annot. : «Nouveau point faute directe Arnaud»")
    print("    Annot. : «Point gagnant smash Pierre»")
    print("    Annot. : «Faute provoquée vollée Thomas Lucas»")
    print("    Incomp.: «Faute directe» → puis énoncer le joueur")
    print("    Vidéo  : «Pause» / «Lecture» / «Retour» / «Avance»")
    print("    Stop   : «Stop écoute»  ou  Ctrl+C")
    print()
    print("─" * 60)

    session = PadelVoiceSession(
        joueurs=["Arnaud", "Pierre", "Thomas", "Lucas"],
        on_annotation=on_annotation,
        on_status=on_status,
        on_video_control=on_video_control,
        on_incomplete=on_incomplete,
        on_error=on_error,
        language="fr-FR",
        enable_whisper=False,
        log_dir="data",
    )

    ok = session.start()
    if not ok:
        print("\n  [ERREUR] Impossible de démarrer le STT.")
        print("  Vérifier: pip install pywin32  ou  pip install SpeechRecognition pyaudio")
        return

    print("\n  Session démarrée. Parlez maintenant.")
    print("  (Ctrl+C pour arrêter)\n")

    try:
        while session.is_active:
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("\n  Interruption clavier.")
    finally:
        session.stop()
        print("\n═" * 60)
        print("  Session terminée.")


if __name__ == "__main__":
    main()
