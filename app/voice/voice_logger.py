"""
Logger dédié pour les commandes vocales
Enregistre tous les détails du traitement vocal pour faciliter le debug
"""

import os
import json
from datetime import datetime
from typing import Dict, Optional


class VoiceLogger:
    """Logger spécialisé pour le système de commandes vocales"""
    
    def __init__(self, log_dir: str = "data"):
        """
        Args:
            log_dir: Dossier où stocker les logs
        """
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        # Fichier de log principal
        self.log_file = os.path.join(log_dir, "voice_commands.log")
        
        # Compteur de commandes
        self.command_counter = 0
        
        # Créer le fichier s'il n'existe pas
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("LOG DES COMMANDES VOCALES - PADEL STAT\n")
                f.write(f"Démarré le: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 80 + "\n\n")
    
    def log_command(self, 
                   raw_text: str,
                   cleaned_text: str,
                   wake_word: Optional[str],
                   command_text: str,
                   parsed_result: Optional[Dict],
                   validation_result: tuple,
                   action_taken: str,
                   error: Optional[str] = None):
        """
        Enregistre une commande vocale complète
        
        Args:
            raw_text: Texte brut transcrit par Google Speech
            cleaned_text: Texte après nettoyage (lower, strip)
            wake_word: Mot de réveil détecté (OK/POINT/FAUTE)
            command_text: Texte de la commande (après extraction du mot de réveil)
            parsed_result: Résultat du parsing (dict ou None)
            validation_result: (is_valid, message)
            action_taken: Action effectuée (ENREGISTRÉ/REJETÉ/ERREUR)
            error: Message d'erreur éventuel
        """
        self.command_counter += 1
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        log_entry = []
        log_entry.append("\n" + "=" * 80)
        log_entry.append(f"COMMANDE #{self.command_counter} - {timestamp}")
        log_entry.append("=" * 80)
        
        # 1. TRANSCRIPTION
        log_entry.append("\n[1] TRANSCRIPTION BRUTE:")
        log_entry.append(f"    '{raw_text}'")
        
        # 2. NETTOYAGE
        log_entry.append("\n[2] APRÈS NETTOYAGE:")
        log_entry.append(f"    '{cleaned_text}'")
        
        # 3. DÉTECTION MOT DE RÉVEIL
        log_entry.append("\n[3] DÉTECTION MOT DE RÉVEIL:")
        if wake_word:
            log_entry.append(f"    ✅ Détecté: '{wake_word}'")
            log_entry.append(f"    → Commande extraite: '{command_text}'")
        else:
            log_entry.append(f"    ❌ Aucun mot de réveil détecté (OK/POINT/FAUTE)")
            log_entry.append(f"    → IGNORÉ")
        
        # 4. PARSING
        log_entry.append("\n[4] RÉSULTAT DU PARSING:")
        if parsed_result:
            log_entry.append(f"    ✅ Parsing réussi:")
            for key, value in parsed_result.items():
                if value is not None and key != 'raw_text':
                    log_entry.append(f"       • {key}: {value}")
        else:
            log_entry.append(f"    ❌ Parsing échoué - Aucun pattern reconnu")
        
        # 5. VALIDATION
        log_entry.append("\n[5] VALIDATION:")
        is_valid, validation_msg = validation_result
        if is_valid:
            log_entry.append(f"    ✅ VALIDE: {validation_msg}")
        else:
            log_entry.append(f"    ❌ INVALIDE: {validation_msg}")
        
        # 6. ACTION
        log_entry.append("\n[6] ACTION:")
        log_entry.append(f"    {action_taken}")
        
        # 7. ERREUR
        if error:
            log_entry.append("\n[7] ERREUR:")
            log_entry.append(f"    ⚠️  {error}")
        
        log_entry.append("\n" + "-" * 80 + "\n")
        
        # Écrire dans le fichier
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write("\n".join(log_entry))
        except Exception as e:
            print(f"[VoiceLogger] Erreur écriture log: {e}")
    
    def log_error(self, error_type: str, message: str, details: Optional[Dict] = None):
        """
        Enregistre une erreur système
        
        Args:
            error_type: Type d'erreur (PARSER/VALIDATION/SYSTEM)
            message: Message d'erreur
            details: Détails supplémentaires
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        log_entry = []
        log_entry.append("\n" + "!" * 80)
        log_entry.append(f"ERREUR SYSTÈME - {timestamp}")
        log_entry.append(f"Type: {error_type}")
        log_entry.append("!" * 80)
        log_entry.append(f"Message: {message}")
        
        if details:
            log_entry.append("\nDétails:")
            for key, value in details.items():
                log_entry.append(f"  • {key}: {value}")
        
        log_entry.append("!" * 80 + "\n")
        
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write("\n".join(log_entry))
        except Exception as e:
            print(f"[VoiceLogger] Erreur écriture log: {e}")
    
    def get_stats(self) -> Dict:
        """Retourne des statistiques sur les logs"""
        return {
            "total_commands": self.command_counter,
            "log_file": self.log_file,
            "exists": os.path.exists(self.log_file)
        }
    
    def clear_logs(self):
        """Efface les logs (nouveau fichier)"""
        if os.path.exists(self.log_file):
            os.remove(self.log_file)
        self.command_counter = 0
        self.__init__(self.log_dir)
