"""
Contrat commun aux moteurs de reconnaissance vocale.

Changer de moteur ne doit rien casser en amont : le parseur ne voit qu'une
`Transcription`, jamais un objet propre a Whisper ou a Vosk.

Voir SPEC_MODULE_VOCAL_PTT_V2.md sections 7.4 et 12.9.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Transcription:
    """Ce qu'un moteur rend, quel qu'il soit."""

    texte: str
    confiance_acoustique: float = 0.0   # 0.0 .. 1.0, comparable entre moteurs
    duree_audio_s: float = 0.0
    duree_calcul_s: float = 0.0
    moteur: str = ""
    brut: Any = field(default=None, repr=False)   # objet natif, pour debug

    @property
    def vide(self) -> bool:
        return not self.texte.strip()

    @property
    def facteur_temps_reel(self) -> Optional[float]:
        """duree_calcul / duree_audio. < 1 = plus rapide que le temps reel."""
        if self.duree_audio_s <= 0:
            return None
        return self.duree_calcul_s / self.duree_audio_s


class STTEngine(ABC):
    """Moteur de transcription.

    Cycle de vie : `charger()` une fois au demarrage, puis `transcrire()`
    autant de fois que necessaire, puis `fermer()`.

    `charger()` doit etre appele hors du chemin de la premiere commande :
    c'est tout l'objet du warmup (critere d'acceptation 3 de la spec).
    """

    nom: str = "base"

    def __init__(self, config):
        self.config = config
        self._charge = False

    @property
    def charge(self) -> bool:
        return self._charge

    @abstractmethod
    def charger(self) -> None:
        """Charge le modele en memoire. Idempotent."""

    @abstractmethod
    def transcrire(self, audio, prompt: Optional[str] = None) -> Transcription:
        """Transcrit un signal mono float32 a `config.sample_rate`.

        `prompt` remplace le biais de decodage par defaut. Sert a le
        restreindre aux seules valeurs que l'arbre attend encore : un terme
        prononce seul est bien moins reconnu qu'en phrase, et c'est
        exactement ce que produit la completion progressive.
        """

    def warmup(self) -> None:
        """Charge le modele et le fait tourner une fois a vide.

        Le premier appel a un modele fraichement charge paie l'allocation
        des noyaux CUDA et le JIT. On paie ce cout au demarrage plutot qu'a
        la premiere commande de l'utilisateur.
        """
        import numpy as np

        self.charger()
        silence = np.zeros(int(self.config.sample_rate * 0.5), dtype=np.float32)
        self.transcrire(silence)

    def fermer(self) -> None:
        """Libere le modele. Par defaut, rien a faire."""
        self._charge = False
