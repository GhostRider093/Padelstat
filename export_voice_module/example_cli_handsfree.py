"""Exemple hands-free — écoute continue + routage de toutes les commandes.

Actions supportées:
  Annotations  : faute directe, point gagnant, faute provoquée
  Vidéo        : pause, lecture, retour_10s, avance_2s, vitesse_lente, ...
  Stats        : review_vocal, stats
  Gestion      : annuler, sauvegarder, rapport

Arrêt: Ctrl+C
"""

from __future__ import annotations
import time

from padel_voice import CommandParser, VoiceCommander, VoiceLogger


# ── Callbacks applicatifs (à remplacer par votre logique métier) ─────────────

def on_annotation(cmd: dict):
    """Appelé quand une commande stat complète est reconnue."""
    tp  = cmd.get("type_point", "?")
    j   = cmd.get("joueur", "?")
    d   = cmd.get("defenseur", "")
    tc  = cmd.get("type_coup", "?")
    print(f"  [ANNOTATION] {tp} | joueur={j} | défenseur={d} | type_coup={tc}")
    print(f"    zone_frappe={cmd.get('zone_frappe')} | "
          f"technique={cmd.get('technique')} | "
          f"coup_final={cmd.get('coup_final')}")


def on_video_control(action: str):
    """Appelé pour pause, lecture, retour_10s, avance_2s…"""
    print(f"  [VIDEO] {action}")


def on_stats(action: str):
    """Appelé pour review_vocal, stats..."""
    print(f"  [STATS] {action}")


# ── Point d'entrée ────────────────────────────────────────────────────────────

def main():
    parser = CommandParser(joueurs=["Arnaud", "Pierre", "Thomas", "Lucas"])
    logger = VoiceLogger(log_dir="data")

    _video_actions = {
        "pause", "lecture",
        "retour", "avance",
        "retour_2s", "avance_2s",
        "retour_10s", "avance_10s",
        "vitesse_lente", "vitesse_normale", "vitesse_rapide",
        "point_precedent", "point_suivant",
        "zoom_in", "zoom_out",
    }
    _stats_actions = {"review_vocal", "stats"}

    def on_text(text: str):
        cmd = parser.parse(text)
        if not cmd:
            print(f"  [?] Non reconnu: {text!r}")
            return

        action = cmd.get("action")
        valid, msg = parser.validate_command(cmd)

        logger.log_command(
            raw_text=text,
            cleaned_text=cmd["raw_text"],
            wake_word=None,
            command_text=cmd["raw_text"],
            parsed_result=cmd,
            validation_result=(valid, msg),
            action_taken=action or "unknown",
            error=None if valid else msg,
        )

        print(f"\n>>> {text!r}")

        if action in _video_actions:
            on_video_control(action)
        elif action in _stats_actions:
            on_stats(action)
        elif action == "nouveau_point":
            if valid:
                on_annotation(cmd)
            else:
                print(f"  [INCOMPLET] {msg}")
        elif action in ("annuler", "sauvegarder", "rapport"):
            print(f"  [GESTION] {action}")
        else:
            print(f"  [AUTRE] action={action}")

    vc = VoiceCommander(callback=on_text, language="fr-FR")
    ok = vc.start()
    print("VoiceCommander started:", ok)
    print("Parlez (ou Ctrl+C pour arrêter)")

    try:
        while True:
            time.sleep(0.25)
    except KeyboardInterrupt:
        pass
    finally:
        vc.stop()


if __name__ == "__main__":
    main()
