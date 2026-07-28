"""
Configuration du module vocal.

Voir SPEC_MODULE_VOCAL_PTT_V2.md section 9.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# Biais de decodage passe a faster-whisper. Aligne sur l'arbre : chaque
# terme canonique y figure, pour que le modele ait deja entendu le mot
# avant de devoir le reconnaitre.
INITIAL_PROMPT = (
    "Annotation de match de padel. Point gagnant, faute directe, "
    "faute provoquée, attaquant, défenseur. "
    "Joueur un, joueur deux, joueur trois, joueur quatre. "
    "Service, lob, fond de court, filet. Coup droit, revers, balle haute. "
    "Smash à plat, víbora, bandeja, bajada. Annuler."
)


@dataclass
class VoiceConfig:
    # --- capture ---
    touche_ptt: str = "v"
    peripherique_audio: Optional[int] = None   # None = defaut systeme
    sample_rate: int = 16000                   # impose par Whisper
    taille_chunk_ms: int = 30

    # --- moteur ---
    moteur: str = "whisper"                    # "whisper" | "vosk"
    modele: str = "small"                      # base | small | medium
    device: str = "auto"                       # "auto" | "cuda" | "cpu"
    compute_type: str = "auto"                 # auto -> int8 CPU, float16 GPU
    langue: str = "fr"
    initial_prompt: str = INITIAL_PROMPT

    # --- parsing ---
    seuil_fuzzy: int = 80
    seuil_confiance_auto: float = 0.75

    # --- garde-fous PTT ---
    duree_min_appui_ms: int = 300

    # Dimensionne par le chemin le plus long de l'arbre : une faute
    # provoquee complete fait 9 slots (« faute provoquee joueur un joueur
    # trois volee balle haute vibora fond de court revers »), soit 10 a 12 s
    # articulees. Un plafond a 10 s coupait l'enonce le plus utile du
    # systeme. Ce n'est pas un reglage libre : le baisser sous la duree du
    # chemin le plus long rend une partie du domaine inannoncable.
    duree_max_appui_s: int = 20

    def resoudre_device(self) -> tuple:
        """(device, compute_type) effectifs.

        Sur CPU on force int8 : le float16 y est plus lent que l'int8 et
        ctranslate2 le refuse sur la plupart des machines.
        """
        device = self.device
        if device == "auto":
            device = "cuda" if _cuda_disponible() else "cpu"

        compute_type = self.compute_type
        if compute_type == "auto":
            compute_type = "float16" if device == "cuda" else "int8"

        return device, compute_type

    @property
    def taille_chunk(self) -> int:
        """Nombre d'echantillons par chunk de capture."""
        return int(self.sample_rate * self.taille_chunk_ms / 1000)


def _cuda_disponible() -> bool:
    """torch en premier, ctranslate2 en repli.

    ctranslate2 est ce qui fait tourner faster-whisper : c'est lui qui
    tranche en dernier ressort, torch n'est qu'un raccourci quand il est la.
    """
    try:
        import torch
        if torch.cuda.is_available():
            return True
    except Exception:
        pass

    try:
        import ctranslate2
        return ctranslate2.get_cuda_device_count() > 0
    except Exception:
        return False
