"""
Gestionnaire d'annotations pour les points de padel
Gère : Fautes directes, Points gagnants, Fautes provoquées
"""

import os
import json
import shutil
import threading
from datetime import datetime


class AnnotationManager:
    def __init__(self, data_folder="data", enable_background_ai=True):
        self.data_folder = data_folder
        self.screens_folder = os.path.join(data_folder, "screens")
        self.backup_folder = os.path.join(data_folder, "backups")
        self.enable_background_ai = bool(enable_background_ai)
        self.annotations = []
        self.match_info = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "joueurs": [],
            "video": None
        }
        self.current_point_id = 1
        self.autosave_file = None
        self._autosave_lock = threading.Lock()
        # Historique des changements de positions dans le temps
        # Entrée: {"timestamp": float, "positions": [pos1, pos2, pos3, pos4]}
        self.position_changes = []
        
        # Créer les dossiers si nécessaire
        os.makedirs(self.screens_folder, exist_ok=True)
        os.makedirs(self.backup_folder, exist_ok=True)

    def _is_in_backup_folder(self, path: str) -> bool:
        try:
            if not path:
                return False
            return os.path.normcase(os.path.normpath(os.path.dirname(path))) == os.path.normcase(
                os.path.normpath(self.backup_folder)
            )
        except Exception:
            return False
    
    def set_players(self, players):
        """Définit les 4 joueurs du match"""
        self.match_info["joueurs"] = players
        # Initialiser un état de positions à t=0 si on a des infos
        try:
            positions = []
            for p in players:
                if isinstance(p, dict):
                    positions.append(p.get("position", "gauche"))
                else:
                    positions.append("gauche")
            if positions and not self.position_changes:
                self.position_changes.append({
                    "timestamp": 0.0,
                    "positions": positions
                })
        except Exception:
            pass
    
    def set_video(self, video_path):
        """Définit la vidéo du match"""
        self.match_info["video"] = os.path.basename(video_path)
        try:
            self.match_info["video_path"] = os.path.abspath(video_path)
        except Exception:
            self.match_info["video_path"] = video_path
        
        # Créer le fichier d'autosave basé sur le nom de la vidéo
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.autosave_file = os.path.join(
            self.data_folder,
            f"autosave_{video_name}_{timestamp}.json"
        )
        
        # Réinitialiser l'historique IA pour le nouveau match
        self._reset_ai_history()
    
    def find_latest_autosave(self):
        """Trouve le dernier fichier autosave disponible"""
        try:
            autosave_files = [
                f for f in os.listdir(self.data_folder)
                if f.startswith("autosave_") and f.endswith(".json")
            ]
            if autosave_files:
                # Trier par date de modification (plus récent en premier)
                autosave_files.sort(
                    key=lambda x: os.path.getmtime(
                        os.path.join(self.data_folder, x)
                    ),
                    reverse=True
                )
                latest = os.path.join(self.data_folder, autosave_files[0])
                return latest
        except Exception as e:
            print(f"Erreur recherche autosave: {e}")
        return None
    
    def get_autosave_info(self, autosave_path):
        """Récupère les infos d'un fichier autosave"""
        try:
            with open(autosave_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            match_info = data.get("match", {})
            points = data.get("points", [])
            
            return {
                "path": autosave_path,
                "video": match_info.get("video", "Inconnue"),
                "video_path": match_info.get("video_path"),
                "date": match_info.get("date", ""),
                "joueurs": match_info.get("joueurs", []),
                "nb_points": len(points),
                "modified": datetime.fromtimestamp(
                    os.path.getmtime(autosave_path)
                ).strftime("%d/%m/%Y %H:%M")
            }
        except Exception as e:
            print(f"Erreur lecture info autosave: {e}")
            return None
    
    def _generate_live_report_background(self):
        """Génère le rapport live avec analyse IA en thread de FAIBLE PRIORITÉ
        L'IA s'exécute à chaque point mais doucement, sans gêner l'annotation"""
        def run_ai_analysis():
            try:
                # Réduire la priorité du thread pour ne pas gêner l'UI
                import sys
                if sys.platform == 'win32':
                    import win32process
                    import win32api
                    try:
                        # Priorité BELOW_NORMAL pour Windows
                        handle = win32api.GetCurrentThread()
                        win32process.SetThreadPriority(handle, win32process.THREAD_PRIORITY_BELOW_NORMAL)
                    except:
                        pass  # Si win32 pas disponible, continuer quand même
                else:
                    # Sur Linux/Mac, réduire la priorité avec os.nice
                    import os
                    try:
                        os.nice(10)  # Augmente la "gentillesse" = priorité plus basse
                    except:
                        pass
                
                # Lancer l'analyse IA en arrière-plan (force_analyze=True)
                # IMPORTANT: generate_live_report attend un dict (export_to_dict), pas un chemin.
                from app.exports.live_html_generator import generate_live_report
                if self.autosave_file:
                    match_data = self.export_to_dict()
                    if match_data and match_data.get("points"):
                        generate_live_report(match_data, force_analyze=True)
            except Exception:
                pass  # Silencieux pour ne pas perturber l'annotation
        
        # Créer et démarrer le thread en mode daemon (priorité basse)
        thread = threading.Thread(target=run_ai_analysis, daemon=True, name="AI-LowPriority")
        thread.start()
    
    def _reset_ai_history(self):
        """Réinitialise l'historique IA pour un nouveau match"""
        try:
            history_file = os.path.join(self.data_folder, "ai_history.json")
            if os.path.exists(history_file):
                os.remove(history_file)
                print("[AnnotationManager] Historique IA réinitialisé pour nouveau match")
        except Exception as e:
            print(f"[AnnotationManager] Erreur réinitialisation historique IA: {e}")
    
    def autosave(self):
        """Sauvegarde automatique après chaque annotation"""
        if not self.autosave_file:
            # Créer un fichier autosave générique si pas de vidéo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.autosave_file = os.path.join(
                self.data_folder,
                f"autosave_{timestamp}.json"
            )
        
        try:
            with self._autosave_lock:
                data = self.export_to_dict()
                data["_meta"] = {
                    "saved_at": datetime.now().isoformat(timespec="seconds"),
                    "autosave_version": 2,
                }

                temp_path = f"{self.autosave_file}.tmp"
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(temp_path, self.autosave_file)

                backup_name = os.path.basename(self.autosave_file)
                backup_path = os.path.join(self.backup_folder, backup_name)
                # Si l'autosave est déjà dans le dossier backup, ne pas recopier (SameFileError)
                if os.path.normcase(os.path.normpath(self.autosave_file)) != os.path.normcase(
                    os.path.normpath(backup_path)
                ):
                    shutil.copy2(self.autosave_file, backup_path)

            # Lancer analyse IA en thread de FAIBLE PRIORITÉ (à chaque point)
            # L'IA travaille doucement en arrière-plan sans gêner l'annotation
            if self.enable_background_ai:
                self._generate_live_report_background()
            return True
        except Exception as e:
            try:
                temp_path = f"{self.autosave_file}.tmp"
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception:
                pass
            print(f"Erreur autosave: {e}")
            return False
    
    def load_autosave(self, autosave_path):
        """Charge un fichier d'autosave"""
        try:
            with open(autosave_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.load_from_dict(data)
            # Si on charge depuis data/backups, continuer l'autosave dans data/
            # (le dossier backups est une copie miroir, pas la cible d'écriture).
            if self._is_in_backup_folder(autosave_path):
                target_path = os.path.join(self.data_folder, os.path.basename(autosave_path))
                try:
                    if os.path.normcase(os.path.normpath(target_path)) != os.path.normcase(
                        os.path.normpath(autosave_path)
                    ):
                        shutil.copy2(autosave_path, target_path)
                except Exception:
                    pass
                self.autosave_file = target_path
            else:
                self.autosave_file = autosave_path
            return True
        except Exception as e:
            print(f"Erreur chargement autosave: {e}")
            # Tentative de reprise depuis la sauvegarde miroir
            try:
                backup_path = os.path.join(
                    self.backup_folder, os.path.basename(autosave_path)
                )
                if os.path.exists(backup_path):
                    with open(backup_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    self.load_from_dict(data)
                    # Même logique: écrire dans data/ si on a chargé depuis backup
                    if self._is_in_backup_folder(autosave_path):
                        self.autosave_file = os.path.join(self.data_folder, os.path.basename(autosave_path))
                    else:
                        self.autosave_file = autosave_path
                    print(f"[RECOVERY] Autosave restauré depuis backup: {backup_path}")
                    return True
            except Exception as backup_error:
                print(f"[RECOVERY] Échec restauration backup: {backup_error}")
            return False
    
    def add_faute_directe(self, joueur, timestamp, frame, type_coup=None, capture_path=None):
        """Ajoute une faute directe avec détails du coup"""
        annotation = {
            "id": self.current_point_id,
            "type": "faute_directe",
            "joueur": joueur,
            "type_coup": type_coup,
            "timestamp": round(timestamp, 2),
            "frame": frame,
            "capture": capture_path if capture_path else None
        }
        self.annotations.append(annotation)
        self.current_point_id += 1
        self.autosave()  # Sauvegarde automatique
        return annotation
    
    def add_point_gagnant(self, joueur, timestamp, frame, type_coup=None,
                          capture_path=None):
        """Ajoute un point gagnant avec type de coup"""
        annotation = {
            "id": self.current_point_id,
            "type": "point_gagnant",
            "joueur": joueur,
            "type_coup": type_coup,
            "timestamp": round(timestamp, 2),
            "frame": frame,
            "capture": capture_path if capture_path else None
        }
        self.annotations.append(annotation)
        self.current_point_id += 1
        self.autosave()  # Sauvegarde automatique
        return annotation
    
    def add_faute_provoquee(self, attaquant, defenseur, timestamp, frame,
                            type_coup_attaquant=None, type_coup_defenseur=None,
                            capture_path=None):
        """Ajoute une faute provoquée avec détails des coups"""
        annotation = {
            "id": self.current_point_id,
            "type": "faute_provoquee",
            "attaquant": attaquant,
            "defenseur": defenseur,
            "type_coup_attaquant": type_coup_attaquant,
            "type_coup_defenseur": type_coup_defenseur,
            "timestamp": round(timestamp, 2),
            "frame": frame,
            "capture": capture_path if capture_path else None
        }
        self.annotations.append(annotation)
        self.current_point_id += 1
        self.autosave()  # Sauvegarde automatique
        return annotation
    
    def remove_last_annotation(self):
        """Supprime la dernière annotation"""
        if self.annotations:
            removed = self.annotations.pop()
            self.autosave()  # Sauvegarde après suppression
            return removed
        return None
    
    def get_all_annotations(self):
        """Retourne toutes les annotations"""
        return self.annotations
    
    def get_stats(self):
        """Calcule les statistiques du match"""
        # Initialiser les stats pour chaque joueur
        joueurs = self.match_info["joueurs"]
        stats = {}
        
        for joueur in joueurs:
            # Support ancien format (string) et nouveau format (dict)
            nom = (
                joueur if isinstance(joueur, str)
                else joueur.get('nom', joueur)
            )
            stats[nom] = {
                "fautes_directes": 0,
                "fautes_directes_detail": {
                    "service": 0,
                    "volee_coup_droit": 0,
                    "volee_revers": 0,
                    "volee_balle_haute": 0,
                    "fond_de_court_coup_droit": 0,
                    "fond_de_court_revers": 0,
                    "fond_de_court_balle_haute": 0,
                    "smash": 0,
                    "lobe": 0,
                    "amorti": 0,
                    "bandeja": 0,
                    "vibora": 0,
                    "autre": 0
                },
                "points_gagnants": 0,
                "points_gagnants_detail": {
                    "service": 0,
                    "volee_coup_droit": 0,
                    "volee_revers": 0,
                    "volee_balle_haute": 0,
                    "fond_de_court_coup_droit": 0,
                    "fond_de_court_revers": 0,
                    "fond_de_court_balle_haute": 0,
                    "smash": 0,
                    "lobe": 0,
                    "amorti": 0,
                    "bandeja": 0,
                    "vibora": 0,
                    "autre": 0
                },
                "fautes_provoquees_subies": 0,
                "fautes_provoquees_subies_detail": {
                    "service": 0,
                    "volee_coup_droit": 0,
                    "volee_revers": 0,
                    "volee_balle_haute": 0,
                    "fond_de_court_coup_droit": 0,
                    "fond_de_court_revers": 0,
                    "fond_de_court_balle_haute": 0,
                    "smash": 0,
                    "lobe": 0,
                    "amorti": 0,
                    "bandeja": 0,
                    "vibora": 0,
                    "autre": 0
                },
                "fautes_provoquees_generees": 0,
                "fautes_provoquees_generees_detail": {
                    "service": 0,
                    "volee_coup_droit": 0,
                    "volee_revers": 0,
                    "volee_balle_haute": 0,
                    "fond_de_court_coup_droit": 0,
                    "fond_de_court_revers": 0,
                    "fond_de_court_balle_haute": 0,
                    "smash": 0,
                    "lobe": 0,
                    "amorti": 0,
                    "bandeja": 0,
                    "vibora": 0,
                    "autre": 0
                },
                "coups_coeur": {
                    "defense": 0,
                    "attaque": 0,
                    "spectaculaire": 0
                }
            }
        
        for annotation in self.annotations:
            if annotation["type"] == "faute_directe":
                joueur = annotation["joueur"]
                # Extraire le nom si c'est un dict
                nom_joueur = joueur if isinstance(joueur, str) else joueur.get('nom', joueur)
                if nom_joueur in stats:
                    stats[nom_joueur]["fautes_directes"] += 1
                    # Détail du type de coup pour fautes directes
                    type_coup = annotation.get("type_coup", "autre")
                    if (
                        type_coup and
                        type_coup in stats[nom_joueur]["fautes_directes_detail"]
                    ):
                        stats[nom_joueur]["fautes_directes_detail"][type_coup] += 1
                    else:
                        stats[nom_joueur]["fautes_directes_detail"]["autre"] += 1
            
            elif annotation["type"] == "point_gagnant":
                joueur = annotation["joueur"]
                # Extraire le nom si c'est un dict
                nom_joueur = joueur if isinstance(joueur, str) else joueur.get('nom', joueur)
                if nom_joueur in stats:
                    stats[nom_joueur]["points_gagnants"] += 1
                    # Détail du type de coup
                    type_coup = annotation.get("type_coup", "autre")
                    if (
                        type_coup and
                        type_coup in stats[nom_joueur]["points_gagnants_detail"]
                    ):
                        stats[nom_joueur]["points_gagnants_detail"][type_coup] += 1
                    else:
                        stats[nom_joueur]["points_gagnants_detail"]["autre"] += 1
            
            elif annotation["type"] == "faute_provoquee":
                attaquant = annotation["attaquant"]
                defenseur = annotation["defenseur"]
                # Extraire les noms si ce sont des dicts
                nom_attaquant = attaquant if isinstance(attaquant, str) else attaquant.get('nom', attaquant)
                nom_defenseur = defenseur if isinstance(defenseur, str) else defenseur.get('nom', defenseur)
                if nom_attaquant in stats:
                    stats[nom_attaquant]["fautes_provoquees_generees"] += 1
                    # Détail du type de coup de l'attaquant
                    type_coup_att = annotation.get("type_coup_attaquant", "autre")
                    if (
                        type_coup_att and
                        type_coup_att in stats[nom_attaquant]["fautes_provoquees_generees_detail"]
                    ):
                        stats[nom_attaquant]["fautes_provoquees_generees_detail"][type_coup_att] += 1
                    else:
                        stats[nom_attaquant]["fautes_provoquees_generees_detail"]["autre"] += 1
                if nom_defenseur in stats:
                    stats[nom_defenseur]["fautes_provoquees_subies"] += 1
                    # Détail du type de coup du défenseur (coup fautif)
                    type_coup_def = annotation.get("type_coup_defenseur", "autre")
                    if (
                        type_coup_def and
                        type_coup_def in stats[defenseur]["fautes_provoquees_subies_detail"]
                    ):
                        stats[defenseur]["fautes_provoquees_subies_detail"][type_coup_def] += 1
                    else:
                        stats[defenseur]["fautes_provoquees_subies_detail"]["autre"] += 1
            
            elif annotation["type"] == "coup_coeur":
                joueur = annotation.get("player")
                coeur_type = annotation.get("coup_coeur_type")
                if joueur in stats and coeur_type:
                    stats[joueur]["coups_coeur"][coeur_type] += 1
        
        # Calculer les statistiques agrégées par type de coup technique
        for joueur in joueurs:
            nom = (
                joueur if isinstance(joueur, str)
                else joueur.get('nom', joueur)
            )
            if nom not in stats:
                continue
            
            # Initialiser les stats agrégées
            stats[nom]["coups_techniques"] = {
                "service": {"total": 0, "fautes": 0, "gagnants": 0, "fp_generees": 0, "fp_subies": 0},
                "coup_droit": {"total": 0, "fautes": 0, "gagnants": 0, "fp_generees": 0, "fp_subies": 0},
                "revers": {"total": 0, "fautes": 0, "gagnants": 0, "fp_generees": 0, "fp_subies": 0},
                "balle_haute": {"total": 0, "fautes": 0, "gagnants": 0, "fp_generees": 0, "fp_subies": 0},
                "smash": {"total": 0, "fautes": 0, "gagnants": 0, "fp_generees": 0, "fp_subies": 0},
                "lobe": {"total": 0, "fautes": 0, "gagnants": 0, "fp_generees": 0, "fp_subies": 0},
                "amorti": {"total": 0, "fautes": 0, "gagnants": 0, "fp_generees": 0, "fp_subies": 0},
                "bandeja": {"total": 0, "fautes": 0, "gagnants": 0, "fp_generees": 0, "fp_subies": 0},
                "vibora": {"total": 0, "fautes": 0, "gagnants": 0, "fp_generees": 0, "fp_subies": 0},
                "volee": {"total": 0, "fautes": 0, "gagnants": 0, "fp_generees": 0, "fp_subies": 0},
                "fond_de_court": {"total": 0, "fautes": 0, "gagnants": 0, "fp_generees": 0, "fp_subies": 0}
            }
            
            # Mapping des types de coups détaillés vers les catégories techniques
            coup_mapping = {
                "service": ["service"],
                "volee_coup_droit": ["coup_droit", "volee"],
                "volee_revers": ["revers", "volee"],
                "volee_balle_haute": ["balle_haute", "volee"],
                "fond_de_court_coup_droit": ["coup_droit", "fond_de_court"],
                "fond_de_court_revers": ["revers", "fond_de_court"],
                "fond_de_court_balle_haute": ["balle_haute", "fond_de_court"],
                "smash": ["smash"],
                "lobe": ["lobe"],
                "amorti": ["amorti"],
                "bandeja": ["bandeja"],
                "vibora": ["vibora"]
            }
            
            # Agréger les fautes directes
            for type_coup, count in stats[nom]["fautes_directes_detail"].items():
                if type_coup in coup_mapping:
                    for technique in coup_mapping[type_coup]:
                        stats[nom]["coups_techniques"][technique]["total"] += count
                        stats[nom]["coups_techniques"][technique]["fautes"] += count
            
            # Agréger les points gagnants
            for type_coup, count in stats[nom]["points_gagnants_detail"].items():
                if type_coup in coup_mapping:
                    for technique in coup_mapping[type_coup]:
                        stats[nom]["coups_techniques"][technique]["total"] += count
                        stats[nom]["coups_techniques"][technique]["gagnants"] += count
            
            # Agréger les fautes provoquées générées
            for type_coup, count in stats[nom]["fautes_provoquees_generees_detail"].items():
                if type_coup in coup_mapping:
                    for technique in coup_mapping[type_coup]:
                        stats[nom]["coups_techniques"][technique]["total"] += count
                        stats[nom]["coups_techniques"][technique]["fp_generees"] += count
            
            # Agréger les fautes provoquées subies
            for type_coup, count in stats[nom]["fautes_provoquees_subies_detail"].items():
                if type_coup in coup_mapping:
                    for technique in coup_mapping[type_coup]:
                        stats[nom]["coups_techniques"][technique]["total"] += count
                        stats[nom]["coups_techniques"][technique]["fp_subies"] += count
        
        return stats
    
    def get_fautes_provoquees_matrix(self):
        """Calcule la matrice des fautes provoquées : qui provoque à qui"""
        joueurs = self.match_info["joueurs"]
        joueur_names = [
            j if isinstance(j, str) else j.get('nom', j)
            for j in joueurs
        ]
        
        # Initialiser matrice
        matrix = {}
        for attaquant in joueur_names:
            matrix[attaquant] = {}
            for defenseur in joueur_names:
                if attaquant != defenseur:
                    matrix[attaquant][defenseur] = 0
        
        # Compter les fautes provoquées
        for annotation in self.annotations:
            if annotation["type"] == "faute_provoquee":
                attaquant = annotation.get("attaquant")
                defenseur = annotation.get("defenseur")
                
                if attaquant in matrix and defenseur in matrix[attaquant]:
                    matrix[attaquant][defenseur] += 1
        
        return matrix
    
    def get_diagonal_stats(self):
        """Stats des confrontations diagonales (Gauche vs Droite)"""
        joueurs = self.match_info["joueurs"]
        
        # Identifier joueurs gauche et droite par équipe
        equipe1_gauche = None
        equipe1_droite = None
        equipe2_gauche = None
        equipe2_droite = None
        
        for joueur in joueurs:
            if isinstance(joueur, dict):
                nom = joueur['nom']
                position = joueur.get('position', 'gauche')
                equipe = joueur.get('equipe', 1)
                
                if equipe == 1:
                    if position == 'gauche':
                        equipe1_gauche = nom
                    else:
                        equipe1_droite = nom
                else:
                    if position == 'gauche':
                        equipe2_gauche = nom
                    else:
                        equipe2_droite = nom
        
        # Stats pour chaque diagonale
        diagonales = {
            "diagonale_gauche": {  # Gauche Eq1 vs Gauche Eq2
                "joueur1": equipe1_gauche,
                "joueur2": equipe2_gauche,
                "points_joueur1": 0,
                "points_joueur2": 0,
                "fautes_joueur1": 0,
                "fautes_joueur2": 0
            },
            "diagonale_droite": {  # Droite Eq1 vs Droite Eq2
                "joueur1": equipe1_droite,
                "joueur2": equipe2_droite,
                "points_joueur1": 0,
                "points_joueur2": 0,
                "fautes_joueur1": 0,
                "fautes_joueur2": 0
            },
            "croisee_1": {  # Gauche Eq1 vs Droite Eq2
                "joueur1": equipe1_gauche,
                "joueur2": equipe2_droite,
                "points_joueur1": 0,
                "points_joueur2": 0,
                "fautes_joueur1": 0,
                "fautes_joueur2": 0
            },
            "croisee_2": {  # Droite Eq1 vs Gauche Eq2
                "joueur1": equipe1_droite,
                "joueur2": equipe2_gauche,
                "points_joueur1": 0,
                "points_joueur2": 0,
                "fautes_joueur1": 0,
                "fautes_joueur2": 0
            }
        }
        
        # Compter les points et fautes pour chaque confrontation
        for annotation in self.annotations:
            if annotation["type"] in ["faute_directe", "point_gagnant"]:
                joueur = annotation.get("joueur")
                
                # Déterminer dans quelle confrontation
                for diag_name, diag_data in diagonales.items():
                    if joueur == diag_data["joueur1"]:
                        if annotation["type"] == "point_gagnant":
                            diag_data["points_joueur1"] += 1
                        elif annotation["type"] == "faute_directe":
                            diag_data["fautes_joueur1"] += 1
                    elif joueur == diag_data["joueur2"]:
                        if annotation["type"] == "point_gagnant":
                            diag_data["points_joueur2"] += 1
                        elif annotation["type"] == "faute_directe":
                            diag_data["fautes_joueur2"] += 1
        
        return diagonales
    
    def get_player_progression(self, joueur):
        """Calcule la progression d'un joueur au fil du match"""
        # Diviser le match en tranches temporelles
        annotations_joueur = [
            a for a in self.annotations
            if a.get("joueur") == joueur or a.get("player") == joueur
        ]
        
        if not annotations_joueur:
            return []
        
        # Diviser en 10 tranches (10%)
        total_time = (
            max(a.get("timestamp", 0) for a in self.annotations)
            if self.annotations else 0
        )
        if total_time == 0:
            return []
        
        nb_tranches = 10
        tranche_duration = total_time / nb_tranches
        
        progression = []
        for i in range(nb_tranches):
            start_time = i * tranche_duration
            end_time = (i + 1) * tranche_duration
            
            annot_tranche = [
                a for a in annotations_joueur
                if start_time <= a.get("timestamp", 0) < end_time
            ]
            
            fautes = sum(
                1 for a in annot_tranche if a.get("type") == "faute_directe"
            )
            points = sum(
                1 for a in annot_tranche if a.get("type") == "point_gagnant"
            )
            total = len(annot_tranche)
            
            efficacite = (points / total * 100) if total > 0 else 0
            
            progression.append({
                "tranche": i + 1,
                "pourcentage_match": (i + 1) * 10,
                "fautes": fautes,
                "points": points,
                "total_actions": total,
                "efficacite": round(efficacite, 1)
            })
        
        return progression
    
    def get_capture_path(self, point_id):
        """Génère le dossier de capture pour un point (10 frames)"""
        point_folder = os.path.join(
            self.screens_folder, f"point_{point_id:03d}"
        )
        os.makedirs(point_folder, exist_ok=True)
        return point_folder
    
    def export_to_dict(self):
        """Exporte toutes les données en dictionnaire"""
        match_info = dict(self.match_info)
        match_info["position_changes"] = self.position_changes
        data = {
            "match": match_info,
            "points": self.annotations,
            "stats": self.get_stats()
        }
        return data

    def add_position_change(self, timestamp, positions):
        """Ajoute un changement de positions à partir d'un timestamp."""
        try:
            self.position_changes.append({
                "timestamp": float(timestamp or 0.0),
                "positions": positions
            })
            self.position_changes.sort(key=lambda x: x["timestamp"])
            return True
        except Exception:
            return False

    def resolve_positions_for_timestamp(self, ts):
        """Retourne les positions applicables pour un instant ts."""
        if not self.position_changes:
            return []
        applicable = self.position_changes[0]["positions"]
        for change in self.position_changes:
            if ts >= change["timestamp"]:
                applicable = change["positions"]
            else:
                break
        return applicable
    
    def load_from_dict(self, data):
        """Charge les données depuis un dictionnaire"""
        self.match_info = data.get("match", self.match_info) or self.match_info
        self.annotations = data.get("points", []) or []

        # Récupère l'historique des positions depuis le fichier.
        raw_position_changes = []
        try:
            raw_position_changes = (
                self.match_info.get("position_changes")
                or data.get("position_changes")
                or []
            )
        except Exception:
            raw_position_changes = []

        self.position_changes = []
        for item in raw_position_changes:
            try:
                ts = float(item.get("timestamp", 0.0))
                positions = item.get("positions", [])
                if isinstance(positions, list):
                    self.position_changes.append({
                        "timestamp": ts,
                        "positions": positions
                    })
            except Exception:
                continue
        self.position_changes.sort(key=lambda x: x["timestamp"])

        # Normalise les points (timestamp/id) pour fiabiliser la timeline après reprise.
        normalized_points = []
        fps_guess = 25.0
        for idx, point in enumerate(self.annotations, start=1):
            if not isinstance(point, dict):
                continue
            item = dict(point)
            if not isinstance(item.get("id"), int):
                item["id"] = idx

            ts = item.get("timestamp")
            if ts is None:
                frame = item.get("frame")
                if frame is not None:
                    try:
                        ts = float(frame) / fps_guess
                    except Exception:
                        ts = 0.0
                else:
                    ts = 0.0
            try:
                item["timestamp"] = round(float(ts), 3)
            except Exception:
                item["timestamp"] = 0.0
            normalized_points.append(item)

        normalized_points.sort(
            key=lambda p: (float(p.get("timestamp", 0.0)), int(p.get("id", 0)))
        )
        self.annotations = normalized_points

        if self.annotations:
            self.current_point_id = max(int(p.get("id", 0)) for p in self.annotations) + 1
        else:
            self.current_point_id = 1
    
    def remove_last(self):
        """Supprime le dernier point annoté"""
        if self.annotations:
            removed = self.annotations.pop()
            self.autosave()
            return removed
        return None
    
    def clear_all(self):
        """Efface toutes les annotations"""
        self.annotations = []
        self.current_point_id = 1
