"""Package exportable: reconnaissance + parsing de commandes vocales (padel).

Ce package est extrait du projet "padel stat" pour être réutilisé dans une autre application.

Import minimal (toujours disponible, sans dépendances audio):
    from padel_voice import CommandParser, PadelVoiceSession, SessionState

Import complet (avec audio STT):
    from padel_voice import VoiceCommander, VoiceBatchRecorder
"""

# ── Toujours disponibles (pas de dépendances audio) ──────────────────────────
from .command_parser import CommandParser
from .voice_logger import VoiceLogger
from .voice_session import PadelVoiceSession, SessionState

# ── STT mains-libres (optionnel: pywin32 / SpeechRecognition) ────────────────
try:
    from .voice_commander import VoiceCommander
except Exception as _e:
    VoiceCommander = None  # type: ignore
    print(f"[WARN] VoiceCommander indisponible: {_e}")

try:
    from .voice_commander_windows import WindowsVoiceCommander, WINDOWS_SAPI_AVAILABLE
except Exception as _e:
    WindowsVoiceCommander = None  # type: ignore
    WINDOWS_SAPI_AVAILABLE = False
    print(f"[WARN] WindowsVoiceCommander indisponible: {_e}")

# ── PTT (optionnel: pyaudio + SpeechRecognition) ─────────────────────────────
try:
    from .voice_batch_recorder import VoiceBatchRecorder
except Exception as _e:
    VoiceBatchRecorder = None  # type: ignore
    print(f"[WARN] VoiceBatchRecorder indisponible: {_e}")

__all__ = [
    # Core (toujours dispo)
    "CommandParser",
    "VoiceLogger",
    "PadelVoiceSession",
    "SessionState",
    # STT optionnel
    "VoiceCommander",
    "WindowsVoiceCommander",
    "WINDOWS_SAPI_AVAILABLE",
    # PTT optionnel
    "VoiceBatchRecorder",
]
