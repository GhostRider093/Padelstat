"""
Mesure du mot-clé d'écoute permanente.

Enregistre N prononciations d'un même mot-clé et journalise ce que Whisper
en fait. But : construire la liste de variantes sur des mesures, comme pour
le reste du vocabulaire — « OK STAT » ne sortira pas tel quel, et il vaut
mieux le savoir avant d'écrire le détecteur.

    python outils/mesure_motcle.py

[Espace] maintenir et prononcer    [Échap] terminer
"""

from __future__ import annotations

import json
import os
import queue
import sys
import threading
import time
import tkinter as tk
from collections import Counter
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import soundfile as sf

from app.voice.config import VoiceConfig
from app.voice.engines.whisper_engine import WhisperEngine
from app.voice.normalizer import normaliser
from app.voice.recorder import ErreurMicro, PTTRecorder

MOT_CLE = "OK STAT"
OBJECTIF = 12

DOSSIER = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tests_audio", "corpus_motcle",
)

# Biais de décodage volontairement différent de celui de l'annotation : en
# écoute permanente, le moteur n'attend pas une commande de padel, il guette
# un mot-clé au milieu de n'importe quoi.
PROMPT = "OK Stat. Commande vocale. OK Stat."


class MesureMotCle:

    def __init__(self, racine: tk.Tk):
        self.racine = racine
        self.config = VoiceConfig()
        self.recorder = PTTRecorder(self.config)
        self.moteur = WhisperEngine(self.config)

        self.resultats: queue.Queue = queue.Queue()
        self.captures = []
        self.pret = False
        self.occupe = False
        self.attend_relachement = False

        os.makedirs(DOSSIER, exist_ok=True)
        self.journal = os.path.join(DOSSIER, "motcle.jsonl")

        self._construire()
        self._lier()
        threading.Thread(target=self._warmup, daemon=True).start()
        self.racine.after(30, self._depiler)

    # ------------------------------------------------------------------ UI

    def _construire(self):
        self.racine.title("Mesure du mot-clé — Padelstat")
        self.racine.geometry("900x520")
        self.racine.configure(bg="#12151a")

        def lab(txt, taille, couleur, pady=(0, 0), gras=False):
            w = tk.Label(self.racine, text=txt, bg="#12151a", fg=couleur,
                         font=("Segoe UI", taille, "bold" if gras else "normal"),
                         wraplength=840, justify="center")
            w.pack(pady=pady)
            return w

        self.compteur = lab("", 11, "#6b7280", pady=(20, 0))
        lab("Prononce :", 12, "#6b7280", pady=(16, 0))
        lab(MOT_CLE, 34, "#e5e7eb", pady=(4, 0), gras=True)
        lab("naturellement, comme tu le dirais en annotant",
            10, "#4b5563", pady=(2, 0))

        self.etat = lab("chargement du modèle…", 20, "#f59e0b",
                        pady=(28, 0), gras=True)

        lab("Whisper a entendu :", 12, "#6b7280", pady=(24, 0))
        self.transcription = lab("", 22, "#22d3ee", pady=(4, 0), gras=True)
        self.recap = lab("", 11, "#6b7280", pady=(16, 0))

        lab("[Espace] maintenir et prononcer      [Échap] terminer",
            10, "#4b5563", pady=(24, 0))

    def _lier(self):
        self.racine.bind("<KeyPress-space>", lambda e: self._appui())
        self.racine.bind("<KeyRelease-space>", lambda e: self._relachement())
        self.racine.bind("<Escape>", lambda e: self._quitter())
        self.racine.protocol("WM_DELETE_WINDOW", self._quitter)

    # ------------------------------------------------------------- actions

    def _warmup(self):
        try:
            self.moteur.warmup()
        except Exception as erreur:
            self.resultats.put(("erreur", f"modèle : {erreur}"))
            return
        self.resultats.put(("pret", None))

    def _appui(self):
        if not self.pret or self.occupe or self.attend_relachement:
            return
        if self.recorder.en_cours:
            return
        try:
            self.recorder.demarrer()
        except ErreurMicro as erreur:
            self._etat(f"micro indisponible : {erreur}", "#ef4444")
            return
        self._etat("● ENREGISTREMENT", "#ef4444")

    def _relachement(self):
        self.attend_relachement = False
        if not self.recorder.en_cours:
            return

        capture = self.recorder.arreter()
        if capture.duree_appui_s < self.config.duree_min_appui_ms / 1000:
            self._etat("appui trop court — ignoré", "#f59e0b")
            return
        if capture.vide or capture.silencieuse:
            self._etat(f"rien entendu (RMS {capture.niveau_rms:.4f})", "#f59e0b")
            return

        self.occupe = True
        self._etat("transcription…", "#f59e0b")
        threading.Thread(target=self._transcrire, args=(capture,),
                         daemon=True).start()

    def _transcrire(self, capture):
        try:
            resultat = self.moteur.transcrire(capture.audio, prompt=PROMPT)
            nom = self._sauver(capture, resultat)
            self.resultats.put(("ok", (capture, resultat, nom)))
        except Exception as erreur:
            self.resultats.put(("erreur", str(erreur)))

    def _sauver(self, capture, resultat) -> str:
        nom = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3] + ".wav"
        sf.write(os.path.join(DOSSIER, nom), capture.audio,
                 capture.sample_rate)

        ligne = {
            "wav": nom,
            "mot_cle": MOT_CLE,
            "transcription": resultat.texte,
            "normalise": normaliser(resultat.texte),
            "confiance": round(resultat.confiance_acoustique, 4),
            "duree_audio_s": round(capture.duree_s, 3),
            "rms": round(capture.niveau_rms, 5),
        }
        with open(self.journal, "a", encoding="utf-8") as f:
            f.write(json.dumps(ligne, ensure_ascii=False) + "\n")
        return nom

    def _quitter(self):
        try:
            self.recorder.fermer()
            self.moteur.fermer()
        finally:
            self.racine.destroy()

    # --------------------------------------------------------------- queue

    def _depiler(self):
        try:
            while True:
                genre, charge = self.resultats.get_nowait()

                if genre == "pret":
                    self.pret = True
                    self._maj_compteur()
                    self._etat("prêt — maintiens Espace", "#22c55e")

                elif genre == "erreur":
                    self.occupe = False
                    self._etat(str(charge), "#ef4444")

                elif genre == "ok":
                    self.occupe = False
                    self._afficher(*charge)

        except queue.Empty:
            pass
        self.racine.after(30, self._depiler)

    def _afficher(self, capture, resultat, nom):
        forme = normaliser(resultat.texte)
        self.captures.append(forme)

        self.transcription.config(text=resultat.texte or "(rien)")
        self._maj_compteur()

        distinctes = Counter(self.captures)
        exact = distinctes.get(normaliser(MOT_CLE), 0)
        self.recap.config(
            text=f"formes distinctes : "
                 + "   ".join(f"{f!r}×{n}" for f, n in distinctes.most_common(6))
                 + f"\nexactes : {exact}/{len(self.captures)}")

        if len(self.captures) >= OBJECTIF:
            self._etat(f"✓ {len(self.captures)} captures — Échap pour finir",
                       "#22c55e")
        else:
            self._etat(f"✓ enregistré — encore "
                       f"{OBJECTIF - len(self.captures)}", "#22c55e")

    def _maj_compteur(self):
        self.compteur.config(
            text=f"{len(self.captures)} / {OBJECTIF} captures")

    def _etat(self, texte, couleur):
        self.etat.config(text=texte, fg=couleur)


def main():
    racine = tk.Tk()
    MesureMotCle(racine)
    racine.mainloop()
    print(f"\nMesures : {os.path.join(DOSSIER, 'motcle.jsonl')}")


if __name__ == "__main__":
    main()
