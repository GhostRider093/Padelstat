"""Session vocale continue pour annotation de matchs de padel.

Design inspiré de PADELST_PROMPT_TOTAL_CHAT_VOCAL.md + PADELST_PROMPT_IMPORT_DIRECT.md
(NanoCode / F:\\NanoCode).

Architecture états (machine d'état):
──────────────────────────────────────────────────────────────────────────────
  IDLE              → session inactive
  LISTENING         → écoute active STT, attente commande
  PROCESSING        → commande reçue, parsing/validation en cours
  WAITING_COMPLETION→ commande incomplète, attente champs manquants
──────────────────────────────────────────────────────────────────────────────
  Transitions:
    IDLE → LISTENING            (start())
    LISTENING → PROCESSING      (texte reconnu)
    PROCESSING → LISTENING      (commande valide ou non reconnue)
    PROCESSING → WAITING_COMPLETION  (commande incomplète)
    WAITING_COMPLETION → PROCESSING  (complément vocal reçu)
    WAITING_COMPLETION → LISTENING   (commande complétée ou abandonnée)
    * → IDLE                    ("stop écoute" / stop())

Commandes de contrôle session vocale (priorité absolue):
  stop écoute / arrête écoute / quitte / quitter / fin session

Commandes de contrôle lecture vidéo:
  stop / arrête / pause / stop lecture / silence / tais toi
        → on_video_control("pause")
  lecture / play / reprend / reprends
        → on_video_control("play")
  retour / recule / en arrière
        → on_video_control("retour")
  avance / en avant / suivant
        → on_video_control("avance")

Commandes annotation padel (toutes reconnues par CommandParser):
  Types de points: faute directe / point gagnant / faute provoquée
  Types de coups : smash / vollée / bandeja / víbora / coup droit / revers /
                   lob / chiquita / amorti / sortie vitre / contre vitre /
                   fond de court / balle haute / service
  Labels spéciaux: cœur bandeja / cœur smash / cœur víbora
  Zones          : filet / milieu / fond
  Diagonales     : parallèle / croisé
  Joueurs        : noms configurés (Arnaud, Pierre, Thomas, Lucas…)
  Actions        : nouveau point / annuler / sauvegarder / rapport
"""

from __future__ import annotations

import re
import threading
import unicodedata
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from .command_parser import CommandParser
from .voice_logger import VoiceLogger

try:
    from .voice_commander import VoiceCommander
    VOICE_COMMANDER_AVAILABLE = True
except Exception:
    VoiceCommander = None  # type: ignore
    VOICE_COMMANDER_AVAILABLE = False


# ─────────────────────────────────────────────────────────────────────────────
# États de la session
# ─────────────────────────────────────────────────────────────────────────────

class SessionState(str, Enum):
    IDLE               = "IDLE"
    LISTENING          = "LISTENING"
    PROCESSING         = "PROCESSING"
    WAITING_COMPLETION = "WAITING_COMPLETION"


# ─────────────────────────────────────────────────────────────────────────────
# Session vocale principale
# ─────────────────────────────────────────────────────────────────────────────

class PadelVoiceSession:
    """Session vocale continue pour annotation de matchs de padel.

    Usage minimal:

        from padel_voice import PadelVoiceSession

        def on_annotation(cmd: dict):
            print("Annotation:", cmd)

        def on_status(state: str, msg: str):
            print(f"[{state}] {msg}")

        session = PadelVoiceSession(
            joueurs=["Arnaud", "Pierre", "Thomas", "Lucas"],
            on_annotation=on_annotation,
            on_status=on_status,
        )
        session.start()
        # … votre boucle principale …
        session.stop()
    """

    # ── Mots-clés de contrôle (normalisés: sans accents, minuscule) ──────────

    # Arrêt complet de la session (comparaison après _normalize → sans accents)
    STOP_SESSION_WORDS: frozenset = frozenset({
        "stop ecoute", "stopecoute",
        "arrete ecoute", "arreteecoute",
        "quitte", "quitter",
        "fin session", "finsession",
        "stop session",
    })

    # Pause lecture: phrases multi-mots (substring exact)
    PAUSE_PHRASES: frozenset = frozenset({
        "stop lecture", "stoplecture",
        "stop parole",
        "tais toi", "taistoi",
    })
    # Pause lecture: mots simples (détectés avec \b pour éviter faux positifs)
    PAUSE_WORDS: frozenset = frozenset({
        "stop", "arrete", "silence", "coupe", "pause",
    })

    # Reprise lecture vidéo
    PLAY_WORDS: frozenset = frozenset({
        "lecture", "play",
        "reprend", "reprends", "resume",
    })

    # Retour arrière vidéo
    RETOUR_WORDS: frozenset = frozenset({
        "retour", "recule",
        "en arriere",
        "precedent",
    })

    # Avance vidéo
    AVANCE_WORDS: frozenset = frozenset({
        "avance", "en avant",
        "suivant", "next",
    })

    def __init__(
        self,
        joueurs: Optional[List[str]] = None,
        on_annotation: Optional[Callable[[Dict], None]] = None,
        on_status: Optional[Callable[[str, str], None]] = None,
        on_video_control: Optional[Callable[[str], None]] = None,
        on_incomplete: Optional[Callable[[Dict, List[str]], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
        language: str = "fr-FR",
        enable_whisper: bool = False,
        log_dir: str = "data",
    ):
        """
        Args:
            joueurs:           Noms des joueurs du match.
            on_annotation:     Appelé quand une annotation valide est prête.
                               Reçoit le dict complet (action, joueur, type_point,
                               type_coup, zone, diagonale, label, defenseur, raw_text).
            on_status:         Appelé à chaque changement d'état.
                               Signature: (state: str, message: str)
                               state ∈ {"IDLE","LISTENING","PROCESSING","WAITING_COMPLETION"}
            on_video_control:  Appelé avec "pause" / "play" / "retour" / "avance".
            on_incomplete:     Appelé quand la commande est parsée mais incomplète.
                               Signature: (partial_command: dict, missing_fields: list[str])
            on_error:          Appelé en cas d'erreur interne.
            language:          Code langue STT (ex: "fr-FR").
            enable_whisper:    Activer Whisper en dernier recours STT.
            log_dir:           Dossier de logs pour voice_commands.log.
        """
        self.joueurs: List[str] = joueurs or []
        self.on_annotation = on_annotation
        self.on_status = on_status
        self.on_video_control = on_video_control
        self.on_incomplete = on_incomplete
        self.on_error = on_error
        self.language = language
        self.enable_whisper = enable_whisper

        self.parser = CommandParser(joueurs=self.joueurs)
        self.logger = VoiceLogger(log_dir=log_dir)
        self.logger.log_event(
            "session_init",
            {
                "joueurs": list(self.joueurs),
                "language": self.language,
                "enable_whisper": self.enable_whisper,
                "log_file": self.logger.log_file,
            },
        )

        self._state: SessionState = SessionState.IDLE
        self._state_lock = threading.Lock()

        # Commande en attente de complétion
        self._pending_command: Optional[Dict] = None

        # Commander STT
        self._commander: Optional[Any] = None

    # ─────────────────────────────────────────────────────────────────────────
    # API publique
    # ─────────────────────────────────────────────────────────────────────────

    def set_joueurs(self, joueurs: List[str]):
        """Mettre à jour la liste des joueurs en cours de session."""
        self.joueurs = joueurs
        self.parser.set_joueurs(joueurs)

    @property
    def state(self) -> SessionState:
        return self._state

    @property
    def is_active(self) -> bool:
        """True si la session est démarrée (tout état hors IDLE)."""
        return self._state != SessionState.IDLE

    def start(self) -> bool:
        """Démarrer la session d'écoute continue.

        Returns:
            True si la reconnaissance vocale a pu démarrer.
        """
        if not VOICE_COMMANDER_AVAILABLE or VoiceCommander is None:
            msg = "VoiceCommander indisponible (dépendances STT manquantes)."
            self._set_state(SessionState.IDLE, msg)
            if self.on_error:
                self.on_error(msg)
            return False

        if self._state != SessionState.IDLE:
            return True  # Déjà active

        self._commander = VoiceCommander(
            callback=self._on_text_received,
            language=self.language,
            enable_whisper=self.enable_whisper,
            log_dir=self.logger.log_dir,
        )
        ok = self._commander.start()
        if ok:
            self.logger.log_event("session_start_ok", {"log_file": self.logger.log_file})
            print(f"[VOICE-DEBUG] Log absolu: {self.logger.log_file}")
            self._set_state(SessionState.LISTENING, "Session vocale démarrée. Je vous écoute.")
        else:
            self.logger.log_event("session_start_failed", {})
            self._set_state(SessionState.IDLE, "Impossible de démarrer la reconnaissance vocale.")
        return ok

    def stop(self):
        """Arrêter la session vocale (→ IDLE)."""
        if self._commander:
            try:
                self._commander.stop()
            except Exception:
                pass
            self._commander = None
        self._pending_command = None
        self.logger.log_event("session_stop", {})
        self._set_state(SessionState.IDLE, "Session vocale arrêtée.")

    def cancel_pending(self):
        """Annuler la commande incomplète en attente et revenir en écoute."""
        self._pending_command = None
        self._set_state(SessionState.LISTENING, "Commande annulée. En écoute.")

    def inject_text(self, text: str):
        """Injecter manuellement un texte (utile pour tests ou STT externe).

        Traite le texte comme s'il venait d'être reconnu par le micro.
        """
        self._on_text_received(text)

    # ─────────────────────────────────────────────────────────────────────────
    # Callback STT interne
    # ─────────────────────────────────────────────────────────────────────────

    def _on_text_received(self, text: str):
        """Appelé par VoiceCommander (ou inject_text) à chaque transcription."""
        if not text or not text.strip():
            return

        raw = text.strip()
        norm = self._normalize(raw)

        # ── Priorité 1: stop session ────────────────────────────────────────
        if self._is_stop_session(norm):
            self._log(raw, norm, parsed=None, action="stop_session", error=None)
            self.stop()
            return

        # ── Priorité 2: complétion commande incomplète ──────────────────────
        if self._state == SessionState.WAITING_COMPLETION and self._pending_command is not None:
            self._complete_pending(raw, norm)
            return

        # ── Priorité 3: contrôle vidéo ──────────────────────────────────────
        video_cmd = self._detect_video_command(norm)
        if video_cmd:
            self._log(raw, norm, parsed=None, action=f"video:{video_cmd}", error=None)
            if self.on_video_control:
                self.on_video_control(video_cmd)
            self._restore_listening()
            return

        # ── Priorité 4: commande annotation padel ───────────────────────────
        # On passe 'raw' (texte original) au parser: il a sa propre normalisation
        # (normaliser_texte) qui gère les corrections phonétiques avec accents.
        self._process_annotation(raw, norm)

    # ─────────────────────────────────────────────────────────────────────────
    # Traitement annotation
    # ─────────────────────────────────────────────────────────────────────────

    def _process_annotation(self, raw: str, norm: str):
        """Parser + valider → callback ou attente complétion."""
        self._set_state(SessionState.PROCESSING, f"Traitement: {raw}")

        # Passer 'raw' au parser: CommandParser.normaliser_texte() gère
        # les corrections phonétiques avec accents (ex: vollée, provoquée…).
        # 'norm' n'est utilisé QUE pour la détection des mots de contrôle.
        parsed = self.parser.parse(raw)

        if parsed is None:
            self._log(raw, norm, parsed=None, action="unknown", error="Non reconnu")
            self._set_state(SessionState.LISTENING, f"Non reconnu: «{raw}»")
            return

        valid, msg = self.parser.validate_command(parsed)

        if valid:
            self._log(raw, norm, parsed=parsed, action="annotation", error=None)
            if self.on_annotation:
                self.on_annotation(parsed)
            label = self.parser.format_command(parsed)
            self._set_state(SessionState.LISTENING, f"✓ {label}")
        else:
            missing = self.parser.get_missing_fields(parsed)
            self._pending_command = parsed
            self._log(raw, norm, parsed=parsed, action="incomplete", error=msg)

            if self.on_incomplete:
                self.on_incomplete(parsed, missing)

            if missing:
                prompt = "Manquant: " + ", ".join(missing)
                self._set_state(SessionState.WAITING_COMPLETION, prompt)
            else:
                # validate a retourné False sans missing → commande invalide définitive
                self._pending_command = None
                self._set_state(SessionState.LISTENING, f"Invalide: {msg}")

    def _complete_pending(self, raw: str, norm: str):
        """Tenter de compléter la commande en attente avec ce nouveau texte."""
        pending = self._pending_command
        if pending is None:
            self._set_state(SessionState.LISTENING, "Commande en attente introuvable.")
            return

        addition = self.parser.parse(raw)  # raw: parser gère sa propre normalisation

        if addition:
            # Si la nouvelle commande est complètement différente (autre type_point
            # ou action explicite différente de nouveau_point), abandonner la pending
            # et traiter la nouvelle commande directement.
            pending_tp = pending.get("type_point")
            new_tp = addition.get("type_point")
            new_action = addition.get("action")
            is_new_independent_command = (
                (new_tp and new_tp != pending_tp)
                or (new_action and new_action not in ("nouveau_point", None))
            )
            if is_new_independent_command:
                self._pending_command = None
                self._set_state(SessionState.LISTENING, "Commande précédente annulée.")
                self._process_annotation(raw, norm)
                return

            # Fusionner: on ne remplace QUE les champs None/absents
            for key, val in addition.items():
                if val is not None and not pending.get(key):
                    pending[key] = val

        valid, msg = self.parser.validate_command(pending)

        if valid:
            cmd = pending
            self._pending_command = None
            self._log(raw, norm, parsed=cmd, action="annotation_completed", error=None)
            if self.on_annotation:
                self.on_annotation(cmd)
            label = self.parser.format_command(cmd)
            self._set_state(SessionState.LISTENING, f"✓ (complété) {label}")
        else:
            missing = self.parser.get_missing_fields(pending)
            self._log(raw, norm, parsed=pending, action="still_incomplete", error=msg)
            if self.on_incomplete:
                self.on_incomplete(pending, missing)
            prompt = "Encore manquant: " + ", ".join(missing)
            self._set_state(SessionState.WAITING_COMPLETION, prompt)

    # ─────────────────────────────────────────────────────────────────────────
    # Détection de commandes de contrôle
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _normalize(text: str) -> str:
        """Normalisation: minuscule, sans accents, sans ponctuation, espaces compactés."""
        s = text.lower().strip()
        # Supprimer les diacritiques
        s = unicodedata.normalize("NFD", s)
        s = "".join(c for c in s if unicodedata.category(c) != "Mn")
        # Supprimer ponctuation
        s = re.sub(r"[^\w\s]", " ", s)
        # Compacter espaces
        s = re.sub(r"\s+", " ", s).strip()
        return s

    def _is_stop_session(self, norm: str) -> bool:
        """Détecter une demande d'arrêt de session vocale."""
        return any(w in norm for w in self.STOP_SESSION_WORDS)

    def _detect_video_command(self, norm: str) -> Optional[str]:
        """Détecter une commande de contrôle vidéo. Retourne None si aucune."""
        # Phrases exactes (substring suffisant car multi-mots)
        if any(phrase in norm for phrase in self.PAUSE_PHRASES):
            return "pause"
        # Mots courts: utiliser frontière de mot pour éviter faux positifs
        if any(re.search(r"\b" + re.escape(w) + r"\b", norm) for w in self.PAUSE_WORDS):
            return "pause"
        if any(re.search(r"\b" + re.escape(w) + r"\b", norm) for w in self.PLAY_WORDS):
            return "play"
        if any(re.search(r"\b" + re.escape(w) + r"\b", norm) for w in self.RETOUR_WORDS):
            return "retour"
        if any(re.search(r"\b" + re.escape(w) + r"\b", norm) for w in self.AVANCE_WORDS):
            return "avance"
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _restore_listening(self):
        """Revenir en écoute si on n'est pas déjà dans cet état."""
        if self._state not in (SessionState.IDLE, SessionState.LISTENING):
            self._set_state(SessionState.LISTENING, "En écoute…")

    def _set_state(self, new_state: SessionState, message: str = ""):
        with self._state_lock:
            old = self._state
            self._state = new_state
        if self.on_status:
            try:
                self.on_status(new_state.value, message)
            except Exception:
                pass

    def _log(self, raw: str, cleaned: str, parsed: Optional[Dict], action: str, error: Optional[str]):
        try:
            self.logger.log_command(
                raw_text=raw,
                cleaned_text=cleaned,
                wake_word=None,
                command_text=cleaned,
                parsed_result=parsed,
                validation_result=(error is None, error or "ok"),
                action_taken=action,
                error=error,
            )
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# Smoke test minimal (parser only, sans audio)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    annotation_items = []
    statuses = []
    incompletes = []

    session = PadelVoiceSession(
        joueurs=["Arnaud", "Pierre", "Thomas", "Lucas"],
        on_annotation=lambda cmd: annotation_items.append(cmd) or print("✓ ANNOTATION:", cmd),
        on_status=lambda s, m: statuses.append((s, m)) or print(f"  [{s}] {m}"),
        on_video_control=lambda c: print(f"  VIDEO: {c}"),
        on_incomplete=lambda cmd, miss: incompletes.append((cmd, miss)) or print(f"  INCOMPLET → {miss}"),
    )

    print("=== Test PadelVoiceSession (inject_text) ===\n")

    tests = [
        # Commandes annotation complètes
        ("Nouveau point faute directe Arnaud",           "annotation"),
        ("Point gagnant smash Pierre",                   "annotation"),
        ("Faute provoquée vollée Thomas Lucas",          "annotation"),
        ("Bandeja cœur Lucas",                           "annotation"),
        # Commandes incomplètes (puis complétion)
        ("Faute directe",                                "incomplet → joueur manquant"),
        ("Arnaud",                                       "complète la précédente"),
        # Contrôle vidéo
        ("Pause",                                        "video:pause"),
        ("Lecture",                                      "video:play"),
        ("Retour",                                       "video:retour"),
        ("Avance",                                       "video:avance"),
        # Commandes simples
        ("Annuler",                                      "annotation:annuler"),
        ("Sauvegarder",                                  "annotation:sauvegarder"),
        # Stop session
        ("Stop écoute",                                  "stop_session"),
    ]

    # Simuler un démarrage sans audio
    session._state = SessionState.LISTENING

    for text, expected in tests:
        print(f"\n▶ «{text}»  (attendu: {expected})")
        session.inject_text(text)

    print(f"\n═══")
    print(f"Annotations créées: {len(annotation_items)}")
    print(f"Incomplets reçus  : {len(incompletes)}")
    print(f"État final        : {session.state.value}")
