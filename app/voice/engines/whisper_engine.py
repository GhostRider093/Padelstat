"""
Moteur faster-whisper.

Voir SPEC_MODULE_VOCAL_PTT_V2.md section 9.
"""

from __future__ import annotations

import logging
import math
import threading
import time

from app.voice.engines.base import STTEngine, Transcription

logger = logging.getLogger(__name__)


class WhisperEngine(STTEngine):
    """faster-whisper, en decodage contraint par un prompt de biais.

    Le module ne fait pas de dictee libre : on desactive donc tout ce qui
    sert a produire du texte plausible plutot que du texte entendu
    (`condition_on_previous_text`), et on coupe le VAD, le declenchement
    etant deja explicite par le push-to-talk.
    """

    nom = "whisper"

    def __init__(self, config):
        super().__init__(config)
        self._modele = None
        self._device = None
        self._compute_type = None
        # Le moteur est partage entre le push-to-talk et l'ecoute
        # permanente. ctranslate2 ne garantit pas la reentrance : deux
        # transcriptions simultanees sur le meme modele sont a proscrire.
        self._verrou = threading.Lock()

    def charger(self) -> None:
        if self._charge:
            return

        from faster_whisper import WhisperModel

        device, compute_type = self.config.resoudre_device()
        debut = time.perf_counter()

        # Recuperer le modele et l'ouvrir sur un device sont deux echecs
        # distincts. Les confondre ferait passer un cache injoignable pour
        # une panne GPU, et rejouerait le meme echec sur CPU.
        chemin = self._resoudre_modele()

        try:
            self._modele = WhisperModel(
                chemin, device=device, compute_type=compute_type
            )
        except Exception as erreur:
            # Un GPU present mais inutilisable (VRAM saturee, pilote ou
            # cuDNN absent) ne doit pas priver l'utilisateur du module.
            if device != "cuda" or not _est_erreur_gpu(erreur):
                raise
            logger.warning(
                "chargement CUDA impossible (%s), repli sur CPU int8", erreur
            )
            device, compute_type = "cpu", "int8"
            self._modele = WhisperModel(
                chemin, device=device, compute_type=compute_type
            )

        self._device = device
        self._compute_type = compute_type
        self._charge = True

        logger.info(
            "modele %s charge sur %s/%s en %.1f s",
            self.config.modele, device, compute_type,
            time.perf_counter() - debut,
        )

    def _resoudre_modele(self) -> str:
        """Chemin local du modele, telecharge au besoin.

        Isole du chargement : une erreur ici est un probleme de cache ou de
        reseau, jamais un probleme de GPU, et doit remonter telle quelle.
        """
        import os

        if os.path.isdir(self.config.modele):
            return self.config.modele

        from faster_whisper.utils import download_model

        try:
            return download_model(self.config.modele)
        except OSError as erreur:
            cache = os.environ.get("HF_HOME") or os.environ.get("HF_HUB_CACHE")
            raise RuntimeError(
                f"modele '{self.config.modele}' introuvable et non "
                f"telechargeable (cache HF : {cache or 'defaut'}) : {erreur}"
            ) from erreur

    @property
    def device(self) -> str:
        return self._device or "?"

    @property
    def compute_type(self) -> str:
        return self._compute_type or "?"

    def transcrire(self, audio, prompt=None) -> Transcription:
        if not self._charge:
            self.charger()

        duree_audio = len(audio) / self.config.sample_rate
        debut = time.perf_counter()

        with self._verrou:
            segments, info = self._modele.transcribe(
                audio,
                language=self.config.langue,
                initial_prompt=prompt or self.config.initial_prompt,
                beam_size=5,
                temperature=0.0,
                condition_on_previous_text=False,
                vad_filter=False,
            )
            # faster-whisper rend un generateur : c'est ici que le calcul
            # a lieu, donc il doit rester sous le verrou.
            segments = list(segments)

        duree_calcul = time.perf_counter() - debut

        texte = " ".join(s.text.strip() for s in segments).strip()

        return Transcription(
            texte=texte,
            confiance_acoustique=_confiance(segments),
            duree_audio_s=duree_audio,
            duree_calcul_s=duree_calcul,
            moteur=self.nom,
            brut=(segments, info),
        )

    def fermer(self) -> None:
        self._modele = None
        self._charge = False


_SIGNES_GPU = ("cuda", "cudnn", "cublas", "gpu", "device", "nvidia")


def _est_erreur_gpu(erreur: Exception) -> bool:
    """L'echec vient-il du GPU, ou d'autre chose ?

    ctranslate2 remonte des RuntimeError textuelles : on ne peut pas
    discriminer par le type, seulement par le message.
    """
    return any(signe in str(erreur).lower() for signe in _SIGNES_GPU)


def _confiance(segments) -> float:
    """Ramene `avg_logprob` sur [0, 1].

    `avg_logprob` est une log-probabilite moyenne par token, donc negative.
    `exp` la ramene en probabilite. La moyenne est ponderee par la duree :
    un segment d'un mot ne doit pas peser autant qu'une phrase entiere.
    """
    if not segments:
        return 0.0

    total_poids = 0.0
    total = 0.0

    for segment in segments:
        poids = max(segment.end - segment.start, 1e-3)
        logprob = getattr(segment, "avg_logprob", None)
        if logprob is None:
            continue
        total += math.exp(logprob) * poids
        total_poids += poids

    if total_poids == 0.0:
        return 0.0
    return max(0.0, min(1.0, total / total_poids))
