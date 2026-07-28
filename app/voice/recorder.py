"""
Capture micro push-to-talk.

Le declenchement est explicite : pas de VAD, pas de wake-word, pas de micro
ouvert. On enregistre entre l'appui et le relachement, un point c'est tout.

Ce module ne connait ni Whisper, ni Tkinter, ni l'arbre. Il rend un signal.

Voir SPEC_MODULE_VOCAL_PTT_V2.md sections 4.1 et 4.2.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# Seuil empirique de silence, en RMS sur un signal float32 normalise.
# A recalibrer sur les mesures reelles : l'outil de mesure journalise le RMS
# de chaque capture precisement pour ca.
SEUIL_SILENCE_RMS = 0.003


@dataclass
class Capture:
    """Le resultat d'un appui push-to-talk."""

    audio: np.ndarray            # mono float32
    sample_rate: int
    duree_appui_s: float         # appui -> relachement
    tronquee: bool = False       # garde-fou touche bloquee declenche

    @property
    def duree_s(self) -> float:
        return len(self.audio) / self.sample_rate if self.sample_rate else 0.0

    @property
    def niveau_rms(self) -> float:
        if not len(self.audio):
            return 0.0
        return float(np.sqrt(np.mean(np.square(self.audio))))

    @property
    def silencieuse(self) -> bool:
        return self.niveau_rms < SEUIL_SILENCE_RMS

    @property
    def vide(self) -> bool:
        return len(self.audio) == 0


class ErreurMicro(RuntimeError):
    """Le micro est indisponible. L'app doit rester utilisable au clavier."""


class PTTRecorder:
    """Enregistreur push-to-talk.

    `demarrer()` et `arreter()` sont appeles depuis le thread principal, sur
    les evenements clavier. Le remplissage du tampon se fait dans le callback
    sounddevice, sur un thread audio qui ne doit jamais bloquer.
    """

    def __init__(self, config):
        self.config = config
        self._stream = None
        self._chunks: list = []
        self._verrou = threading.Lock()
        self._debut: Optional[float] = None
        self._tronquee = False
        self._sr_capture = config.sample_rate
        self._max_frames = 0
        self._frames_recues = 0

    # ----------------------------------------------------------------- etat

    @property
    def en_cours(self) -> bool:
        return self._stream is not None

    @property
    def depassement(self) -> bool:
        """Le garde-fou de duree maximale a-t-il saute ?"""
        return self._tronquee

    # -------------------------------------------------------------- capture

    def demarrer(self) -> None:
        """Idempotent : un KeyPress repete par l'auto-repeat clavier ne doit
        pas relancer la capture ni perdre ce qui est deja enregistre."""
        if self.en_cours:
            return

        import sounddevice as sd

        sr, canaux = self._negocier_format()
        self._sr_capture = sr
        self._max_frames = int(sr * self.config.duree_max_appui_s)
        self._frames_recues = 0
        self._tronquee = False
        with self._verrou:
            self._chunks = []

        try:
            self._stream = sd.InputStream(
                device=self.config.peripherique_audio,
                samplerate=sr,
                channels=canaux,
                dtype="float32",
                blocksize=int(sr * self.config.taille_chunk_ms / 1000),
                callback=self._callback,
            )
            self._stream.start()
        except Exception as erreur:
            self._stream = None
            raise ErreurMicro(f"capture impossible : {erreur}") from erreur

        self._debut = time.perf_counter()

    def arreter(self) -> Capture:
        """Ferme le flux et rend l'audio capture."""
        duree_appui = self._duree_appui()
        self._fermer_flux()

        with self._verrou:
            chunks = self._chunks
            self._chunks = []

        audio = (np.concatenate(chunks) if chunks
                 else np.zeros(0, dtype=np.float32))
        audio = self._reechantillonner(audio)

        return Capture(
            audio=audio,
            sample_rate=self.config.sample_rate,
            duree_appui_s=duree_appui,
            tronquee=self._tronquee,
        )

    def annuler(self) -> None:
        """Abandon : on jette tout sans rien rendre."""
        self._fermer_flux()
        with self._verrou:
            self._chunks = []

    def fermer(self) -> None:
        self._fermer_flux()

    # -------------------------------------------------------------- interne

    def _callback(self, indata, frames, horodatage, statut) -> None:
        """Thread audio. Ne doit rien faire de couteux ni de bloquant."""
        if statut:
            logger.debug("statut capture : %s", statut)

        if self._tronquee:
            return

        self._frames_recues += frames
        if self._frames_recues > self._max_frames:
            # Touche restee enfoncee : on arrete d'accumuler plutot que de
            # remplir la memoire. Le flux, lui, sera ferme par l'appelant.
            self._tronquee = True
            logger.warning(
                "appui > %s s, capture tronquee",
                self.config.duree_max_appui_s,
            )
            return

        bloc = indata.copy()
        if bloc.ndim > 1:
            bloc = bloc.mean(axis=1)      # mono

        with self._verrou:
            self._chunks.append(bloc.astype(np.float32, copy=False))

    def _duree_appui(self) -> float:
        return time.perf_counter() - self._debut if self._debut else 0.0

    def _fermer_flux(self) -> None:
        if self._stream is None:
            return
        try:
            self._stream.stop()
            self._stream.close()
        except Exception as erreur:
            logger.debug("fermeture du flux : %s", erreur)
        finally:
            self._stream = None
            self._debut = None

    def _negocier_format(self) -> tuple:
        """Trouve un format accepte par le peripherique.

        On demande d'abord 16 kHz mono, ce que Whisper attend. Si le pilote
        refuse, on capture a sa frequence native et on reechantillonne : mieux
        vaut un reechantillonnage qu'un module vocal qui refuse de demarrer.
        """
        import sounddevice as sd

        device = self.config.peripherique_audio

        try:
            infos = sd.query_devices(device, "input")
        except Exception as erreur:
            raise ErreurMicro(f"aucun peripherique d'entree : {erreur}") from erreur

        canaux = 1 if infos["max_input_channels"] >= 1 else 0
        if canaux == 0:
            raise ErreurMicro("le peripherique n'a aucune entree audio")

        candidats = [self.config.sample_rate, int(infos["default_samplerate"])]
        for sr in candidats:
            try:
                sd.check_input_settings(
                    device=device, channels=canaux,
                    samplerate=sr, dtype="float32",
                )
                if sr != self.config.sample_rate:
                    logger.info(
                        "capture a %d Hz, reechantillonnage vers %d Hz",
                        sr, self.config.sample_rate,
                    )
                return sr, canaux
            except Exception:
                continue

        raise ErreurMicro(
            f"aucune frequence acceptee parmi {candidats} "
            f"sur le peripherique {device}"
        )

    def _reechantillonner(self, audio: np.ndarray) -> np.ndarray:
        """Vers config.sample_rate. Interpolation lineaire : suffisante pour
        de la parole a 16 kHz, et sans dependance supplementaire."""
        cible = self.config.sample_rate
        if self._sr_capture == cible or len(audio) == 0:
            return audio

        n = int(round(len(audio) * cible / self._sr_capture))
        return np.interp(
            np.linspace(0, len(audio) - 1, n),
            np.arange(len(audio)),
            audio,
        ).astype(np.float32)
