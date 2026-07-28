"""
Outil de mesure du moteur vocal.

Enregistre des commandes padel en push-to-talk, les transcrit avec Whisper,
et journalise tout : audio, texte brut, confiance, latence.

But : construire `vocabulaire.py` sur le profil d'erreurs reel de Whisper,
et non sur celui de Google Speech herite de VARIANTES_COMMANDES_VOCALES.md.
Les deux moteurs ne se trompent pas de la meme facon.

    python outils/mesure_vocale.py

Commandes :  [V] maintenir pour parler    [Espace] phrase suivante
             [R] refaire                  [Echap] quitter

Chaque capture produit un WAV et une ligne JSON dans
tests_audio/corpus_whisper/, rejouables sans micro.
"""

from __future__ import annotations

import json
import os
import queue
import sys
import threading
import time
import tkinter as tk
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import soundfile as sf

from app.voice.arbre import coups_terminaux
from app.voice.config import VoiceConfig
from app.voice.engines.whisper_engine import WhisperEngine
from app.voice.recorder import ErreurMicro, PTTRecorder

DOSSIER = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tests_audio", "corpus_whisper",
)


# --------------------------------------------------------------------------
# Phrases de reference
# --------------------------------------------------------------------------
#
# Derivees de l'arbre : les 13 coups terminaux y passent au moins une fois.
# L'attendu est note en clair pour pouvoir, plus tard, mesurer le parseur
# sur les memes enregistrements.

def _phrases():
    p = []

    coups = [
        ("service", "service", {"zone": "service"}),
        ("lob", "lob", {"zone": "lob"}),
        ("fond de court coup droit", "fond_de_court_CD",
         {"zone": "fond_de_court", "type_coup": "coup_droit"}),
        ("fond de court revers", "fond_de_court_R",
         {"zone": "fond_de_court", "type_coup": "revers"}),
        ("fond de court balle haute smash", "fond_de_court_BH_smash",
         {"zone": "fond_de_court", "type_coup": "balle_haute",
          "coup_bh": "smash_plat"}),
        ("fond de court balle haute víbora", "fond_de_court_BH_vibora",
         {"zone": "fond_de_court", "type_coup": "balle_haute",
          "coup_bh": "vibora"}),
        ("fond de court balle haute bandeja", "fond_de_court_BH_bandeja",
         {"zone": "fond_de_court", "type_coup": "balle_haute",
          "coup_bh": "bandeja"}),
        ("fond de court balle haute bajada", "fond_de_court_BH_bajada",
         {"zone": "fond_de_court", "type_coup": "balle_haute",
          "coup_bh": "bajada"}),
        ("filet coup droit", "volee_CD",
         {"zone": "volee", "type_coup": "coup_droit"}),
        ("filet revers", "volee_R",
         {"zone": "volee", "type_coup": "revers"}),
        ("filet balle haute smash", "volee_BH_smash",
         {"zone": "volee", "type_coup": "balle_haute",
          "coup_bh": "smash_plat"}),
        ("filet balle haute víbora", "volee_BH_vibora",
         {"zone": "volee", "type_coup": "balle_haute",
          "coup_bh": "vibora"}),
        ("filet balle haute bandeja", "volee_BH_bandeja",
         {"zone": "volee", "type_coup": "balle_haute",
          "coup_bh": "bandeja"}),
    ]

    joueurs = ["un", "deux", "trois", "quatre"]

    # Les 13 coups, en point gagnant, en faisant tourner les joueurs.
    for i, (dit, identifiant, slots) in enumerate(coups):
        n = joueurs[i % 4]
        p.append({
            "texte": f"point gagnant joueur {n} {dit}",
            "attendu": dict(slots, type_point="point_gagnant",
                            joueur=i % 4 + 1),
            "coup": identifiant,
            "groupe": "point gagnant",
        })

    # La faute directe porte un coup, elle aussi.
    for i, indice in enumerate([0, 2, 4, 8, 9, 1]):
        dit, identifiant, slots = coups[indice]
        n = joueurs[i % 4]
        p.append({
            "texte": f"faute directe joueur {n} {dit}",
            "attendu": dict(slots, type_point="faute_directe",
                            joueur=i % 4 + 1),
            "coup": identifiant,
            "groupe": "faute directe",
        })

    # Faute provoquee : un joueur entierement, puis l'autre. L'enonce le
    # plus lourd du systeme — jusqu'a 9 slots.
    p += [
        {"texte": "faute provoquée joueur un filet balle haute víbora "
                  "joueur trois fond de court revers",
         "groupe": "faute provoquée"},
        {"texte": "faute provoquée joueur deux service "
                  "joueur quatre filet coup droit",
         "groupe": "faute provoquée"},
        {"texte": "faute provoquée joueur trois fond de court balle haute "
                  "bajada joueur un lob",
         "groupe": "faute provoquée"},
    ]

    # Ordre des mots libre : meme intention attendue.
    p += [
        {"texte": "filet revers point gagnant joueur trois",
         "groupe": "ordre libre"},
        {"texte": "smash gagnant pour le deux fond de court balle haute",
         "groupe": "ordre libre"},
        {"texte": "bajada joueur quatre point gagnant",
         "groupe": "ordre libre"},
    ]

    # Termes isoles : les plus fragiles, et « filet » n'a jamais ete mesure.
    for terme in ["filet", "filet", "bandeja", "víbora", "bajada", "smash",
                  "balle haute", "fond de court", "lob", "annuler"]:
        p.append({"texte": terme, "groupe": "terme isolé"})

    return p


PHRASES = _phrases()

# Garde-fou : la session doit couvrir tous les coups de l'arbre. Si un coup
# est ajoute a arbre.py sans phrase correspondante, on le saura au lancement
# plutot qu'en decouvrant un trou dans le corpus trois heures plus tard.
_couverts = {p["coup"] for p in PHRASES if "coup" in p}
_manquants = coups_terminaux() - _couverts
assert not _manquants, f"coups sans phrase de reference : {sorted(_manquants)}"


# --------------------------------------------------------------------------
# Interface
# --------------------------------------------------------------------------


class Mesure:

    def __init__(self, racine: tk.Tk):
        self.racine = racine
        self.config = VoiceConfig()
        self.recorder = PTTRecorder(self.config)
        self.moteur = WhisperEngine(self.config)

        self.resultats: queue.Queue = queue.Queue()
        self.index = 0
        self.enregistre = 0
        self.pret = False
        self.occupe = False
        # Apres une coupure automatique, la touche est encore enfoncee :
        # l'auto-repetition clavier relancerait une capture en boucle.
        self.attend_relachement = False

        os.makedirs(DOSSIER, exist_ok=True)
        self.journal = os.path.join(DOSSIER, "mesures.jsonl")

        self._construire()
        self._lier_touches()

        threading.Thread(target=self._warmup, daemon=True).start()
        self.racine.after(30, self._depiler)

    # ------------------------------------------------------------------ UI

    def _construire(self):
        self.racine.title("Mesure vocale — Padelstat")
        self.racine.geometry("980x620")
        self.racine.configure(bg="#12151a")

        def etiquette(txt, taille, couleur, pady=(0, 0), gras=False):
            widget = tk.Label(
                self.racine, text=txt, bg="#12151a", fg=couleur,
                font=("Segoe UI", taille, "bold" if gras else "normal"),
                wraplength=920, justify="center",
            )
            widget.pack(pady=pady)
            return widget

        self.compteur = etiquette("", 11, "#6b7280", pady=(18, 0))
        self.groupe = etiquette("", 12, "#8b5cf6", pady=(2, 0))
        etiquette("Dis :", 12, "#6b7280", pady=(14, 0))
        self.phrase = etiquette("", 24, "#e5e7eb", pady=(4, 0), gras=True)

        self.etat = etiquette("chargement du modèle…", 20, "#f59e0b",
                              pady=(26, 0), gras=True)

        etiquette("Whisper a entendu :", 12, "#6b7280", pady=(24, 0))
        self.transcription = etiquette("", 20, "#22d3ee", pady=(4, 0), gras=True)
        self.metriques = etiquette("", 11, "#6b7280", pady=(10, 0))

        self.aide = etiquette(
            "[V] maintenir pour parler    [Espace] suivante    "
            "[R] refaire    [Échap] quitter",
            10, "#4b5563", pady=(28, 0),
        )

    def _lier_touches(self):
        touche = self.config.touche_ptt
        self.racine.bind(f"<KeyPress-{touche}>", lambda e: self._appui())
        self.racine.bind(f"<KeyRelease-{touche}>", lambda e: self._relachement())
        self.racine.bind("<space>", lambda e: self._suivante())
        self.racine.bind("<r>", lambda e: self._afficher_phrase())
        self.racine.bind("<Escape>", lambda e: self._quitter())
        self.racine.protocol("WM_DELETE_WINDOW", self._quitter)

    def _afficher_phrase(self):
        entree = PHRASES[self.index]
        self.compteur.config(
            text=f"{self.index + 1} / {len(PHRASES)}"
                 f"    —    {self.enregistre} capture(s) enregistrée(s)")
        self.groupe.config(text=entree["groupe"].upper())
        self.phrase.config(text=entree["texte"])
        self.transcription.config(text="")
        self.metriques.config(text="")
        self._etat("prêt — maintiens V", "#22c55e")

    def _etat(self, texte, couleur):
        self.etat.config(text=texte, fg=couleur)

    # -------------------------------------------------------------- actions

    def _warmup(self):
        """Hors du thread principal : l'UI ne doit jamais geler."""
        debut = time.perf_counter()
        try:
            self.moteur.warmup()
        except Exception as erreur:
            self.resultats.put(("erreur", f"modèle indisponible : {erreur}"))
            return
        self.resultats.put(("pret", time.perf_counter() - debut))

    def _appui(self):
        if (not self.pret or self.occupe or self.recorder.en_cours
                or self.attend_relachement):
            return
        try:
            self.recorder.demarrer()
        except ErreurMicro as erreur:
            self._etat(f"micro indisponible : {erreur}", "#ef4444")
            return
        self._etat("● ENREGISTREMENT", "#ef4444")

    def _relachement(self, coupe=False):
        if not coupe:
            self.attend_relachement = False    # vrai relachement clavier

        if not self.recorder.en_cours:
            return

        capture = self.recorder.arreter()
        seuil = self.config.duree_min_appui_ms / 1000

        if coupe:
            # Le garde-fou a saute : on transcrit quand meme ce qui a ete
            # capture avant la coupure, c'est de la parole valide. Mais on
            # attend un vrai relachement avant d'autoriser une nouvelle
            # capture, sinon l'auto-repetition boucle.
            self.attend_relachement = True
            self._etat(f"coupé à {self.config.duree_max_appui_s} s "
                       "— relâche V", "#f59e0b")
        elif capture.duree_appui_s < seuil:
            self._etat(f"appui trop court ({capture.duree_appui_s * 1000:.0f} ms)"
                       " — ignoré", "#f59e0b")
            return

        if capture.vide or capture.silencieuse:
            self._etat(f"rien entendu (RMS {capture.niveau_rms:.4f})", "#f59e0b")
            return

        self.occupe = True
        self._etat("transcription…", "#f59e0b")
        threading.Thread(target=self._transcrire, args=(capture,),
                         daemon=True).start()

    def _transcrire(self, capture):
        """Thread de travail. Aucun appel Tkinter ici : tout passe par la
        queue, depilee par le thread principal."""
        try:
            debut = time.perf_counter()
            resultat = self.moteur.transcrire(capture.audio)
            latence = time.perf_counter() - debut
            chemin = self._sauver(capture, resultat)
            self.resultats.put(("ok", (capture, resultat, latence, chemin)))
        except Exception as erreur:
            self.resultats.put(("erreur", str(erreur)))

    def _sauver(self, capture, resultat) -> str:
        entree = PHRASES[self.index]
        horodatage = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        nom = f"{horodatage}.wav"

        sf.write(os.path.join(DOSSIER, nom), capture.audio,
                 capture.sample_rate)

        ligne = {
            "wav": nom,
            "attendu_dit": entree["texte"],
            "groupe": entree["groupe"],
            "transcription": resultat.texte,
            "confiance": round(resultat.confiance_acoustique, 4),
            "duree_audio_s": round(capture.duree_s, 3),
            "duree_calcul_s": round(resultat.duree_calcul_s, 3),
            "rms": round(capture.niveau_rms, 5),
            "tronquee": capture.tronquee,
            "modele": self.config.modele,
            "device": self.moteur.device,
        }
        if "attendu" in entree:
            ligne["attendu_slots"] = entree["attendu"]
        if "coup" in entree:
            ligne["coup"] = entree["coup"]

        with open(self.journal, "a", encoding="utf-8") as fichier:
            fichier.write(json.dumps(ligne, ensure_ascii=False) + "\n")

        return nom

    def _suivante(self):
        if self.occupe:
            return
        self.index = (self.index + 1) % len(PHRASES)
        self._afficher_phrase()

    def _quitter(self):
        try:
            self.recorder.fermer()
            self.moteur.fermer()
        finally:
            self.racine.destroy()

    # ---------------------------------------------------------------- queue

    def _depiler(self):
        """root.after : le seul endroit qui touche a Tkinter."""

        # Garde-fou touche bloquee. Le recorder cesse d'accumuler au-dela de
        # la duree maximale, mais c'est ici que la capture est reellement
        # coupee : sans ca, l'interface reste figee sur ENREGISTREMENT
        # jusqu'au relachement, ce qui se lit comme un plantage.
        if self.recorder.en_cours and self.recorder.depassement:
            self._relachement(coupe=True)

        try:
            while True:
                genre, charge = self.resultats.get_nowait()

                if genre == "pret":
                    self.pret = True
                    self.aide.config(
                        text=self.aide.cget("text")
                        + f"        (warmup {charge:.1f} s)")
                    self._afficher_phrase()

                elif genre == "erreur":
                    self.occupe = False
                    self._etat(str(charge), "#ef4444")

                elif genre == "ok":
                    self.occupe = False
                    self._afficher_resultat(*charge)

        except queue.Empty:
            pass

        self.racine.after(30, self._depiler)

    def _afficher_resultat(self, capture, resultat, latence, chemin):
        self.enregistre += 1
        self.transcription.config(
            text=resultat.texte or "(rien)",
            fg="#22d3ee" if resultat.texte else "#ef4444",
        )
        self.metriques.config(
            text=f"latence {latence * 1000:.0f} ms   ·   "
                 f"audio {capture.duree_s:.2f} s   ·   "
                 f"×{resultat.facteur_temps_reel:.2f} temps réel   ·   "
                 f"confiance {resultat.confiance_acoustique:.3f}   ·   "
                 f"RMS {capture.niveau_rms:.4f}   ·   {chemin}"
        )
        couleur = "#22c55e" if latence < 0.5 else "#f59e0b"
        self._etat("✓ enregistré — [Espace] suivante, [R] refaire", couleur)
        self.compteur.config(
            text=f"{self.index + 1} / {len(PHRASES)}"
                 f"    —    {self.enregistre} capture(s) enregistrée(s)")


def main():
    racine = tk.Tk()
    Mesure(racine)
    racine.mainloop()
    print(f"\nMesures : {os.path.join(DOSSIER, 'mesures.jsonl')}")


if __name__ == "__main__":
    main()
