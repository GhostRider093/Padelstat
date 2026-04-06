"""Exemple push-to-talk (PTT) — toutes les commandes stats + vidéo.

Simule un lecteur vidéo en CLI:
  Entrée seule     → start/stop enregistrement (PTT)
  p                → pause/lecture (contrôle direct, sans audio)
  r10              → retour 10s
  a2               → avance 2s
  st               → afficher stats
  rv               → review vocal
  q                → quitter

Note: PTT audio nécessite pyaudio + SpeechRecognition (pip install pyaudio SpeechRecognition).
Sans ces dépendances, les exemples de routage fonctionnent quand même en mode texte.
"""

from __future__ import annotations
import time

from padel_voice import CommandParser, VoiceBatchRecorder


# ── Simulation d'état lecteur vidéo ──────────────────────────────────────────

class FakeVideoPlayer:
    def __init__(self):
        self.position = 0.0
        self.playing = False
        self.speed = 1.0
        self.annotations: list = []

    def route(self, cmd: dict):
        """Reçoit une commande parsée et applique l'effet."""
        action = cmd.get("action") or ""
        if action == "pause":
            self.playing = False; print(f"  [VIDEO] ⏸ pause @ {self.position:.1f}s")
        elif action == "lecture":
            self.playing = True; print(f"  [VIDEO] ▶ lecture @ {self.position:.1f}s")
        elif action == "retour_2s":
            self.position = max(0, self.position - 2); print(f"  [VIDEO] ⏪ -2s → {self.position:.1f}s")
        elif action == "avance_2s":
            self.position += 2; print(f"  [VIDEO] ⏩ +2s → {self.position:.1f}s")
        elif action == "retour_10s":
            self.position = max(0, self.position - 10); print(f"  [VIDEO] ⏪ -10s → {self.position:.1f}s")
        elif action == "avance_10s":
            self.position += 10; print(f"  [VIDEO] ⏩ +10s → {self.position:.1f}s")
        elif action == "vitesse_lente":
            self.speed = 0.5; print(f"  [VIDEO] 🐢 x0.5")
        elif action == "vitesse_normale":
            self.speed = 1.0; print(f"  [VIDEO] 🏃 x1.0")
        elif action == "vitesse_rapide":
            self.speed = 2.0; print(f"  [VIDEO] 🚀 x2.0")
        elif action == "point_precedent":
            print(f"  [VIDEO] ◀◀ point précédent")
        elif action == "point_suivant":
            print(f"  [VIDEO] ▶▶ point suivant")
        elif action == "review_vocal":
            print(f"  [STATS] 🔍 review vocal — {len(self.annotations)} annotations")
        elif action == "stats":
            print(f"  [STATS] 📊 {len(self.annotations)} points enregistrés")
        elif action == "annuler":
            if self.annotations:
                removed = self.annotations.pop()
                print(f"  [GESTION] 🗑 supprimé: {removed}")
        elif action == "sauvegarder":
            print(f"  [GESTION] 💾 sauvegarde ({len(self.annotations)} points)")
        elif action == "rapport":
            print(f"  [GESTION] 📄 génération rapport")
        elif action == "nouveau_point":
            tp = cmd.get("type_point", "?")
            j  = cmd.get("joueur", "?")
            tc = cmd.get("type_coup", "?")
            ann = {"ts": self.position, "type_point": tp, "joueur": j, "type_coup": tc}
            self.annotations.append(ann)
            print(f"  [STAT] ✅ +{tp} | {j} | {tc} @ {self.position:.1f}s")
        else:
            print(f"  [?] action inconnue: {action!r}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = CommandParser(joueurs=["Arnaud", "Pierre", "Thomas", "Lucas"])
    player = FakeVideoPlayer()

    def ui_callback(event_type: str, data: dict):
        print(f"  [PTT-EVENT] {event_type}: {data}")

    def create_annotation_callback(audio_text: str, video_timestamp: float) -> bool:
        cmd = parser.parse(audio_text)
        if not cmd:
            print(f"  [PTT] Non reconnu: {audio_text!r}")
            return False
        valid, msg = parser.validate_command(cmd)
        if not valid:
            print(f"  [PTT] Incomplet: {msg}")
            return False
        player.position = video_timestamp
        player.route(cmd)
        return True

    # PTT audio (nécessite pyaudio)
    try:
        rec = VoiceBatchRecorder(data_dir="data")
        rec.start_session(
            video_path="demo_video.mp4",
            ui_callback=ui_callback,
            create_annotation_callback=create_annotation_callback,
        )
        ptt_ok = True
    except RuntimeError as e:
        print(f"  [WARN] PTT audio indisponible ({e})")
        rec = None
        ptt_ok = False

    # Commandes shortcuts clavier → route directement
    _shortcuts = {
        "p":   "pause",
        "l":   "lecture",
        "r10": "retour_10s",
        "a10": "avance_10s",
        "r2":  "retour_2s",
        "a2":  "avance_2s",
        "sl":  "vitesse_lente",
        "sr":  "vitesse_rapide",
        "sn":  "vitesse_normale",
        "st":  "stats",
        "rv":  "review_vocal",
        "z":   "annuler",
        "sv":  "sauvegarder",
    }

    print(f"\nPTT {'✅ actif' if ptt_ok else '❌ désactivé (pyaudio manquant)'}")
    print("Entrée=PTT start/stop | p=pause | r10=retour10s | st=stats | q=quitter")
    print(f"Position: {player.position:.1f}s\n")

    while True:
        s = input("> ").strip().lower()
        if s == "q":
            break
        if s in _shortcuts:
            synthetic = {"action": _shortcuts[s], "raw_text": s}
            player.route(synthetic)
            continue
        if s == "":
            if rec and ptt_ok:
                if not rec.is_recording:
                    player.position += 3.0
                    print(f"  [PTT] 🔴 enregistrement... (ts={player.position:.1f}s)")
                    rec.start_recording(video_timestamp=player.position)
                else:
                    print("  [PTT] ⏹ stop (transcription async...)")
                    rec.stop_recording()
                    time.sleep(0.2)
            else:
                print("  [PTT] audio non disponible — entrez du texte directement")
        else:
            # Texte tapé à la main (test parseur)
            cmd = parser.parse(s)
            if not cmd:
                print(f"  [?] Non reconnu: {s!r}")
                continue
            valid, msg = parser.validate_command(cmd)
            if valid:
                player.route(cmd)
            else:
                print(f"  [INCOMPLET] {msg}")

    if rec:
        rec.cleanup()


if __name__ == "__main__":
    main()
