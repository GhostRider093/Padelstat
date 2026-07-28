"""Moteurs de reconnaissance vocale."""

from app.voice.engines.base import STTEngine, Transcription

__all__ = ["STTEngine", "Transcription", "creer_moteur"]


def creer_moteur(config) -> STTEngine:
    """Instancie le moteur nomme par `config.moteur`."""
    if config.moteur == "whisper":
        from app.voice.engines.whisper_engine import WhisperEngine
        return WhisperEngine(config)
    if config.moteur == "vosk":
        from app.voice.engines.vosk_engine import VoskEngine
        return VoskEngine(config)
    raise ValueError(f"moteur inconnu : {config.moteur!r}")
