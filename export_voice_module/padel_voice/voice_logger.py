"""Logger dédié pour les commandes vocales.

Objectif: exporter un logger simple (fichier texte) pour diagnostiquer
la transcription, le parsing et la validation.
"""

import os
import platform
import traceback
from datetime import datetime
from typing import Any, Dict, Optional


class VoiceLogger:
    """Logger spécialisé pour le système de commandes vocales"""

    def __init__(self, log_dir: str = "data"):
        self.log_dir = os.path.abspath(log_dir)
        os.makedirs(self.log_dir, exist_ok=True)

        self.log_file = os.path.abspath(os.path.join(self.log_dir, "voice_commands.log"))
        self.command_counter = 0
        self.event_counter = 0

        if not os.path.exists(self.log_file):
            with open(self.log_file, "w", encoding="utf-8") as f:
                f.write("=" * 80 + "\n")
                f.write("LOG DES COMMANDES VOCALES - EXPORT MODULE\n")
                f.write(f"Démarré le: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Chemin absolu log: {self.log_file}\n")
                f.write(f"OS: {platform.platform()}\n")
                f.write(f"PID: {os.getpid()}\n")
                f.write("=" * 80 + "\n\n")

    def _append_lines(self, lines: list[str]):
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    def log_event(self, event: str, data: Optional[Dict[str, Any]] = None):
        self.event_counter += 1
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        lines = [
            "\n" + "#" * 80,
            f"EVENT #{self.event_counter} - {timestamp}",
            "#" * 80,
            f"name: {event}",
            f"log_file: {self.log_file}",
        ]
        if data:
            lines.append("data:")
            for key, value in data.items():
                lines.append(f"  - {key}: {repr(value)}")
        lines.append("-" * 80)
        try:
            self._append_lines(lines)
        except Exception as e:
            print(f"[VoiceLogger] Erreur écriture event log: {e}")

    def log_exception(self, context: str, error: Exception):
        trace = traceback.format_exc()
        self.log_event(
            "exception",
            {
                "context": context,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "traceback": trace,
            },
        )

    def log_command(
        self,
        raw_text: str,
        cleaned_text: str,
        wake_word: Optional[str],
        command_text: str,
        parsed_result: Optional[Dict],
        validation_result: tuple,
        action_taken: str,
        error: Optional[str] = None,
    ):
        self.command_counter += 1
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        log_entry = []
        log_entry.append("\n" + "=" * 80)
        log_entry.append(f"COMMANDE #{self.command_counter} - {timestamp}")
        log_entry.append("=" * 80)

        log_entry.append("\n[1] TRANSCRIPTION BRUTE:")
        log_entry.append(f"    '{raw_text}'")
        log_entry.append(f"    len={len(raw_text)}")

        log_entry.append("\n[2] APRÈS NETTOYAGE:")
        log_entry.append(f"    '{cleaned_text}'")
        log_entry.append(f"    len={len(cleaned_text)}")

        log_entry.append("\n[3] DÉTECTION MOT DE RÉVEIL:")
        if wake_word:
            log_entry.append(f"    ✅ Détecté: '{wake_word}'")
            log_entry.append(f"    → Commande extraite: '{command_text}'")
        else:
            log_entry.append("    ❌ Aucun mot de réveil détecté")
            log_entry.append("    → IGNORÉ")

        log_entry.append("\n[4] RÉSULTAT DU PARSING:")
        if parsed_result:
            log_entry.append("    ✅ Parsing réussi:")
            for key, value in parsed_result.items():
                if value is not None and key != "raw_text":
                    log_entry.append(f"       • {key}: {value}")
        else:
            log_entry.append("    ❌ Parsing échoué")

        log_entry.append("\n[5] VALIDATION:")
        is_valid, validation_msg = validation_result
        if is_valid:
            log_entry.append(f"    ✅ VALIDE: {validation_msg}")
        else:
            log_entry.append(f"    ❌ INVALIDE: {validation_msg}")

        log_entry.append("\n[6] ACTION:")
        log_entry.append(f"    {action_taken}")
        log_entry.append(f"    log_file: {self.log_file}")

        if error:
            log_entry.append("\n[7] ERREUR:")
            log_entry.append(f"    ⚠️  {error}")

        log_entry.append("\n" + "-" * 80 + "\n")

        try:
            self._append_lines(log_entry)
        except Exception as e:
            print(f"[VoiceLogger] Erreur écriture log: {e}")

    def get_stats(self) -> Dict:
        return {
            "total_commands": self.command_counter,
            "total_events": self.event_counter,
            "log_file": self.log_file,
            "exists": os.path.exists(self.log_file),
            "size_bytes": (os.path.getsize(self.log_file) if os.path.exists(self.log_file) else 0),
        }

    def clear_logs(self):
        if os.path.exists(self.log_file):
            os.remove(self.log_file)
        self.command_counter = 0
        self.__init__(self.log_dir)
