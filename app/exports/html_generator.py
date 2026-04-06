"""
Génération de rapports HTML avec statistiques
"""

import os
import json
from datetime import datetime
from .type_coup_labels import TYPE_COUP_LABELS_V2


class HTMLGenerator:
    def __init__(self, template_path="assets/report_template.html"):
        self.template_path = template_path
    
    def _generate_screenshots_on_demand(
        self, annotation_manager, points, video_player,
        num_frames=10, logger=None
    ):
        """
        Génère les captures pour les points sans capture.
        Appelée seulement pendant la génération du rapport.
        
        Args:
            annotation_manager: Instance de AnnotationManager
            points: Liste des points annotés
            video_player: Instance de VideoPlayer pour capturer les frames
        """
        try:
            import cv2
        except Exception:
            if logger:
                logger.warning("OpenCV indisponible: captures du rapport ignorees")
            return

        # Trier par frame pour minimiser les seeks
        sortable = []
        for p in points:
            if p.get("capture") is None:
                sortable.append((p.get("frame", 0), p))
        sortable.sort(key=lambda x: x[0])
        
        if logger:
            msg = (
                f"Génération des captures pour {len(sortable)} points "
                f"(num_frames={num_frames})"
            )
            logger.info(msg)
        
        # Sauvegarder la position actuelle de la vidéo une seule fois
        original_frame = (
            video_player.current_frame
            if hasattr(video_player, 'current_frame') else 0
        )
        
        for frame_num, point in sortable:
            try:
                point_id = point.get("id", 0)
                capture_folder = annotation_manager.get_capture_path(point_id)
                # Si des images existent déjà, sauter
                if (
                    os.path.exists(capture_folder)
                    and os.listdir(capture_folder)
                ):
                    point["capture"] = f"screens/point_{point_id:03d}"
                    continue
                os.makedirs(capture_folder, exist_ok=True)
                if video_player.cap:
                    video_player.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                    video_player.capture_frames_before(
                        capture_folder, num_frames=num_frames
                    )
                point["capture"] = f"screens/point_{point_id:03d}"
            except Exception as e:
                if logger:
                    logger.warning(
                        f"Capture échouée pour point {point.get('id')}: {e}"
                    )
        
        # Restaurer la position originale
        try:
            if video_player.cap:
                video_player.cap.set(cv2.CAP_PROP_POS_FRAMES, original_frame)
        except Exception:
            pass
    
    def generate_report(
        self, annotation_manager, output_path=None, video_player=None,
        fast_mode=False, num_frames=6, logger=None
    ):
        """
        Génère un rapport HTML avec statistiques
        
        Args:
            annotation_manager: Instance de AnnotationManager
            output_path: Chemin du fichier de sortie (optionnel)
            video_player: Instance de VideoPlayer pour générer les captures
                à la demande (optionnel)
        
        Returns:
            str: Chemin du fichier créé
        """
        data = annotation_manager.export_to_dict()
        stats = data.get("stats", {})
        match_info = data.get("match", {})
        points = data.get("points", [])
        
        # Générer les captures d'écran à la demande si video_player est fourni
        if video_player is not None and not fast_mode:
            self._generate_screenshots_on_demand(
                annotation_manager, points, video_player,
                num_frames=num_frames, logger=logger
            )
        elif logger and fast_mode:
            logger.info("Mode rapide activé: génération des captures ignorée")
        
        # Générer un nom de fichier si non fourni
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(
                annotation_manager.data_folder,
                f"rapport_{timestamp}.html"
            )
        
        # Générer le HTML
        html = self._generate_html(
            match_info, stats, points, annotation_manager
        )
        
        # Écrire le fichier
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        return output_path
    
    def _analyze_chronology(self, points, joueurs, max_timestamp):
        """Analyse la répartition chronologique des points"""
        if not points or max_timestamp == 0:
            return {}
        
        # Diviser en 5 tranches de 20%
        tranches = [
            ("0-20%", 0, 0.2),
            ("20-40%", 0.2, 0.4),
            ("40-60%", 0.4, 0.6),
            ("60-80%", 0.6, 0.8),
            ("80-100%", 0.8, 1.0)
        ]
        
        # Initialiser les stats par joueur et par tranche
        chronology = {}
        for joueur in joueurs:
            chronology[joueur] = {
                'tranches': {},
                'total_fautes': 0,
                'total_gagnants': 0
            }
            for label, _, _ in tranches:
                chronology[joueur]['tranches'][label] = {
                    'fautes_directes': 0,
                    'points_gagnants': 0,
                    'fautes_provoquees_gen': 0,
                    'fautes_provoquees_sub': 0
                }
        
        # Analyser chaque point
        for point in points:
            timestamp = point.get('timestamp', 0)
            point_type = point.get('type', '')
            
            # Déterminer la tranche temporelle (% du match)
            percentage = timestamp / max_timestamp if max_timestamp > 0 else 0
            
            # Trouver la tranche correspondante
            tranche_label = None
            for label, start, end in tranches:
                is_last = (percentage == 1.0 and end == 1.0)
                if start <= percentage < end or is_last:
                    tranche_label = label
                    break
            
            if not tranche_label:
                continue
            
            # Compter selon le type de point
            if point_type == 'faute_directe':
                joueur = point.get('joueur', '')
                if joueur in chronology:
                    chronology[joueur]['tranches'][tranche_label][
                        'fautes_directes'
                    ] += 1
                    chronology[joueur]['total_fautes'] += 1
            
            elif point_type == 'point_gagnant':
                joueur = point.get('joueur', '')
                if joueur in chronology:
                    chronology[joueur]['tranches'][tranche_label][
                        'points_gagnants'
                    ] += 1
                    chronology[joueur]['total_gagnants'] += 1
            
            elif point_type == 'faute_provoquee':
                attaquant = point.get('attaquant', '')
                defenseur = point.get('defenseur', '')
                if attaquant in chronology:
                    chronology[attaquant]['tranches'][tranche_label][
                        'fautes_provoquees_gen'
                    ] += 1
                if defenseur in chronology:
                    chronology[defenseur]['tranches'][tranche_label][
                        'fautes_provoquees_sub'
                    ] += 1
        
        return chronology
    
    def _calculer_stats_avancees_chrono(self, data_joueur_tranches):
        """Calcule les stats avancées pour chaque tranche d'un joueur"""
        stats_avancees = {}
        
        for tranche, data in data_joueur_tranches.items():
            fd = data.get('fautes_directes', 0)
            pg = data.get('points_gagnants', 0)
            fp = data.get('fautes_provoquees_gen', 0)
            fs = data.get('fautes_provoquees_sub', 0)
            
            total_actions = fd + pg + fp + fs
            ratio_efficacite = round((pg + fp) / (fd + fs), 2) if (fd + fs) > 0 else 0
            pct_positives = round((pg + fp) / total_actions * 100, 1) if total_actions > 0 else 0
            
            stats_avancees[tranche] = {
                'total_actions': total_actions,
                'fautes_directes': fd,
                'points_gagnants': pg,
                'fautes_provoquees': fp,
                'fautes_subies': fs,
                'ratio_efficacite': ratio_efficacite,
                'pct_positives': pct_positives
            }
        
        return stats_avancees
    
    def _generer_html_tableau_chrono_avance(self, chronology_data, joueurs):
        """Génère le HTML pour les tableaux chronologiques avancés (un tableau par joueur)"""
        couleurs_joueurs = {
            joueurs[0]: "#667eea",
            joueurs[1]: "#ff6b6b",
            joueurs[2]: "#51cf66",
            joueurs[3]: "#ffd43b"
        } if len(joueurs) >= 4 else {j: "#667eea" for j in joueurs}
        
        html = """
            <div class="section">
                <h2>📊 Analyse Chronologique Avancée</h2>
                <p style="color: #666; margin-bottom: 30px;">Évolution des statistiques par tranches de 20% du match</p>
"""
        
        # Générer un tableau pour chaque joueur
        for joueur in joueurs:
            player_data = chronology_data.get(joueur, {}).get('tranches', {})
            stats_avancees = self._calculer_stats_avancees_chrono(player_data)
            couleur = couleurs_joueurs.get(joueur, "#667eea")
            
            html += f"""
                <div style="margin-bottom: 50px; padding: 30px; background: #f8f9fa; border-radius: 12px;">
                    <h3 style="color: {couleur}; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 3px solid {couleur};">📊 {joueur}</h3>
                    <div style="overflow-x: auto; margin: 0 auto;">
                        <table style="width: 100%; border-collapse: collapse; background: white; border-radius: 15px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
                            <thead>
                                <tr style="background: linear-gradient(135deg, {couleur} 0%, #764ba2 100%); color: white;">
                                    <th style="padding: 15px; text-align: left; font-size: 14px; font-weight: 600;">Statistique</th>
                                    <th style="padding: 15px; text-align: center; font-size: 14px; font-weight: 600;">0-20%</th>
                                    <th style="padding: 15px; text-align: center; font-size: 14px; font-weight: 600;">20-40%</th>
                                    <th style="padding: 15px; text-align: center; font-size: 14px; font-weight: 600;">40-60%</th>
                                    <th style="padding: 15px; text-align: center; font-size: 14px; font-weight: 600;">60-80%</th>
                                    <th style="padding: 15px; text-align: center; font-size: 14px; font-weight: 600;">80-100%</th>
                                </tr>
                            </thead>
                            <tbody>
"""
            
            # Lignes de statistiques
            lignes = [
                ("🎾 Total actions", "total_actions"),
                ("⚠️ Fautes directes", "fautes_directes"),
                ("🏆 Points gagnants", "points_gagnants"),
                ("🎯 Fautes provoquées", "fautes_provoquees"),
                ("🚫 Fautes subies", "fautes_subies"),
                ("⚡ Ratio efficacité", "ratio_efficacite"),
                ("💪 % Actions positives", "pct_positives")
            ]
            
            tranches = ["0-20%", "20-40%", "40-60%", "60-80%", "80-100%"]
            
            for i, (label, key) in enumerate(lignes):
                bg = "#f8f9fa" if i % 2 == 0 else "white"
                html += f'                                <tr style="background: {bg};">\n'
                html += f'                                    <td style="padding: 15px; font-weight: 600; color: {couleur}; text-align: left; border-top: 1px solid #e0e0e0;">{label}</td>\n'
                
                # Trouver la meilleure valeur
                valeurs = [stats_avancees.get(t, {}).get(key, 0) for t in tranches]
                if key in ["fautes_directes", "fautes_subies"]:
                    valeurs_non_nulles = [v for v in valeurs if v > 0]
                    best_val = min(valeurs_non_nulles) if valeurs_non_nulles else None
                else:
                    best_val = max(valeurs) if any(v > 0 for v in valeurs) else None
                
                # Ajouter les cellules
                for tranche in tranches:
                    val = stats_avancees.get(tranche, {}).get(key, 0)
                    is_best = (val == best_val and best_val is not None and val != 0)
                    style = 'padding: 15px; text-align: center; border-top: 1px solid #e0e0e0;'
                    if is_best:
                        style += ' font-weight: bold; background: #d3f9d8 !important;'
                    html += f'                                    <td style="{style}">{val}</td>\n'
                
                html += '                                </tr>\n'
            
            html += """
                            </tbody>
                        </table>
                    </div>
                    <div style="text-align: center; margin-top: 12px; color: #666; font-size: 13px; font-style: italic;">
                        💚 Les meilleures valeurs de chaque catégorie sont surlignées en vert
                    </div>
                </div>
"""
        
        html += """
            </div>
"""
        return html
    
    def _generer_html_tableau_chrono_unifie(self, chronology_data, joueurs):
        """Génère le HTML pour le tableau chronologique unifié (comparaison des 4 joueurs)"""
        couleurs_joueurs = {
            joueurs[0]: "#667eea",
            joueurs[1]: "#ff6b6b",
            joueurs[2]: "#51cf66",
            joueurs[3]: "#ffd43b"
        } if len(joueurs) >= 4 else {j: "#667eea" for j in joueurs}
        
        # Calculer les stats avancées pour tous les joueurs
        all_stats = {}
        for joueur in joueurs:
            player_data = chronology_data.get(joueur, {}).get('tranches', {})
            all_stats[joueur] = self._calculer_stats_avancees_chrono(player_data)
        
        tranches = ["0-20%", "20-40%", "40-60%", "60-80%", "80-100%"]
        stats_list = [
            ("⚠️ Fautes directes", "fautes_directes"),
            ("🏆 Points gagnants", "points_gagnants"),
            ("🎯 Fautes provoquées", "fautes_provoquees"),
            ("🚫 Fautes subies", "fautes_subies")
        ]
        
        html = """
            <div class="section">
                <h2>📊 Tableau Chronologique Comparatif</h2>
                <p style="color: #666; text-align: center; margin-bottom: 30px;">Comparaison des 4 joueurs par tranches de 20% du match</p>
"""
        
        # Générer un tableau pour chaque tranche
        for tranche in tranches:
            html += f"""
                <div style="margin-bottom: 50px;">
                    <h3 style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 20px; border-radius: 10px; margin-bottom: 20px; font-size: 1.3em;">🕒 {tranche} du match</h3>
                    <table style="width: 100%; border-collapse: collapse; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                        <thead>
                            <tr style="background: #f8f9fa;">
                                <th style="padding: 15px; text-align: left; font-weight: 600; color: #1e293b; border-bottom: 2px solid #e2e8f0; width: 200px;">Statistique</th>
"""
            
            # En-têtes de colonnes (joueurs)
            for joueur in joueurs:
                couleur = couleurs_joueurs.get(joueur, "#667eea")
                html += f'                                <th style="padding: 15px; text-align: center; font-weight: 700; font-size: 1.1em; color: {couleur}; border-bottom: 2px solid #e2e8f0;">{joueur}</th>\n'
            
            html += """                            </tr>
                        </thead>
                        <tbody>
"""
            
            # Lignes de statistiques
            for label, key in stats_list:
                html += f'                            <tr>\n'
                html += f'                                <td style="padding: 15px; font-weight: 600; text-align: left; color: #667eea; border-bottom: 1px solid #e2e8f0;">{label}</td>\n'
                
                # Valeurs pour chaque joueur
                valeurs = [all_stats[j].get(tranche, {}).get(key, 0) for j in joueurs]
                
                # Trouver la meilleure et la pire valeur
                if key in ["fautes_directes", "fautes_subies"]:
                    valeurs_non_nulles = [v for v in valeurs if v > 0]
                    best = min(valeurs_non_nulles) if valeurs_non_nulles else None
                    worst = max(valeurs) if any(v > 0 for v in valeurs) else None
                else:
                    best = max(valeurs) if any(v > 0 for v in valeurs) else None
                    worst = min(valeurs) if any(v > 0 for v in valeurs) else None
                
                for joueur in joueurs:
                    val = all_stats[joueur].get(tranche, {}).get(key, 0)
                    style = 'padding: 15px; text-align: center; border-bottom: 1px solid #e2e8f0;'
                    
                    # Vérifier si c'est la meilleure ou pire valeur (et qu'il y a une unique meilleure/pire)
                    if val == best and best is not None and val != 0 and valeurs.count(best) == 1:
                        style += ' font-weight: bold; background: #d3f9d8 !important;'
                    elif val == worst and worst is not None and val != 0 and valeurs.count(worst) == 1 and best != worst:
                        style += ' background: #ffe0e0 !important;'
                    
                    html += f'                                <td style="{style}">{val}</td>\n'
                
                html += '                            </tr>\n'
            
            html += """                        </tbody>
                    </table>
                </div>
"""
        
        html += """
                <div style="margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 10px; text-align: center;">
                    <p style="margin: 5px 0; color: #666;"><span style="background: #d3f9d8; padding: 3px 8px; border-radius: 3px; font-weight: bold;">💚 Vert</span> = Meilleure valeur</p>
                    <p style="margin: 5px 0; color: #666;"><span style="background: #ffe0e0; padding: 3px 8px; border-radius: 3px; font-weight: bold;">🔴 Rouge</span> = Pire valeur</p>
                    <p style="margin-top: 15px; color: #999; font-size: 0.9em;">Pour les fautes directes et subies, le meilleur est le plus bas • Pour les points gagnants et fautes provoquées, le meilleur est le plus haut</p>
                </div>
            </div>
"""
        return html
    
    def _calculer_coups_forts_faibles(self, stats, joueurs):
        """Calcule le coup fort (actions positives) et faible (actions négatives) pour chaque joueur"""
        resultats = {}
        
        labels_coups = {
            'volee_coup_droit': 'Volée CD',
            'volee_revers': 'Volée Revers',
            'smash': 'Smash',
            'bandeja': 'Bandeja',
            'vibora': 'Vibora',
            'amorti': 'Amorti',
            'service': 'Service',
            'fond_de_court_coup_droit': 'Fond CD',
            'fond_de_court_revers': 'Fond Revers',
            'fond_de_court_balle_haute': 'Fond Balle Haute',
            'fond_de_court': 'Fond de court'
        }
        
        for joueur in joueurs:
            player_stats = stats.get(joueur, {})
            
            # Actions POSITIVES : points gagnants + fautes provoquées
            pg_detail = player_stats.get('points_gagnants_detail', {})
            fp_detail = player_stats.get('fautes_provoquees_detail', {})
            
            actions_positives = {}
            for coup, count in pg_detail.items():
                actions_positives[coup] = actions_positives.get(coup, 0) + count
            for coup, count in fp_detail.items():
                actions_positives[coup] = actions_positives.get(coup, 0) + count
            
            # Actions NÉGATIVES : fautes directes + fautes subies
            fd_detail = player_stats.get('fautes_directes_detail', {})
            fs_detail = player_stats.get('fautes_subies_detail', {})
            
            actions_negatives = {}
            for coup, count in fd_detail.items():
                actions_negatives[coup] = actions_negatives.get(coup, 0) + count
            for coup, count in fs_detail.items():
                actions_negatives[coup] = actions_negatives.get(coup, 0) + count
            
            # Trouver les coups les plus utilisés (gérer les égalités)
            coups_forts = []
            if actions_positives:
                max_val = max(actions_positives.values())
                coups_forts = [labels_coups.get(c, c) for c, v in actions_positives.items() if v == max_val]
            
            coups_faibles = []
            if actions_negatives:
                max_val = max(actions_negatives.values())
                coups_faibles = [labels_coups.get(c, c) for c, v in actions_negatives.items() if v == max_val]
            
            resultats[joueur] = {
                'coups_forts': coups_forts if coups_forts else ['Aucun'],
                'coups_faibles': coups_faibles if coups_faibles else ['Aucun']
            }
        
        return resultats
    
    def _generate_impact_graph(self, points, joueurs, output_folder):
        """Génère un graphique d'impact des joueurs et le sauvegarde"""
        try:
            import matplotlib
            matplotlib.use('Agg')  # Backend sans interface graphique
            import matplotlib.pyplot as plt
            import numpy as np
            from matplotlib import font_manager
            
            # Calculer l'impact pour chaque joueur
            impact = {joueur: 0 for joueur in joueurs}
            
            for point in points:
                point_type = point.get('type')
                
                if point_type == 'point_gagnant':
                    joueur = point.get('joueur')
                    if joueur in impact:
                        impact[joueur] += 1
                
                elif point_type == 'faute_directe':
                    joueur = point.get('joueur')
                    if joueur in impact:
                        impact[joueur] -= 1
                
                elif point_type == 'faute_provoquee':
                    attaquant = point.get('attaquant')
                    defenseur = point.get('defenseur')
                    if attaquant in impact:
                        impact[attaquant] += 1
                    if defenseur in impact:
                        impact[defenseur] -= 1
            
            # Trier par impact (du meilleur au pire)
            impact_trie = dict(sorted(impact.items(), key=lambda x: x[1], reverse=True))
            
            # Configurer matplotlib pour utiliser la police Inter
            plt.rcParams['font.family'] = 'sans-serif'
            plt.rcParams['font.sans-serif'] = ['Inter', 'DejaVu Sans', 'Arial']
            
            # Créer le graphique avec style amélioré
            fig, ax = plt.subplots(figsize=(14, 8), facecolor='#1a1a2e')
            ax.set_facecolor('#16213e')
            
            # Préparer les données pour le graphique
            noms = list(impact_trie.keys())
            valeurs = list(impact_trie.values())
            
            # Couleurs dégradées pour un meilleur effet visuel
            couleurs = []
            for v in valeurs:
                if v > 3:
                    couleurs.append('#4ecca3')  # Vert éclatant
                elif v > 0:
                    couleurs.append('#51cf66')  # Vert normal
                elif v > -5:
                    couleurs.append('#ff6b6b')  # Rouge normal
                else:
                    couleurs.append('#c92a2a')  # Rouge foncé
            
            # Créer le graphique en barres avec effet 3D
            x_pos = np.arange(len(noms))
            bars = ax.bar(x_pos, valeurs, color=couleurs, edgecolor='white', linewidth=2, 
                           alpha=0.9, width=0.6)
            
            # Ajouter un effet d'ombre
            for i, bar in enumerate(bars):
                height = bar.get_height()
                # Ombre
                ax.bar(i, height, color='black', alpha=0.2, width=0.62, 
                       bottom=min(0, height) - 0.5, zorder=0)
            
            # Ajouter les noms des joueurs AU-DESSUS de chaque barre
            for i, (bar, nom) in enumerate(zip(bars, noms)):
                height = bar.get_height()
                y_offset = 1.5 if height > 0 else -1.5
                
                # Nom du joueur en grand
                ax.text(bar.get_x() + bar.get_width()/2., height + y_offset,
                        nom.upper(),
                        ha='center', va='bottom' if height > 0 else 'top',
                        fontsize=24, fontweight='bold', color='white')
                
                # Valeur de l'impact
                ax.text(bar.get_x() + bar.get_width()/2., height/2,
                        f'{int(height):+d}',
                        ha='center', va='center',
                        fontsize=28, fontweight='bold', color='white')
            
            # Personnaliser le graphique
            ax.set_ylabel('Impact (Points)', fontsize=16, fontweight='bold', color='white')
            ax.set_title('IMPACT DES JOUEURS', fontsize=36, fontweight='bold', 
                         color='white', pad=30)
            ax.axhline(y=0, color='white', linestyle='-', linewidth=1.5, alpha=0.6)
            ax.grid(axis='y', alpha=0.15, linestyle='--', color='white')
            
            # Supprimer les labels de l'axe X (on a les noms au-dessus des barres)
            ax.set_xticks([])
            ax.set_xlabel('')
            
            # Personnaliser les ticks
            ax.tick_params(colors='white', labelsize=12)
            for spine in ax.spines.values():
                spine.set_color('white')
                spine.set_linewidth(1.5)
            
            plt.tight_layout()
            
            # Sauvegarder le graphique
            os.makedirs(output_folder, exist_ok=True)
            graph_path = os.path.join(output_folder, 'impact_joueurs.png')
            plt.savefig(graph_path, dpi=150, facecolor='#1a1a2e', edgecolor='none')
            plt.close()
            
            return 'impact_joueurs.png'
            
        except Exception as e:
            print(f"Erreur lors de la génération du graphique d'impact: {e}")
            return None
    
    def _generate_evolution_graph(self, points, joueurs, output_folder):
        """Génère les graphiques d'évolution temporelle : 1 global + 1 par joueur"""
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import numpy as np
            from matplotlib import font_manager
            
            # Calculer l'évolution de l'impact au fil du match
            evolution = {joueur: [0] for joueur in joueurs}
            impact_cumul = {joueur: 0 for joueur in joueurs}
            
            for point in points:
                point_type = point.get('type')
                
                if point_type == 'point_gagnant':
                    joueur = point.get('joueur')
                    if joueur in impact_cumul:
                        impact_cumul[joueur] += 1
                
                elif point_type == 'faute_directe':
                    joueur = point.get('joueur')
                    if joueur in impact_cumul:
                        impact_cumul[joueur] -= 1
                
                elif point_type == 'faute_provoquee':
                    attaquant = point.get('attaquant')
                    defenseur = point.get('defenseur')
                    if attaquant in impact_cumul:
                        impact_cumul[attaquant] += 1
                    if defenseur in impact_cumul:
                        impact_cumul[defenseur] -= 1
                
                for joueur in joueurs:
                    evolution[joueur].append(impact_cumul[joueur])
            
            # Charger la police Bebas Neue
            bebas_font = None
            font_paths = [
                r'C:\Windows\Fonts\BebasNeue-Regular.ttf',
                r'C:\Windows\Fonts\bebas-neue.ttf',
                r'C:\Windows\Fonts\BebasNeue.ttf',
            ]
            
            for font_path in font_paths:
                if os.path.exists(font_path):
                    bebas_font = font_manager.FontProperties(fname=font_path)
                    break
            
            os.makedirs(output_folder, exist_ok=True)
            colors = ['#4ecca3', '#ffd43b', '#ff6b6b', '#845ef7']
            
            # 1. Graphique GLOBAL avec tous les joueurs
            fig, ax = plt.subplots(figsize=(14, 7), facecolor='#1a1a2e')
            ax.set_facecolor('#16213e')
            
            x = list(range(len(evolution[joueurs[0]])))
            
            for i, joueur in enumerate(joueurs):
                y = evolution[joueur]
                color = colors[i % len(colors)]
                ax.plot(x, y, color=color, linewidth=3, marker='o', markersize=3, 
                        label=joueur.upper(), alpha=0.9)
                ax.fill_between(x, 0, y, color=color, alpha=0.15)
            
            ax.axhline(y=0, color='white', linestyle='-', linewidth=2, alpha=0.5)
            ax.set_xlabel('Points du match', fontsize=16, fontweight='bold', color='white',
                          fontproperties=bebas_font if bebas_font else None)
            ax.set_ylabel('Impact cumulé', fontsize=16, fontweight='bold', color='white',
                          fontproperties=bebas_font if bebas_font else None)
            ax.set_title('ÉVOLUTION GLOBALE', fontsize=32, fontweight='bold', 
                        color='white', pad=20, fontproperties=bebas_font if bebas_font else None)
            ax.grid(True, alpha=0.2, linestyle='--', color='white')
            
            legend = ax.legend(loc='upper left', fontsize=12, framealpha=0.9, facecolor='#16213e', 
                               edgecolor='white', labelcolor='white')
            if bebas_font:
                for text in legend.get_texts():
                    text.set_fontproperties(bebas_font)
            
            ax.tick_params(colors='white', labelsize=11)
            for spine in ax.spines.values():
                spine.set_color('white')
                spine.set_linewidth(1.5)
            
            plt.tight_layout()
            graph_path = os.path.join(output_folder, 'evolution_globale.png')
            plt.savefig(graph_path, dpi=120, facecolor='#1a1a2e', edgecolor='none')
            plt.close()
            
            # 2. Graphiques INDIVIDUELS pour chaque joueur
            filenames = ['evolution_globale.png']
            
            for i, joueur in enumerate(joueurs):
                fig, ax = plt.subplots(figsize=(12, 6), facecolor='#1a1a2e')
                ax.set_facecolor('#16213e')
                
                y = evolution[joueur]
                color = colors[i % len(colors)]
                
                ax.plot(x, y, color=color, linewidth=4, marker='o', markersize=4, alpha=0.9)
                ax.fill_between(x, 0, y, color=color, alpha=0.2)
                
                ax.axhline(y=0, color='white', linestyle='-', linewidth=2, alpha=0.5)
                ax.set_xlabel('Points du match', fontsize=16, fontweight='bold', color='white',
                              fontproperties=bebas_font if bebas_font else None)
                ax.set_ylabel('Impact cumulé', fontsize=16, fontweight='bold', color='white',
                              fontproperties=bebas_font if bebas_font else None)
                ax.set_title(f'{joueur.upper()}', fontsize=32, fontweight='bold', 
                            color=color, pad=20, fontproperties=bebas_font if bebas_font else None)
                ax.grid(True, alpha=0.2, linestyle='--', color='white')
                
                ax.tick_params(colors='white', labelsize=11)
                for spine in ax.spines.values():
                    spine.set_color('white')
                    spine.set_linewidth(1.5)
                
                plt.tight_layout()
                filename = f'evolution_{joueur.lower()}.png'
                graph_path = os.path.join(output_folder, filename)
                plt.savefig(graph_path, dpi=120, facecolor='#1a1a2e', edgecolor='none')
                plt.close()
                filenames.append(filename)
            
            return filenames
            
        except Exception as e:
            print(f"Erreur lors de la génération du graphique d'évolution: {e}")
            return None
    
    def _generate_other_graphs(self, points, joueurs, stats, output_folder):
        """Génère les autres graphiques : efficacité, radar, coups, progression"""
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import numpy as np
            from matplotlib import font_manager
            
            # Charger Bebas Neue
            bebas_font = None
            for font_path in [r'C:\Windows\Fonts\BebasNeue-Regular.ttf', r'C:\Windows\Fonts\bebas-neue.ttf', r'C:\Windows\Fonts\BebasNeue.ttf']:
                if os.path.exists(font_path):
                    bebas_font = font_manager.FontProperties(fname=font_path)
                    break
            
            os.makedirs(output_folder, exist_ok=True)
            colors = ['#4ecca3', '#ffd43b', '#ff6b6b', '#845ef7']
            filenames = []
            
            # 1. EFFICACITÉ PAR JOUEUR
            fig, ax = plt.subplots(figsize=(12, 7), facecolor='#1a1a2e')
            ax.set_facecolor('#16213e')
            
            efficacites = []
            for joueur in joueurs:
                player_stats = stats.get(joueur, {})
                total = player_stats.get('fautes_directes', 0) + player_stats.get('points_gagnants', 0)
                eff = (player_stats.get('points_gagnants', 0) / total * 100) if total > 0 else 0
                efficacites.append(eff)
            
            bars = ax.bar(range(len(joueurs)), efficacites, color=colors[:len(joueurs)], edgecolor='white', linewidth=2, alpha=0.9, width=0.6)
            
            for i, (bar, eff) in enumerate(zip(bars, efficacites)):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height/2, f'{eff:.1f}%',
                        ha='center', va='center', fontsize=24, fontweight='bold', color='white',
                        fontproperties=bebas_font if bebas_font else None)
                ax.text(i, -8, joueurs[i].upper(), ha='center', fontsize=16, fontweight='bold', color='white',
                        fontproperties=bebas_font if bebas_font else None)
            
            ax.set_ylim(0, 100)
            ax.set_ylabel('Efficacité (%)', fontsize=16, fontweight='bold', color='white',
                          fontproperties=bebas_font if bebas_font else None)
            ax.set_title('EFFICACITÉ PAR JOUEUR', fontsize=32, fontweight='bold', color='white', pad=20,
                        fontproperties=bebas_font if bebas_font else None)
            ax.set_xticks([])
            ax.grid(axis='y', alpha=0.2, linestyle='--', color='white')
            ax.tick_params(colors='white', labelsize=12)
            for spine in ax.spines.values():
                spine.set_color('white')
                spine.set_linewidth(1.5)
            
            plt.tight_layout()
            path = os.path.join(output_folder, 'efficacite_joueurs.png')
            plt.savefig(path, dpi=120, facecolor='#1a1a2e', edgecolor='none')
            plt.close()
            filenames.append('efficacite_joueurs.png')
            
            # 2. RADAR DE COMPÉTENCES (moyennes des joueurs)
            fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'), facecolor='#1a1a2e')
            ax.set_facecolor('#16213e')
            
            categories = ['Points\nGagnants', 'Fautes\nProvoquées', 'Précision', 'Défense', 'Attaque']
            num_vars = len(categories)
            angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
            angles += angles[:1]
            
            for i, joueur in enumerate(joueurs):
                player_stats = stats.get(joueur, {})
                pg = player_stats.get('points_gagnants', 0)
                fp = player_stats.get('fautes_provoquees_genere', 0)
                fd = player_stats.get('fautes_directes', 0)
                total = pg + fd if (pg + fd) > 0 else 1
                precision = (pg / total) * 100
                defense = fp * 10
                attaque = pg * 10
                
                values = [pg * 5, fp * 5, precision, defense, attaque]
                max_val = max(values) if max(values) > 0 else 1
                values = [v/max_val*100 for v in values]
                values += values[:1]
                
                ax.plot(angles, values, 'o-', linewidth=2, label=joueur.upper(), color=colors[i])
                ax.fill(angles, values, alpha=0.15, color=colors[i])
            
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(categories, color='white', fontsize=11, fontweight='bold')
            ax.set_ylim(0, 100)
            ax.set_yticks([25, 50, 75, 100])
            ax.set_yticklabels(['25', '50', '75', '100'], color='white', fontsize=9)
            ax.grid(color='white', alpha=0.3)
            ax.set_title('RADAR DE COMPÉTENCES', fontsize=28, fontweight='bold', color='white', pad=30,
                        fontproperties=bebas_font if bebas_font else None, y=1.08)
            legend = ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=11, framealpha=0.9, facecolor='#16213e', edgecolor='white', labelcolor='white')
            if bebas_font:
                for text in legend.get_texts():
                    text.set_fontproperties(bebas_font)
            
            plt.tight_layout()
            path = os.path.join(output_folder, 'radar_competences.png')
            plt.savefig(path, dpi=120, facecolor='#1a1a2e', edgecolor='none', bbox_inches='tight')
            plt.close()
            filenames.append('radar_competences.png')
            
            # 3. RÉPARTITION DES COUPS GAGNANTS
            coups_data = {}
            for joueur in joueurs:
                player_stats = stats.get(joueur, {})
                pg_detail = player_stats.get('points_gagnants_detail', {})
                for coup, count in pg_detail.items():
                    if coup not in coups_data:
                        coups_data[coup] = []
                    coups_data[coup].append(count)
            
            if coups_data:
                fig, ax = plt.subplots(figsize=(12, 7), facecolor='#1a1a2e')
                ax.set_facecolor('#16213e')
                
                x = np.arange(len(coups_data))
                width = 0.8 / len(joueurs)
                
                for i, joueur in enumerate(joueurs):
                    player_stats = stats.get(joueur, {})
                    pg_detail = player_stats.get('points_gagnants_detail', {})
                    values = [pg_detail.get(coup, 0) for coup in coups_data.keys()]
                    ax.bar(x + i * width, values, width, label=joueur.upper(), color=colors[i], alpha=0.9, edgecolor='white', linewidth=1)
                
                ax.set_xlabel('Type de coup', fontsize=14, fontweight='bold', color='white',
                              fontproperties=bebas_font if bebas_font else None)
                ax.set_ylabel('Nombre', fontsize=14, fontweight='bold', color='white',
                              fontproperties=bebas_font if bebas_font else None)
                ax.set_title('RÉPARTITION DES COUPS GAGNANTS', fontsize=28, fontweight='bold', color='white', pad=20,
                            fontproperties=bebas_font if bebas_font else None)
                ax.set_xticks(x + width * (len(joueurs)-1) / 2)
                ax.set_xticklabels(coups_data.keys(), rotation=45, ha='right', color='white', fontsize=10)
                ax.grid(axis='y', alpha=0.2, linestyle='--', color='white')
                ax.tick_params(colors='white', labelsize=11)
                for spine in ax.spines.values():
                    spine.set_color('white')
                    spine.set_linewidth(1.5)
                
                legend = ax.legend(fontsize=11, framealpha=0.9, facecolor='#16213e', edgecolor='white', labelcolor='white')
                if bebas_font:
                    for text in legend.get_texts():
                        text.set_fontproperties(bebas_font)
                
                plt.tight_layout()
                path = os.path.join(output_folder, 'coups_gagnants.png')
                plt.savefig(path, dpi=120, facecolor='#1a1a2e', edgecolor='none')
                plt.close()
                filenames.append('coups_gagnants.png')
            
            # 4. MOMENTUM DU MATCH (Équipe Gauche vs Équipe Droite)
            fig, ax = plt.subplots(figsize=(14, 7), facecolor='#1a1a2e')
            ax.set_facecolor('#16213e')
            
            # Identifier les équipes (positions gauche/droite)
            equipe_gauche = []
            equipe_droite = []
            for joueur in joueurs:
                # On suppose que les 2 premiers sont à gauche, les 2 derniers à droite
                if len(equipe_gauche) < 2:
                    equipe_gauche.append(joueur)
                else:
                    equipe_droite.append(joueur)
            
            momentum = [0]  # Commence à l'équilibre
            score_momentum = 0
            
            for point in points:
                point_type = point.get('type')
                joueur = point.get('joueur')
                attaquant = point.get('attaquant')
                defenseur = point.get('defenseur')
                
                # Point pour équipe gauche = +1, équipe droite = -1
                if point_type == 'point_gagnant':
                    if joueur in equipe_gauche:
                        score_momentum += 1
                    elif joueur in equipe_droite:
                        score_momentum -= 1
                
                elif point_type == 'faute_directe':
                    if joueur in equipe_gauche:
                        score_momentum -= 1
                    elif joueur in equipe_droite:
                        score_momentum += 1
                
                elif point_type == 'faute_provoquee':
                    if attaquant in equipe_gauche:
                        score_momentum += 1
                    elif attaquant in equipe_droite:
                        score_momentum -= 1
                    
                    if defenseur in equipe_gauche:
                        score_momentum -= 1
                    elif defenseur in equipe_droite:
                        score_momentum += 1
                
                momentum.append(score_momentum)
            
            x = range(len(momentum))
            y = momentum
            
            # Créer un dégradé de couleur selon le momentum
            colors_momentum = []
            for val in y:
                if val > 0:
                    intensity = min(abs(val) / max(abs(max(y)), abs(min(y)), 1), 1)
                    colors_momentum.append((78/255, 204/255, 163/255, intensity * 0.5))  # Vert
                else:
                    intensity = min(abs(val) / max(abs(max(y)), abs(min(y)), 1), 1)
                    colors_momentum.append((255/255, 107/255, 107/255, intensity * 0.5))  # Rouge
            
            ax.plot(x, y, color='white', linewidth=3, alpha=0.9)
            ax.fill_between(x, 0, y, color='#4ecca3', where=[v >= 0 for v in y], alpha=0.3, label=f'{" & ".join(equipe_gauche)}')
            ax.fill_between(x, 0, y, color='#ff6b6b', where=[v < 0 for v in y], alpha=0.3, label=f'{" & ".join(equipe_droite)}')
            
            ax.axhline(y=0, color='white', linestyle='-', linewidth=2, alpha=0.6)
            ax.set_xlabel('Points du match', fontsize=14, fontweight='bold', color='white',
                          fontproperties=bebas_font if bebas_font else None)
            ax.set_ylabel('Momentum (← Droite | Gauche →)', fontsize=14, fontweight='bold', color='white',
                          fontproperties=bebas_font if bebas_font else None)
            ax.set_title('MOMENTUM DU MATCH', fontsize=28, fontweight='bold', color='white', pad=20,
                        fontproperties=bebas_font if bebas_font else None)
            ax.grid(True, alpha=0.2, linestyle='--', color='white', axis='y')
            ax.tick_params(colors='white', labelsize=11)
            for spine in ax.spines.values():
                spine.set_color('white')
                spine.set_linewidth(1.5)
            
            legend = ax.legend(fontsize=11, framealpha=0.9, facecolor='#16213e', edgecolor='white', labelcolor='white')
            if bebas_font:
                for text in legend.get_texts():
                    text.set_fontproperties(bebas_font)
            
            plt.tight_layout()
            path = os.path.join(output_folder, 'momentum_match.png')
            plt.savefig(path, dpi=120, facecolor='#1a1a2e', edgecolor='none')
            plt.close()
            filenames.append('momentum_match.png')
            
            return filenames
            
        except Exception as e:
            print(f"Erreur lors de la génération des autres graphiques: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _generate_html(self, match_info, stats, points,
                       annotation_manager=None):
        """Génère le contenu HTML du rapport"""
        
        # Normaliser les noms des joueurs (liste de chaînes)
        raw_joueurs = match_info.get("joueurs", [])
        joueurs = [
            (j if isinstance(j, str) else str(j.get("nom", "Joueur")))
            for j in raw_joueurs
        ]
        date = match_info.get("date", "")
        video = match_info.get("video", "")
        
        # Calculer les totaux
        total_points = len(points)
        total_fautes = sum(1 for p in points if p["type"] == "faute_directe")
        total_gagnants = sum(1 for p in points if p["type"] == "point_gagnant")
        total_provoquees = sum(
            1 for p in points if p["type"] == "faute_provoquee"
        )
        # Calculer les fautes subies (somme des fautes_provoquees_subies de tous les joueurs)
        total_fautes_subies = sum(
            stats.get(j, {}).get('fautes_provoquees_subies', 0) for j in joueurs
        )
        
        # Calculer la durée totale de la vidéo (timestamp max)
        max_timestamp = (
            max([p.get("timestamp", 0) for p in points]) if points else 0
        )
        
        # Analyse chronologique : diviser en 5 tranches de 20%
        chronology_data = self._analyze_chronology(
            points, joueurs, max_timestamp
        )
        
        # Générer le graphique d'impact des joueurs
        impact_graph_filename = None
        if annotation_manager:
            try:
                output_folder = os.path.join(annotation_manager.data_folder, 'graphs')
                impact_graph_filename = self._generate_impact_graph(points, joueurs, output_folder)
                if impact_graph_filename:
                    print(f"OK - Graphique d'impact genere: {impact_graph_filename}")
                else:
                    print(f"ATTENTION - Graphique d'impact non genere (aucune erreur mais retour None)")
            except Exception as e:
                import traceback
                print(f"ERREUR - Impossible de generer le graphique d'impact: {e}")
                traceback.print_exc()
        
        # Générer le graphique d'évolution temporelle
        evolution_graph_filename = None
        if annotation_manager:
            try:
                output_folder = os.path.join(annotation_manager.data_folder, 'graphs')
                evolution_graph_filename = self._generate_evolution_graph(points, joueurs, output_folder)
                if evolution_graph_filename:
                    print(f"OK - Graphique d'evolution genere: {evolution_graph_filename}")
                else:
                    print(f"ATTENTION - Graphique d'evolution non genere (aucune erreur mais retour None)")
            except Exception as e:
                import traceback
                print(f"ERREUR - Impossible de generer le graphique d'evolution: {e}")
                traceback.print_exc()
        
        # Générer les autres graphiques (efficacité, radar, coups, progression)
        other_graphs = None
        if annotation_manager:
            try:
                output_folder = os.path.join(annotation_manager.data_folder, 'graphs')
                other_graphs = self._generate_other_graphs(points, joueurs, stats, output_folder)
                if other_graphs:
                    print(f"OK - Autres graphiques generes: {other_graphs}")
                else:
                    print(f"ATTENTION - Autres graphiques non generes")
            except Exception as e:
                import traceback
                print(f"ERREUR - Impossible de generer les autres graphiques: {e}")
                traceback.print_exc()
        
        # Récupérer statistiques diagonales si annotation_manager disponible
        diagonales = {}
        if annotation_manager:
            try:
                diagonales = annotation_manager.get_diagonal_stats()
            except AttributeError:
                pass
        
        # Chemin script Chart.js local relatif au dossier du rapport
        # Les rapports sont écrits dans `data/`, les assets sont dans `assets/`
        chartjs_local_src = '../assets/vendor/chart.umd.min.js'

        html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rapport Match Padel - {date}</title>
    <!-- Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <!-- Chart.js locale (préférée) + CDN (sûreté) -->
    <script src="{chartjs_local_src}"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #f5f7fa url('../assets/logo_nanoapp.png') no-repeat center center fixed;
            background-size: contain;
            color: #2d3748;
            line-height: 1.6;
            padding: 20px;
            position: relative;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.75);
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            overflow: hidden;
            position: relative;
            z-index: 10;
        }}
        
        .header {{
            background: transparent url('../images/Gemini_Generated_Image_7wnhob7wnhob7wnh.png') no-repeat center center;
            background-size: cover;
            color: white;
            padding: 48px 40px;
            border: 3px solid #2a4365;
            box-shadow: 0 0 20px rgba(42, 67, 101, 0.6), inset 0 0 20px rgba(42, 67, 101, 0.2);
            position: relative;
        }}
        
        .decorative-image {{
            position: fixed;
            top: 0;
            right: 0;
            width: 100%;
            height: 100%;
            z-index: -1;
            opacity: 0.5;
            object-fit: cover;
        }}
        
        .header h1 {{
            font-size: 2.2em;
            font-weight: 600;
            margin-bottom: 8px;
            letter-spacing: -0.5px;
            text-align: left;
        }}
        
        .header p {{
            font-size: 1em;
            opacity: 0.85;
            font-weight: 400;
            text-align: left;
        }}
        
        .content {{
            padding: 48px 40px;
        }}
        
        .section {{
            margin-bottom: 48px;
        }}
        
        .section h2 {{
            color: #1e293b;
            font-size: 1.6em;
            font-weight: 600;
            margin-bottom: 24px;
            padding-bottom: 12px;
            border-bottom: 2px solid #e2e8f0;
            letter-spacing: -0.3px;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 24px;
            margin-top: 24px;
        }}
        
        .stat-card {{
            background: rgba(255, 255, 255, 0.9);
            padding: 28px;
            border-radius: 8px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
            transition: all 0.2s ease;
        }}
        
        .stat-card:hover {{
            border-color: #0ea5e9;
            box-shadow: 0 4px 12px rgba(14,165,233,0.1);
        }}
        
        .stat-card h3 {{
            color: #1e293b;
            font-size: 1.1em;
            font-weight: 600;
            margin-bottom: 20px;
            letter-spacing: -0.2px;
        }}
        
        .stat-item {{
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #f1f5f9;
        }}
        
        .stat-item:last-child {{
            border-bottom: none;
        }}
        
        .stat-item-header {{
            margin-top: 12px;
            padding-top: 12px;
            border-top: 2px solid #e2e8f0;
        }}
        
        .stat-label-sub {{
            color: #0ea5e9;
            font-weight: 600;
            font-size: 0.9em;
        }}
        
        .stat-item-sub {{
            display: flex;
            justify-content: space-between;
            padding: 6px 0 6px 16px;
            background: #f8fafc;
            margin: 3px 0;
            border-radius: 4px;
            border-left: 3px solid #0ea5e9;
        }}
        
        .stat-label-small {{
            color: #64748b;
            font-size: 0.88em;
        }}
        
        .stat-value-small {{
            color: #1e293b;
            font-weight: 600;
            font-size: 0.88em;
        }}
        
        .stat-label {{
            color: #475569;
            font-weight: 500;
            font-size: 0.95em;
        }}
        
        .stat-value {{
            color: #1e293b;
            font-weight: 700;
            font-size: 1.05em;
        }}
        
        .summary-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        
        .summary-card {{
            background: transparent url('../images/Gemini_Generated_Image_tlbk3ztlbk3ztlbk.png') no-repeat center center;
            background-size: cover;
            color: white;
            padding: 28px;
            border-radius: 12px;
            text-align: center;
            box-shadow: 0 4px 16px rgba(42, 67, 101, 0.3);
            border: 2px solid #2a4365;
        }}
        
        .summary-card h4 {{
            font-size: 0.85em;
            opacity: 1;
            color: #ffffff;
            margin-bottom: 12px;
            text-transform: uppercase;
            letter-spacing: 1.2px;
            font-weight: 600;
            text-shadow: 3px 3px 8px rgba(0, 0, 0, 1), -2px -2px 6px rgba(0, 0, 0, 1), 0 0 10px rgba(0, 0, 0, 1);
        }}
        
        .summary-card .number {{
            font-size: 2.8em;
            font-weight: 700;
            letter-spacing: -1px;
            text-shadow: 3px 3px 6px rgba(0, 0, 0, 0.9), -2px -2px 4px rgba(0, 0, 0, 0.7);
        }}
        
        .points-list {{
            margin-top: 24px;
        }}
        
        .point-item {{
            background: rgba(255, 255, 255, 0.9);
            padding: 24px;
            margin-bottom: 16px;
            border-radius: 8px;
            border-left: 4px solid #0ea5e9;
            border: 1px solid #e2e8f0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        }}
        
        .point-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }}
        
        .point-type {{
            font-weight: 600;
            color: #1e293b;
            font-size: 1.05em;
        }}
        
        .point-time {{
            color: #64748b;
            font-size: 0.88em;
            font-weight: 500;
        }}
        
        .point-details {{
            color: #475569;
            line-height: 1.7;
            font-size: 0.95em;
        }}
        
        .point-capture {{
            margin-top: 16px;
            text-align: center;
        }}
        
        .point-capture img {{
            max-width: 100%;
            border-radius: 6px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: 600;
            margin-left: 8px;
            letter-spacing: 0.3px;
        }}
        
        .badge-faute {{
            background: #fee2e2;
            color: #991b1b;
        }}
        
        .badge-gagnant {{
            background: #dcfce7;
            color: #166534;
        }}
        
        .badge-provoquee {{
            background: #fef3c7;
            color: #92400e;
        }}
        
        @media print {{
            body {{
                background: white;
            }}
            .container {{
                box-shadow: none;
            }}
        }}
        
        /* Media queries pour mobile */
        @media (max-width: 768px) {{
            body {{
                padding: 10px;
            }}
            
            .container {{
                margin: 0;
                border-radius: 0;
                background: rgba(255, 255, 255, 0.95);
            }}
            
            .header {{
                padding: 24px 20px;
            }}
            
            .header h1 {{
                font-size: 1.6em;
            }}
            
            .header p {{
                font-size: 0.9em;
            }}
            
            .content {{
                padding: 20px 16px;
            }}
            
            .section h2 {{
                font-size: 1.3em;
            }}
            
            .summary-cards {{
                grid-template-columns: 1fr;
                gap: 15px;
            }}
            
            .summary-card {{
                padding: 20px;
            }}
            
            .summary-card h4 {{
                font-size: 0.9em;
            }}
            
            .summary-card .number {{
                font-size: 2em;
            }}
            
            .stats-grid {{
                grid-template-columns: 1fr;
                gap: 16px;
            }}
            
            .stat-card {{
                padding: 20px;
            }}
            
            .stat-card h3 {{
                font-size: 1em;
            }}
            
            /* Graphiques responsifs */
            div[style*="grid-template-columns"] {{
                grid-template-columns: 1fr !important;
            }}
            
            /* Ajustement des tableaux */
            table {{
                font-size: 0.85em;
            }}
            
            table td, table th {{
                padding: 8px 4px !important;
            }}
            
            /* Points list */
            .point-item {{
                padding: 16px;
            }}
            
            .point-header {{
                flex-direction: column;
                align-items: flex-start;
                gap: 8px;
            }}
            
            .point-type {{
                font-size: 0.95em;
            }}
            
            /* Badges */
            .badge {{
                font-size: 0.75em;
                padding: 3px 8px;
            }}
        }}
        
        @media (max-width: 480px) {{
            .header h1 {{
                font-size: 1.4em;
            }}
            
            .summary-card .number {{
                font-size: 1.8em;
            }}
            
            .section h2 {{
                font-size: 1.2em;
            }}
            
            table {{
                font-size: 0.75em;
            }}
        }}
    </style>
</head>
<body>
    <img src="../images/cgnngcncggc.jpg" alt="Decorative" class="decorative-image">
    <div class="container">
        <div class="header">
            <h1>Rapport Match Padel</h1>
            <p>{date} - {video}</p>
        </div>
        
        <div class="content">
            <div class="section">
                <h2>📊 Résumé du match</h2>
                <div class="summary-cards">
                    <div class="summary-card">
                        <h4>Total Points</h4>
                        <div class="number">{total_points}</div>
                    </div>
                    <div class="summary-card">
                        <h4>Fautes Directes</h4>
                        <div class="number">{total_fautes}</div>
                        <p style="font-size: 0.8em; margin-top: 8px; opacity: 0.8;">{(total_fautes/total_points*100) if total_points > 0 else 0:.1f}% du total</p>
                    </div>
                    <div class="summary-card">
                        <h4>Points Gagnants</h4>
                        <div class="number">{total_gagnants}</div>
                        <p style="font-size: 0.8em; margin-top: 8px; opacity: 0.8;">{(total_gagnants/total_points*100) if total_points > 0 else 0:.1f}% du total</p>
                    </div>
                    <div class="summary-card">
                        <h4>Fautes Provoquées</h4>
                        <div class="number">{total_provoquees}</div>
                        <p style="font-size: 0.8em; margin-top: 8px; opacity: 0.8;">{(total_provoquees/total_points*100) if total_points > 0 else 0:.1f}% du total</p>
                    </div>
                    <div class="summary-card">
                        <h4>Ratio Efficacité</h4>
                        <div class="number">{((total_gagnants+total_provoquees)/(total_fautes+1)):.2f}</div>
                        <p style="font-size: 0.8em; margin-top: 8px; opacity: 0.8;">(Gagnants+Provoquées)/Fautes</p>
                    </div>
                    <div class="summary-card">
                        <h4>Durée Match</h4>
                        <div class="number">{int(max_timestamp//60)}:{int(max_timestamp%60):02d}</div>
                        <p style="font-size: 0.8em; margin-top: 8px; opacity: 0.8;">minutes</p>
                    </div>
                </div>
            </div>
"""
        
        # === SECTION GRAPHIQUES DÉTAILLÉS (remontée ici) ===
        html += """
            <div class="section">
                <h2>📊 Graphiques détaillés</h2>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 30px; margin-top: 20px;">
                    <div style="background: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); grid-column: 1 / -1;">
                        <h3 style="color: #2c5282; text-align: center; margin-bottom: 12px; font-weight: 600;">⚖️ Impact des joueurs</h3>
                        <p style="color: #718096; text-align: center; font-size: 0.9em; margin-bottom: 20px;">Contribution nette de chaque joueur au match : points gagnants + fautes provoquées − fautes directes − fautes subies</p>"""
        
        # Afficher l'image PNG si elle existe, sinon le canvas Chart.js
        if impact_graph_filename:
            html += f"""
                        <div style="text-align: center;">
                            <img src="graphs/{impact_graph_filename}" 
                                 style="max-width: 100%; height: auto; border-radius: 10px; cursor: pointer;"
                                 onclick="this.requestFullscreen()"
                                 title="Cliquez pour afficher en plein écran">
                        </div>"""
        else:
            html += """
                        <canvas id="impactChart"></canvas>"""
        
        html += """
                    </div>
                    <div style="background: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); grid-column: 1 / -1;">
                        <h3 style="color: #2c5282; text-align: center; margin-bottom: 12px; font-weight: 600;">⏱️ Évolution temporelle</h3>
                        <p style="color: #718096; text-align: center; font-size: 0.9em; margin-bottom: 20px;">Progression du score virtuel (momentum) au fil du match pour visualiser les phases dominantes</p>"""
        
        # Afficher les 5 graphiques (global + 4 individuels)
        if evolution_graph_filename and isinstance(evolution_graph_filename, list):
            html += """
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin-top: 15px;">"""
            
            for i, filename in enumerate(evolution_graph_filename):
                label = "GLOBAL" if i == 0 else joueurs[i-1].upper()
                html += f"""
                            <div style="text-align: center; cursor: pointer;" onclick="document.getElementById('modal-{i}').style.display='block'">
                                <p style="font-weight: bold; color: #667eea; margin-bottom: 8px; font-size: 13px;">{label}</p>
                                <img src="graphs/{filename}" 
                                     style="width: 100%; height: auto; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.15); transition: transform 0.2s;"
                                     onmouseover="this.style.transform='scale(1.03)'"
                                     onmouseout="this.style.transform='scale(1)'"
                                     title="Cliquez pour agrandir">
                            </div>
                            
                            <!-- Modal pour {label} -->
                            <div id="modal-{i}" style="display: none; position: fixed; z-index: 9999; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.95); padding: 20px;">
                                <span style="position: absolute; top: 20px; right: 40px; color: white; font-size: 45px; font-weight: bold; cursor: pointer; z-index: 10000;"
                                      onclick="document.getElementById('modal-{i}').style.display='none'">&times;</span>
                                <img src="graphs/{filename}" 
                                     style="margin: auto; display: block; max-width: 95%; max-height: 95%; object-fit: contain; margin-top: 3%;">
                            </div>"""
            
            html += """
                        </div>"""
        
        html += """
                    </div>
                    <div style="background: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
                        <h3 style="color: #2c5282; text-align: center; margin-bottom: 12px; font-weight: 600;">🎾 Répartition des coups gagnants</h3>
                        <p style="color: #718096; text-align: center; font-size: 0.9em; margin-bottom: 20px;">Analyse des types de coups ayant généré des points gagnants durant le match</p>"""
        
        if other_graphs and len(other_graphs) > 2:
            html += f"""
                        <img src="graphs/{other_graphs[2]}" style="width: 100%; height: auto; cursor: pointer;" 
                             onclick="this.requestFullscreen()" title="Cliquez pour agrandir">"""
        else:
            html += """
                        <canvas id="coupsChart"></canvas>"""
        
        html += """
                    </div>
                    <div style="background: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
                        <h3 style="color: #2c5282; text-align: center; margin-bottom: 12px; font-weight: 600;">🎯 Radar de compétences</h3>
                        <p style="color: #718096; text-align: center; font-size: 0.9em; margin-bottom: 20px;">Profil technique multidimensionnel de chaque joueur (attaque, défense, précision, agressivité)</p>"""
        
        if other_graphs and len(other_graphs) > 1:
            html += f"""
                        <img src="graphs/{other_graphs[1]}" style="width: 100%; height: auto; cursor: pointer;" 
                             onclick="this.requestFullscreen()" title="Cliquez pour agrandir">"""
        else:
            html += """
                        <canvas id="radarChart"></canvas>"""
        
        html += """
                    </div>
                    <div style="background: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
                        <h3 style="color: #2c5282; text-align: center; margin-bottom: 12px; font-weight: 600;">📉 Efficacité par joueur</h3>
                        <p style="color: #718096; text-align: center; font-size: 0.9em; margin-bottom: 20px;">Pourcentage d'actions positives par rapport au total des actions effectuées</p>"""
        
        if other_graphs and len(other_graphs) > 0:
            html += f"""
                        <img src="graphs/{other_graphs[0]}" style="width: 100%; height: auto; cursor: pointer;" 
                             onclick="this.requestFullscreen()" title="Cliquez pour agrandir">"""
        else:
            html += """
                        <canvas id="efficaciteChart"></canvas>"""
        
        html += """
                    </div>
                    <div style="background: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); grid-column: 1 / -1;">
                        <h3 style="color: #2c5282; text-align: center; margin-bottom: 12px; font-weight: 600;">🌊 Momentum du match</h3>
                        <p style="color: #718096; text-align: center; font-size: 0.9em; margin-bottom: 20px;">Évolution de la dynamique du jeu montrant les périodes de domination et les retournements de situation</p>"""
        
        if other_graphs and len(other_graphs) > 3:
            html += f"""
                        <img src="graphs/{other_graphs[3]}" style="width: 100%; height: auto; cursor: pointer;" 
                             onclick="this.requestFullscreen()" title="Cliquez pour agrandir">"""
        else:
            html += """
                        <canvas id="momentumChart"></canvas>"""
        
        html += """
                    </div>
                </div>
            </div>
            
            <div class="section">
                <h2>⚡ Indicateurs de Performance</h2>
                <div class="stats-grid">
"""
        
        # Calculer les indicateurs de performance pour chaque joueur
        for joueur in joueurs:
            player_stats = stats.get(joueur, {})
            fd = player_stats.get('fautes_directes', 0)
            pg = player_stats.get('points_gagnants', 0)
            fp_gen = player_stats.get('fautes_provoquees_generees', 0)
            fp_sub = player_stats.get('fautes_provoquees_subies', 0)
            
            total_actions = fd + pg + fp_gen + fp_sub
            ratio_positif = (pg + fp_gen) / (fd + fp_sub + 1)
            efficacite = (
                ((pg + fp_gen) / total_actions * 100) if total_actions > 0 else 0
            )
            agressivite = ((pg + fp_gen) / (pg + fp_gen + fd + 1) * 100) if (pg + fp_gen + fd) > 0 else 0
            
            html += f"""
                    <div class="stat-card">
                        <h3>🎯 {joueur}</h3>
                        <div class="stat-item">
                            <span class="stat-label">💪 Actions totales</span>
                            <span class="stat-value">{total_actions}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">✨ Efficacité globale</span>
                            <span class="stat-value" style="color: {'#51cf66' if efficacite > 50 else '#ff6b6b'};">{efficacite:.1f}%</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">⚔️ Ratio positif/négatif</span>
                            <span class="stat-value" style="color: {'#51cf66' if ratio_positif > 1 else '#ff6b6b'};">{ratio_positif:.2f}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">🚀 Indice d'agressivité</span>
                            <span class="stat-value" style="color: {'#667eea' if agressivite > 60 else '#ffd43b'};">{agressivite:.1f}%</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">🎲 Constance</span>
                            <span class="stat-value" style="color: {'#51cf66' if fd < pg else '#ff6b6b'};">{'Excellent' if fd < pg/2 else 'Bon' if fd < pg else 'À améliorer'}</span>
                        </div>
                    </div>
"""
        
        html += """
                </div>
            </div>
            
            <div class="section">
                <h2>🔥 Analyse des Séquences et Momentum</h2>
                <div class="stats-grid">
"""
        
        # Analyser les séries pour chaque joueur
        for joueur in joueurs:
            # Calculer les séries de réussite
            serie_actuelle = 0
            serie_max = 0
            serie_neg_max = 0
            serie_neg_actuelle = 0
            
            for point in points:
                if point.get('type') == 'point_gagnant' and point.get('joueur') == joueur:
                    serie_actuelle += 1
                    serie_neg_actuelle = 0
                    serie_max = max(serie_max, serie_actuelle)
                elif point.get('type') == 'faute_directe' and point.get('joueur') == joueur:
                    serie_neg_actuelle += 1
                    serie_actuelle = 0
                    serie_neg_max = max(serie_neg_max, serie_neg_actuelle)
                elif point.get('type') == 'faute_provoquee':
                    if point.get('attaquant') == joueur:
                        serie_actuelle += 1
                        serie_neg_actuelle = 0
                        serie_max = max(serie_max, serie_actuelle)
                    elif point.get('defenseur') == joueur:
                        serie_neg_actuelle += 1
                        serie_actuelle = 0
                        serie_neg_max = max(serie_neg_max, serie_neg_actuelle)
            
            html += f"""
                    <div class="stat-card">
                        <h3>📊 {joueur} - Momentum</h3>
                        <div class="stat-item">
                            <span class="stat-label">🔥 Plus longue série positive</span>
                            <span class="stat-value" style="color: #51cf66;">{serie_max} points</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">❄️ Plus longue série négative</span>
                            <span class="stat-value" style="color: #ff6b6b;">{serie_neg_max} fautes</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">🎢 Régularité</span>
                            <span class="stat-value">{'Très régulier' if serie_max < 4 and serie_neg_max < 4 else 'Variable' if serie_max < 6 or serie_neg_max < 6 else 'Irrégulier'}</span>
                        </div>
                    </div>
"""
        
        html += """
                </div>
            </div>
            
            <div class="section">
                <h2>📈 Analyse chronologique</h2>
                <p style="color: #666; margin-bottom: 20px;">Répartition des points dans le temps (par tranche de 20%)</p>
                
                <div class="stats-grid">
"""
        
        # Ajouter les stats chronologiques par joueur
        for joueur in joueurs:
            player_chrono = chronology_data.get(joueur, {})
            tranches_data = player_chrono.get('tranches', {})
            
            html += f"""
                    <div class="stat-card">
                        <h3>{joueur}</h3>
"""
            
            # Afficher chaque tranche (toujours, même avec des zéros)
            tranche_order = ["0-20%", "20-40%", "40-60%", "60-80%", "80-100%"]
            for tranche_label in tranche_order:
                tranche = tranches_data.get(tranche_label, {
                    'fautes_directes': 0,
                    'points_gagnants': 0,
                    'fautes_provoquees_gen': 0,
                    'fautes_provoquees_sub': 0
                })
                fautes = tranche.get('fautes_directes', 0)
                gagnants = tranche.get('points_gagnants', 0)
                prov_gen = tranche.get('fautes_provoquees_gen', 0)
                prov_sub = tranche.get('fautes_provoquees_sub', 0)

                html += f"""
                        <div class="stat-item-header">
                            <span class="stat-label-sub">🕒 {tranche_label} du match</span>
                        </div>
                        <div class="stat-item-sub">
                            <span class="stat-label-small">⚠️ Fautes directes</span>
                            <span class="stat-value-small">{fautes}</span>
                        </div>
                        <div class="stat-item-sub">
                            <span class="stat-label-small">🏆 Points gagnants</span>
                            <span class="stat-value-small">{gagnants}</span>
                        </div>
                        <div class="stat-item-sub">
                            <span class="stat-label-small">🎯 Fautes provoquées</span>
                            <span class="stat-value-small">{prov_gen}</span>
                        </div>
                        <div class="stat-item-sub">
                            <span class="stat-label-small">🚫 Fautes subies</span>
                            <span class="stat-value-small">{prov_sub}</span>
                        </div>
"""
            
            html += """
                    </div>
"""
        
        html += """
                </div>
            </div>
"""
        
        # Ajouter les tableaux chronologiques avancés (nouveau)
        html += self._generer_html_tableau_chrono_avance(chronology_data, joueurs)
        
        # Ajouter le tableau chronologique unifié (nouveau)
        html += self._generer_html_tableau_chrono_unifie(chronology_data, joueurs)
        
        html += """
            <div class="section">
                <h2>⚔️ Confrontations Diagonales</h2>
                <p style="text-align: center; color: #666; margin-bottom: 20px;">Analyse des confrontations Gauche vs Droite</p>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px;">
"""
        
        # Ajouter les statistiques diagonales si disponibles
        if diagonales:
            diag_labels = {
                "diagonale_gauche": "🔵 Gauche vs Gauche",
                "diagonale_droite": "🔴 Droite vs Droite",
                "croisee_1": "🟡 Croisée 1",
                "croisee_2": "🟢 Croisée 2"
            }
            
            for diag_name, diag_data in diagonales.items():
                j1 = diag_data.get("joueur1", "N/A")
                j2 = diag_data.get("joueur2", "N/A")
                pts_j1 = diag_data.get("points_joueur1", 0)
                pts_j2 = diag_data.get("points_joueur2", 0)
                fau_j1 = diag_data.get("fautes_joueur1", 0)
                fau_j2 = diag_data.get("fautes_joueur2", 0)
                
                if j1 != "N/A" and j2 != "N/A":
                    total_j1 = pts_j1 + fau_j1
                    total_j2 = pts_j2 + fau_j2
                    eff_j1 = (pts_j1 / total_j1 * 100) if total_j1 > 0 else 0
                    eff_j2 = (pts_j2 / total_j2 * 100) if total_j2 > 0 else 0
                    
                    html += f"""
                    <div style="background: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
                        <h4 style="color: #667eea; text-align: center; margin-bottom: 15px;">{diag_labels[diag_name]}</h4>
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                            <div style="text-align: center; flex: 1;">
                                <div style="font-weight: bold; font-size: 18px; color: #333;">{j1}</div>
                                <div style="color: #51cf66; font-size: 24px; font-weight: bold; margin: 10px 0;">{pts_j1}</div>
                                <div style="color: #ff6b6b; font-size: 14px;">Fautes: {fau_j1}</div>
                                <div style="color: #667eea; font-size: 14px; margin-top: 5px;">Efficacité: {eff_j1:.1f}%</div>
                            </div>
                            <div style="font-size: 30px; color: #ccc; padding: 0 20px;">VS</div>
                            <div style="text-align: center; flex: 1;">
                                <div style="font-weight: bold; font-size: 18px; color: #333;">{j2}</div>
                                <div style="color: #51cf66; font-size: 24px; font-weight: bold; margin: 10px 0;">{pts_j2}</div>
                                <div style="color: #ff6b6b; font-size: 14px;">Fautes: {fau_j2}</div>
                                <div style="color: #667eea; font-size: 14px; margin-top: 5px;">Efficacité: {eff_j2:.1f}%</div>
                            </div>
                        </div>
                    </div>
"""
        else:
            html += """
                    <div style="background: white; padding: 20px; border-radius: 15px; text-align: center; color: #999;">
                        <p>Statistiques diagonales non disponibles</p>
                        <p style="font-size: 12px;">Définissez les positions (gauche/droite) des joueurs</p>
                    </div>
"""
        
        html += """
                </div>
            </div>
            
            <div class="section">
                <h2>👥 Statistiques détaillées par joueur</h2>
                <div class="stats-grid">
"""
        
        # Statistiques par joueur avec plus de détails
        for joueur in joueurs:
            player_stats = stats.get(joueur, {})
            detail_pg = player_stats.get('points_gagnants_detail', {})
            
            # Calculer les totaux de types de coups
            total_volees = detail_pg.get('volee_coup_droit', 0) + detail_pg.get('volee_revers', 0)
            
            html += f"""
                    <div class="stat-card">
                        <h3>🎾 {joueur}</h3>
                        <div class="stat-item">
                            <span class="stat-label">⚠️ Fautes directes</span>
                            <span class="stat-value">{player_stats.get('fautes_directes', 0)}</span>
                        </div>
"""
            
            # Détail des fautes directes si disponible
            detail_fd = player_stats.get('fautes_directes_detail', {})
            if detail_fd and sum(detail_fd.values()) > 0:
                html += """
                        <div class="stat-item-header">
                            <span class="stat-label-sub">📋 Détail fautes directes :</span>
                        </div>
"""
                type_labels_fd = TYPE_COUP_LABELS_V2.copy()
                
                for key, label in type_labels_fd.items():
                    value = detail_fd.get(key, 0)
                    if value > 0:
                        pourcent = (value / player_stats.get('fautes_directes', 1) * 100)
                        html += f"""
                        <div class="stat-item-sub">
                            <span class="stat-label-small">{label}</span>
                            <span class="stat-value-small">{value} ({pourcent:.0f}%)</span>
                        </div>
"""
            
            html += f"""
                        <div class="stat-item">
                            <span class="stat-label">🏆 Points gagnants</span>
                            <span class="stat-value">{player_stats.get('points_gagnants', 0)}</span>
                        </div>
"""
            
            # Détail des points gagnants si disponible
            if detail_pg and sum(detail_pg.values()) > 0:
                html += """
                        <div class="stat-item-header">
                            <span class="stat-label-sub">📋 Détail points gagnants :</span>
                        </div>
"""
                type_labels = TYPE_COUP_LABELS_V2.copy()
                
                for key, label in type_labels.items():
                    value = detail_pg.get(key, 0)
                    if value > 0:
                        pourcent = (value / player_stats.get('points_gagnants', 1) * 100)
                        html += f"""
                        <div class="stat-item-sub">
                            <span class="stat-label-small">{label}</span>
                            <span class="stat-value-small">{value} ({pourcent:.0f}%)</span>
                        </div>
"""
                
                # Statistiques de tendance
                html += """
                        <div class="stat-item-header">
                            <span class="stat-label-sub">📊 Analyse de jeu :</span>
                        </div>
"""
                
                style_jeu = "Agressif au filet" if total_volees > detail_pg.get('fond_de_court', 0) else "Jeu de fond"
                coup_favori = max(detail_pg.items(), key=lambda x: x[1])[0] if detail_pg else "N/A"
                coup_favori_label = type_labels.get(coup_favori, coup_favori)
                
                html += f"""
                        <div class="stat-item-sub">
                            <span class="stat-label-small">🎯 Style de jeu</span>
                            <span class="stat-value-small">{style_jeu}</span>
                        </div>
                        <div class="stat-item-sub">
                            <span class="stat-label-small">⭐ Coup signature</span>
                            <span class="stat-value-small">{coup_favori_label}</span>
                        </div>
"""
            
            html += f"""
                        <div class="stat-item">
                            <span class="stat-label">🎯 Fautes provoquées</span>
                            <span class="stat-value">{player_stats.get('fautes_provoquees_generees', 0)}</span>
                        </div>
"""
            
            # Détail des fautes provoquées générées si disponible
            detail_fp_gen = player_stats.get('fautes_provoquees_generees_detail', {})
            if detail_fp_gen and sum(detail_fp_gen.values()) > 0:
                html += """
                        <div class="stat-item-header">
                            <span class="stat-label-sub">📋 Détail coups gagnants (attaque) :</span>
                        </div>
"""
                type_labels = TYPE_COUP_LABELS_V2.copy()
                
                for key, label in type_labels.items():
                    value = detail_fp_gen.get(key, 0)
                    if value > 0:
                        total_fp_gen = player_stats.get('fautes_provoquees_generees', 1)
                        pourcent = (value / total_fp_gen * 100)
                        html += f"""
                        <div class="stat-item-sub">
                            <span class="stat-label-small">{label}</span>
                            <span class="stat-value-small">{value} ({pourcent:.0f}%)</span>
                        </div>
"""
            
            html += f"""
                        <div class="stat-item">
                            <span class="stat-label">🚫 Fautes subies</span>
                            <span class="stat-value">{player_stats.get('fautes_provoquees_subies', 0)}</span>
                        </div>
"""
            
            # Détail des fautes provoquées subies si disponible
            detail_fp_sub = player_stats.get('fautes_provoquees_subies_detail', {})
            if detail_fp_sub and sum(detail_fp_sub.values()) > 0:
                html += """
                        <div class="stat-item-header">
                            <span class="stat-label-sub">📋 Détail coups fautifs (défense) :</span>
                        </div>
"""
                type_labels_fp_sub = TYPE_COUP_LABELS_V2.copy()

                for key, label in type_labels_fp_sub.items():
                    value = detail_fp_sub.get(key, 0)
                    if value > 0:
                        total_fp_sub = player_stats.get('fautes_provoquees_subies', 1)
                        pourcent = (value / total_fp_sub * 100)
                        html += f"""
                        <div class="stat-item-sub">
                            <span class="stat-label-small">{label}</span>
                            <span class="stat-value-small">{value} ({pourcent:.0f}%)</span>
                        </div>
"""
            
            html += """
                    </div>
"""
        
        html += """
                </div>
            </div>
            
            <div class="section">
                <h2>🎾 Analyse technique détaillée par coup</h2>
                <div class="stats-grid">
"""
        
        # Afficher les statistiques techniques agrégées pour chaque joueur
        for joueur in joueurs:
            player_stats = stats.get(joueur, {})
            coups_tech = player_stats.get('coups_techniques', {})
            
            html += f"""
                    <div class="stat-card">
                        <h3>🎾 {joueur}</h3>
"""
            
            # Tableau récapitulatif des coups techniques
            techniques = [
                ("Service", "service", "🎾"),
                ("Coup droit", "coup_droit", "🎾"),
                ("Revers", "revers", "🎾"),
                ("Balle haute", "balle_haute", "🎾"),
                ("Smash", "smash", "💥"),
                ("Amorti", "amorti", "🎯"),
                ("Bandeja", "bandeja", "🔥"),
                ("Vibora", "vibora", "🐍"),
                ("Volée", "volee", "⚡"),
                ("Fond de court", "fond_de_court", "⚡")
            ]
            
            for label, key, emoji in techniques:
                coup_stats = coups_tech.get(key, {})
                total = coup_stats.get('total', 0)
                
                if total > 0:
                    fautes = coup_stats.get('fautes', 0)
                    gagnants = coup_stats.get('gagnants', 0)
                    fp_gen = coup_stats.get('fp_generees', 0)
                    fp_sub = coup_stats.get('fp_subies', 0)
                    
                    # Calculer le ratio d'efficacité
                    if total > 0:
                        pct_gagnants = round((gagnants / total) * 100, 1)
                        pct_fautes = round((fautes / total) * 100, 1)
                        pct_fp_gen = round((fp_gen / total) * 100, 1)
                        pct_fp_sub = round((fp_sub / total) * 100, 1)
                    else:
                        pct_gagnants = pct_fautes = pct_fp_gen = pct_fp_sub = 0
                    
                    # Déterminer la couleur selon l'efficacité
                    if gagnants + fp_gen > fautes + fp_sub:
                        color = "#22c55e"  # Vert
                    elif gagnants + fp_gen == fautes + fp_sub:
                        color = "#f59e0b"  # Orange
                    else:
                        color = "#ef4444"  # Rouge
                    
                    html += f"""
                        <div class="stat-item-header" style="margin-top: 12px;">
                            <span class="stat-label-sub" style="font-size: 14px; color: {color};">{emoji} {label} - Total: {total}</span>
                        </div>
                        <div class="stat-item-sub">
                            <span class="stat-label-small">🏆 Gagnants</span>
                            <span class="stat-value-small">{gagnants} ({pct_gagnants}%)</span>
                        </div>
                        <div class="stat-item-sub">
                            <span class="stat-label-small">⚠️ Fautes directes</span>
                            <span class="stat-value-small">{fautes} ({pct_fautes}%)</span>
                        </div>
                        <div class="stat-item-sub">
                            <span class="stat-label-small">🎯 Fautes provoquées</span>
                            <span class="stat-value-small">{fp_gen} ({pct_fp_gen}%)</span>
                        </div>
                        <div class="stat-item-sub">
                            <span class="stat-label-small">🚫 Fautes subies</span>
                            <span class="stat-value-small">{fp_sub} ({pct_fp_sub}%)</span>
                        </div>
"""
            
            html += """
                    </div>
"""
        
        html += """
                </div>
            </div>
"""
        
        # Section Coups Forts / Coups Faibles
        coups_analysis = self._calculer_coups_forts_faibles(stats, joueurs)
        
        html += """
            <div class="section">
                <h2>⚡ Points Forts et Faibles par Joueur</h2>
                <p style="text-align: center; color: #666; margin-bottom: 30px;">Coups les plus efficaces et les plus problématiques de chaque joueur</p>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 24px;">
"""
        
        for joueur in joueurs:
            analysis = coups_analysis.get(joueur, {})
            coups_forts = analysis.get('coups_forts', ['Aucun'])
            coups_faibles = analysis.get('coups_faibles', ['Aucun'])
            
            html += f"""
                    <div style="background: white; padding: 28px; border-radius: 12px; box-shadow: 0 4px 16px rgba(0,0,0,0.08); border-top: 4px solid #2c5282;">
                        <h3 style="color: #2c5282; margin-bottom: 24px; font-size: 1.3em; font-weight: 600;">{joueur}</h3>
                        
                        <div style="margin-bottom: 24px; padding: 20px; background: #e6ffed; border-radius: 8px; border-left: 4px solid #38a169;">
                            <h4 style="color: #276749; margin-bottom: 12px; font-size: 1em; font-weight: 600;">✅ Coup(s) Fort(s)</h4>
                            <p style="color: #2d3748; font-size: 1.1em; font-weight: 500; margin: 0;">{', '.join(coups_forts)}</p>
                            <p style="color: #718096; font-size: 0.85em; margin-top: 6px;">Utilisé le plus pour actions positives</p>
                        </div>
                        
                        <div style="padding: 20px; background: #fff5f5; border-radius: 8px; border-left: 4px solid #e53e3e;">
                            <h4 style="color: #c53030; margin-bottom: 12px; font-size: 1em; font-weight: 600;">⚠️ Coup(s) Faible(s)</h4>
                            <p style="color: #2d3748; font-size: 1.1em; font-weight: 500; margin: 0;">{', '.join(coups_faibles)}</p>
                            <p style="color: #718096; font-size: 0.85em; margin-top: 6px;">Utilisé le plus pour actions négatives</p>
                        </div>
                    </div>
"""
        
        html += """
                </div>
            </div>
"""
        
        html += """
            <div class="section">
                <h2>💡 Analyses tactiques et recommandations</h2>
                <div class="stats-grid">
"""
        
        # Générer des recommandations personnalisées pour chaque joueur
        for joueur in joueurs:
            player_stats = stats.get(joueur, {})
            fd = player_stats.get('fautes_directes', 0)
            pg = player_stats.get('points_gagnants', 0)
            fp_gen = player_stats.get('fautes_provoquees_generees', 0)
            fp_sub = player_stats.get('fautes_provoquees_subies', 0)
            detail_pg = player_stats.get('points_gagnants_detail', {})
            
            # Analyser les points forts et faibles
            points_forts = []
            points_ameliorer = []
            
            if pg > fd:
                points_forts.append("✅ Excellent ratio points gagnants/fautes")
            else:
                points_ameliorer.append("⚠️ Trop de fautes directes par rapport aux points gagnants")
            
            if fp_gen > fp_sub:
                points_forts.append("✅ Génère plus de fautes qu'il n'en subit")
            else:
                points_ameliorer.append("⚠️ Subit plus de pression qu'il n'en crée")
            
            # Analyser le style de jeu
            total_volees = detail_pg.get('volee_coup_droit', 0) + detail_pg.get('volee_revers', 0)
            smashes = detail_pg.get('smash', 0)
            fond = detail_pg.get('fond_de_court', 0)
            
            if total_volees > fond:
                points_forts.append("✅ Très efficace au filet")
            if smashes > 2:
                points_forts.append("✅ Smash performant")
            if fond > total_volees:
                points_ameliorer.append("💡 Pourrait être plus agressif au filet")
            
            # Recommandations
            recommandations = []
            if fd > pg:
                recommandations.append("🎯 Travailler la constance et réduire les fautes non forcées")
            if fp_sub > fp_gen:
                recommandations.append("💪 Développer un jeu plus offensif pour mettre la pression")
            if total_volees < 2 and pg > 3:
                recommandations.append("🏐 Monter plus souvent au filet pour finir les points")
            if smashes == 0 and pg > 5:
                recommandations.append("💥 Travailler le smash pour conclure les échanges")
            
            if not recommandations:
                recommandations.append("🏆 Excellent niveau de jeu, continuez ainsi!")
            
            html += f"""
                    <div class="stat-card">
                        <h3>📊 {joueur} - Analyse</h3>
                        <div style="margin: 15px 0;">
                            <h4 style="color: #51cf66; font-size: 1em; margin-bottom: 10px;">💪 Points forts :</h4>
"""
            
            if points_forts:
                for pf in points_forts:
                    html += f"""
                            <div style="padding: 8px; background: #d3f9d8; border-radius: 4px; margin: 5px 0; font-size: 0.9em;">
                                {pf}
                            </div>
"""
            else:
                html += """
                            <div style="padding: 8px; color: #999; font-size: 0.9em;">À développer</div>
"""
            
            html += """
                        </div>
                        <div style="margin: 15px 0;">
                            <h4 style="color: #ffd43b; font-size: 1em; margin-bottom: 10px;">🔧 À améliorer :</h4>
"""
            
            if points_ameliorer:
                for pa in points_ameliorer:
                    html += f"""
                            <div style="padding: 8px; background: #fff9db; border-radius: 4px; margin: 5px 0; font-size: 0.9em;">
                                {pa}
                            </div>
"""
            else:
                html += """
                            <div style="padding: 8px; color: #999; font-size: 0.9em;">Niveau excellent</div>
"""
            
            html += """
                        </div>
                        <div style="margin: 15px 0;">
                            <h4 style="color: #667eea; font-size: 1em; margin-bottom: 10px;">💡 Recommandations :</h4>
"""
            
            for reco in recommandations:
                html += f"""
                            <div style="padding: 8px; background: #e8eaf6; border-radius: 4px; margin: 5px 0; font-size: 0.9em;">
                                {reco}
                            </div>
"""
            
            html += """
                        </div>
                    </div>
"""
        
        html += """
                </div>
            </div>
            
            <div class="section">
                <h2>📊 Tableau comparatif détaillé</h2>
                <div style="overflow-x: auto; margin: 0 auto;">
                    <table style="width: 100%; border-collapse: collapse; background: white; border-radius: 15px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
                        <thead>
                            <tr style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
                                <th style="padding: 15px; text-align: left; font-size: 14px;">Statistique</th>
"""
        
        for joueur in joueurs:
            html += f"""
                                <th style="padding: 15px; text-align: center; font-size: 14px;">{joueur}</th>
"""
        
        html += """
                            </tr>
                        </thead>
                        <tbody>
"""
        
        # Lignes du tableau comparatif
        comparaison_stats = [
            ('🎾 Total actions', lambda s: s.get('fautes_directes', 0) + s.get('points_gagnants', 0) + s.get('fautes_provoquees_generees', 0) + s.get('fautes_provoquees_subies', 0)),
            ('⚠️ Fautes directes', lambda s: s.get('fautes_directes', 0)),
            ('🏆 Points gagnants', lambda s: s.get('points_gagnants', 0)),
            ('🎯 Fautes provoquées', lambda s: s.get('fautes_provoquees_generees', 0)),
            ('🚫 Fautes subies', lambda s: s.get('fautes_provoquees_subies', 0)),
            ('⚡ Ratio efficacité', lambda s: round((s.get('points_gagnants', 0) + s.get('fautes_provoquees_generees', 0)) / (s.get('fautes_directes', 0) + s.get('fautes_provoquees_subies', 0) + 1), 2)),
            ('💪 % Actions positives', lambda s: round((s.get('points_gagnants', 0) + s.get('fautes_provoquees_generees', 0)) / (s.get('fautes_directes', 0) + s.get('points_gagnants', 0) + s.get('fautes_provoquees_generees', 0) + s.get('fautes_provoquees_subies', 0) + 1) * 100, 1)),
        ]
        
        for i, (stat_label, stat_func) in enumerate(comparaison_stats):
            row_bg = "#f8f9fa" if i % 2 == 0 else "white"
            html += f"""
                            <tr style="background: {row_bg};">
                                <td style="padding: 15px; font-weight: 600; color: #667eea; border-top: 1px solid #e0e0e0;">{stat_label}</td>
"""
            
            # Calculer les valeurs pour tous les joueurs pour trouver le meilleur
            valeurs = []
            for joueur in joueurs:
                player_stats = stats.get(joueur, {})
                valeur = stat_func(player_stats)
                valeurs.append((joueur, valeur))
            
            # Trouver la meilleure valeur (dépend du contexte)
            if 'Fautes' in stat_label and 'provoquées' not in stat_label and 'subies' in stat_label:
                meilleur = min(valeurs, key=lambda x: x[1])[0]  # Moins de fautes = mieux
            else:
                meilleur = max(valeurs, key=lambda x: x[1])[0]  # Plus = mieux
            
            for joueur, valeur in valeurs:
                is_best = joueur == meilleur
                cell_style = "font-weight: bold; background: #d3f9d8;" if is_best else ""
                html += f"""
                                <td style="padding: 15px; text-align: center; border-top: 1px solid #e0e0e0; {cell_style}">{valeur}</td>
"""
            
            html += """
                            </tr>
"""
        
        html += """
                        </tbody>
                    </table>
                </div>
                <div style="text-align: center; margin-top: 12px; color: #666; font-size: 12px;">
                    💚 Les meilleures valeurs de chaque catégorie sont surlignées en vert
                </div>
            </div>
            
            <div class="section">
                <h2>🎯 Matrice des confrontations</h2>
                <p style="text-align: center; color: #666; margin-bottom: 20px;">Tableau unique désignant le vainqueur (net) par confrontation</p>
"""
        
        # Récupérer la matrice des fautes provoquées
        fautes_matrix = {}
        if annotation_manager:
            try:
                fautes_matrix = annotation_manager.get_fautes_provoquees_matrix()
            except AttributeError:
                pass
        
        if fautes_matrix:
            joueur_names = list(fautes_matrix.keys())
            
            # Créer tableau HTML stylisé (net gagnant-perdant)
            html += """
                <div style=\"overflow-x: auto; margin: 0 auto; max-width: 900px;\">
                    <table style=\"width: 100%; border-collapse: collapse; background: white; border-radius: 15px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.1);\">
                        <thead>
                            <tr style=\"background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;\">
                                <th style=\"padding: 15px; text-align: left; font-size: 14px;\">Confrontation</th>
"""
            
            for defenseur in joueur_names:
                html += f"""
                                <th style=\"padding: 15px; text-align: center; font-size: 14px;\">{defenseur}</th>
"""
            
            html += """
                            </tr>
                        </thead>
                        <tbody>
"""
            
            for i, attaquant in enumerate(joueur_names):
                row_bg = "#f8f9fa" if i % 2 == 0 else "white"
                html += f"""
                            <tr style=\"background: {row_bg};\">
                                <td style=\"padding: 15px; font-weight: bold; color: #667eea; border-top: 1px solid #e0e0e0;\">{attaquant}</td>
"""
                
                for defenseur in joueur_names:
                    if attaquant == defenseur:
                        cell_value = "—"
                        cell_color = "#e0e0e0"
                    else:
                        a_to_b = fautes_matrix.get(attaquant, {}).get(defenseur, 0)
                        b_to_a = fautes_matrix.get(defenseur, {}).get(attaquant, 0)
                        net = a_to_b - b_to_a
                        sign = '+' if net > 0 else ('' if net == 0 else '')
                        cell_value = f"{sign}{net}"
                        if net > 0:
                            cell_color = "#d3f9d8"
                        elif net < 0:
                            cell_color = "#ffe3e3"
                        else:
                            cell_color = "#fff9db"
                    
                    html += f"""
                                <td style=\"padding: 15px; text-align: center; font-weight: bold; background: {cell_color}; border-top: 1px solid #e0e0e0;\">{cell_value}</td>
"""
                
                html += """
                            </tr>
"""
            
            html += """
                        </tbody>
                    </table>
                </div>
                <div style=\"text-align: center; margin-top: 12px; color: #666; font-size: 12px;\">
                    Légende: vert = ligne vainqueur, rouge = colonne vainqueur, jaune = neutre (égalité).
                </div>
            </div>
            
            <div class="section">
                <h2>❤️ Coups de Cœur</h2>
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 15px; color: white;">
                    <p style="text-align: center; font-size: 18px; margin-bottom: 15px;">Moments spectaculaires du match</p>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
"""
        
        # Compter les coups de cœur
        coups_coeur = {
            "defense": [],
            "attaque": [],
            "spectaculaire": []
        }
        
        for point in points:
            if point.get("type") == "coup_coeur":
                coeur_type = point.get("coup_coeur_type")
                if coeur_type in coups_coeur:
                    coups_coeur[coeur_type].append(point)
        
        total_coeurs = sum(len(v) for v in coups_coeur.values())
        
        if total_coeurs > 0:
            coeur_icons = {
                "defense": "💪",
                "attaque": "⚡",
                "spectaculaire": "✨"
            }
            coeur_labels = {
                "defense": "Superbes Défenses",
                "attaque": "Superbes Attaques",
                "spectaculaire": "Points Spectaculaires"
            }
            
            for coeur_type, coeur_list in coups_coeur.items():
                if len(coeur_list) > 0:
                    html += f"""
                        <div style="background: rgba(255,255,255,0.15); padding: 15px; border-radius: 10px; text-align: center;">
                            <div style="font-size: 40px; margin-bottom: 10px;">{coeur_icons[coeur_type]}</div>
                            <div style="font-size: 24px; font-weight: bold;">{len(coeur_list)}</div>
                            <div style="font-size: 14px; opacity: 0.9;">{coeur_labels[coeur_type]}</div>
                        </div>
"""
        else:
            html += """
                        <div style="text-align: center; padding: 20px; opacity: 0.7;">
                            <p>Aucun coup de cœur enregistré pour ce match</p>
                        </div>
"""
        
        html += """
                    </div>
                </div>
            </div>
            
            <div class="section">
                <h2 onclick="toggleChronologie()" style="cursor: pointer; user-select: none; display: flex; align-items: center; justify-content: space-between;">
                    <span>📝 Chronologie des points</span>
                    <span id="chrono-arrow" style="transition: transform 0.3s;">▼</span>
                </h2>
                <div id="chronologie-content" style="display: none;">
                <div class="points-list">
"""
        
        # Liste des points
        for point in points:
            point_type = point.get("type", "")
            point_id = point.get("id", 0)
            timestamp = point.get("timestamp", 0)
            capture = point.get("capture", "")
            
            minutes = int(timestamp // 60)
            seconds = int(timestamp % 60)
            time_str = f"{minutes:02d}:{seconds:02d}"
            
            # Badge de type
            badge_class = ""
            type_label = ""
            if point_type == "faute_directe":
                badge_class = "badge-faute"
                type_label = "Faute Directe"
            elif point_type == "point_gagnant":
                badge_class = "badge-gagnant"
                type_label = "Point Gagnant"
            elif point_type == "faute_provoquee":
                badge_class = "badge-provoquee"
                type_label = "Faute Provoquée"
            
            html += f"""
                    <div class="point-item">
                        <div class="point-header">
                            <div class="point-type">Point #{point_id}<span class="badge {badge_class}">{type_label}</span></div>
                            <div class="point-time">⏱️ {time_str}</div>
                        </div>
                        <div class="point-details">
"""
            
            if point_type == "faute_directe":
                joueur = point.get("joueur", "")
                html += f"            <strong>Joueur :</strong> {joueur}\n"
            elif point_type == "point_gagnant":
                joueur = point.get("joueur", "")
                type_coup = point.get("type_coup", "")
                
                # Labels des types de coups
                type_coup_labels = {
                    'service': '🎾 Service',
                    'volee_coup_droit': '🎾 Volée coup droit',
                    'volee_revers': '🎾 Volée revers',
                    'smash': '💥 Smash',
                    'amorti': '🎯 Amorti',
                    'bandeja': '🔥 Bandeja',
                    'vibora': '🐍 Vibora',
                    'fond_de_court': '⚡ Fond de court'
                }
                
                coup_label = type_coup_labels.get(type_coup, type_coup)
                
                html += f"            <strong>Joueur :</strong> {joueur}<br>\n"
                if type_coup:
                    html += f"            <strong>Type de coup :</strong> {coup_label}\n"
            elif point_type == "faute_provoquee":
                attaquant = point.get("attaquant", "")
                defenseur = point.get("defenseur", "")
                html += f"            <strong>Attaquant :</strong> {attaquant} | <strong>Défenseur :</strong> {defenseur}\n"
            
            html += "        </div>\n"
            
            if capture:
                html += f"""
                        <div class="point-capture">
                            <img src="{capture}" alt="Capture Point #{point_id}">
                        </div>
"""
            
            html += "                    </div>\n"
        
        html += f"""
                </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Fonction pour afficher/masquer la chronologie
        function toggleChronologie() {{{{
            const content = document.getElementById('chronologie-content');
            const arrow = document.getElementById('chrono-arrow');
            if (content.style.display === 'none') {{{{
                content.style.display = 'block';
                arrow.style.transform = 'rotate(180deg)';
            }}}} else {{{{
                content.style.display = 'none';
                arrow.style.transform = 'rotate(0deg)';
            }}}}
        }}}}
        
        // Attendre que Chart.js soit chargé et que le DOM soit prêt
        window.addEventListener('load', function() {{{{
        if (typeof Chart === 'undefined') {{{{ return; }}}}
        
        // Graphique: Répartition des coups gagnants
        const coupsCtx = document.getElementById('coupsChart');
        const coupsData = {{}};
"""
        
        # Préparer données des coups gagnants
        type_labels_js = {
            'volee_coup_droit': 'Volée CD',
            'volee_revers': 'Volée Revers',
            'smash': 'Smash',
            'amorti': 'Amorti',
            'fond_de_court': 'Fond de court'
        }
        
        coups_totaux = {k: 0 for k in type_labels_js.keys()}
        
        for joueur in joueurs:
            player_stats = stats.get(joueur, {})
            detail_pg = player_stats.get('points_gagnants_detail', {})
            for coup_type in type_labels_js.keys():
                coups_totaux[coup_type] += detail_pg.get(coup_type, 0)
        
        html += f"""
        const coupsLabels = {[type_labels_js[k] for k in type_labels_js.keys()]};
        const coupsValues = {[coups_totaux[k] for k in type_labels_js.keys()]};
        
        new Chart(coupsCtx, {{
            type: 'polarArea',
            data: {{
                labels: coupsLabels,
                datasets: [{{
                    data: coupsValues,
                    backgroundColor: [
                        'rgba(102, 126, 234, 0.6)',
                        'rgba(118, 75, 162, 0.6)',
                        'rgba(255, 107, 107, 0.6)',
                        'rgba(81, 207, 102, 0.6)',
                        'rgba(255, 212, 59, 0.6)'
                    ]
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ position: 'bottom' }}
                }}
            }}
        }});
        
        // Graphique: Radar de compétences par joueur
        const radarCtx = document.getElementById('radarChart');
"""
        
        # Préparer données radar pour chaque joueur
        radar_data = {}
        for joueur in joueurs:
            player_stats = stats.get(joueur, {})
            fd = player_stats.get('fautes_directes', 0)
            pg = player_stats.get('points_gagnants', 0)
            fp_gen = player_stats.get('fautes_provoquees_generees', 0)
            
            # Normaliser sur 100
            max_val = max(fd, pg, fp_gen, 1)
            radar_data[joueur] = {
                'attaque': (pg / max_val * 100) if max_val > 0 else 0,
                'precision': ((pg + fp_gen) / (pg + fp_gen + fd + 1) * 100) if (pg + fp_gen + fd) > 0 else 0,
                'pression': (fp_gen / max_val * 100) if max_val > 0 else 0,
                'constance': (100 - (fd / max_val * 100)) if max_val > 0 else 0,
                'efficacite': ((pg + fp_gen) / (fd + pg + fp_gen + 1) * 100) if (fd + pg + fp_gen) > 0 else 0
            }
        
        html += f"""
        const radarDatasets = [];
        const radarColors = ['rgba(102, 126, 234, 0.6)', 'rgba(255, 107, 107, 0.6)', 'rgba(81, 207, 102, 0.6)', 'rgba(255, 212, 59, 0.6)'];
        const radarBorderColors = ['rgba(102, 126, 234, 1)', 'rgba(255, 107, 107, 1)', 'rgba(81, 207, 102, 1)', 'rgba(255, 212, 59, 1)'];
"""
        
        for idx, (joueur, data) in enumerate(radar_data.items()):
            html += f"""
        radarDatasets.push({{
            label: '{joueur}',
            data: [{data['attaque']:.1f}, {data['precision']:.1f}, {data['pression']:.1f}, {data['constance']:.1f}, {data['efficacite']:.1f}],
            backgroundColor: radarColors[{idx}],
            borderColor: radarBorderColors[{idx}],
            pointBackgroundColor: radarBorderColors[{idx}],
            pointBorderColor: '#fff',
            pointHoverBackgroundColor: '#fff',
            pointHoverBorderColor: radarBorderColors[{idx}]
        }});
"""
        
        html += """
        new Chart(radarCtx, {
            type: 'radar',
            data: {
                labels: ['Attaque', 'Précision', 'Pression', 'Constance', 'Efficacité'],
                datasets: radarDatasets
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'bottom' }
                },
                scales: {
                    r: {
                        beginAtZero: true,
                        max: 100,
                        ticks: { stepSize: 20 }
                    }
                }
            }
        }});
        
        // Graphique: Efficacité par joueur (barres empilées)
        const efficaciteCtx = document.getElementById('efficaciteChart');
"""
        
        # Préparer données d'efficacité
        eff_labels = []
        eff_positifs = []
        eff_negatifs = []
        
        for joueur in joueurs:
            player_stats = stats.get(joueur, {})
            fd = player_stats.get('fautes_directes', 0)
            pg = player_stats.get('points_gagnants', 0)
            fp_gen = player_stats.get('fautes_provoquees_generees', 0)
            fp_sub = player_stats.get('fautes_provoquees_subies', 0)
            
            eff_labels.append(joueur)
            eff_positifs.append(pg + fp_gen)
            eff_negatifs.append(-(fd + fp_sub))
        
        html += f"""
        new Chart(efficaciteCtx, {{
            type: 'bar',
            data: {{
                labels: {eff_labels},
                datasets: [
                    {{
                        label: 'Actions positives',
                        data: {eff_positifs},
                        backgroundColor: 'rgba(81, 207, 102, 0.8)'
                    }},
                    {{
                        label: 'Actions négatives',
                        data: {eff_negatifs},
                        backgroundColor: 'rgba(255, 107, 107, 0.8)'
                    }}
                ]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ position: 'bottom' }}
                }},
                scales: {{
                    x: {{ stacked: true }},
                    y: {{ stacked: true }}
                }}
            }}
        }});
        
        // Graphique: Momentum du match (différence de score virtuel au fil du temps)
        const momentumCtx = document.getElementById('momentumChart');
        const momentumData = [];
        let momentum = {{}};
"""
        
        # Initialiser momentum pour chaque joueur
        for joueur in joueurs:
            html += f"        momentum['{joueur}'] = 0;\n"
        
        html += """
        
"""
        
        # Calculer le momentum au fil des points
        for i, point in enumerate(points):
            point_type = point.get('type', '')
            timestamp = point.get('timestamp', 0)
            
            if point_type == 'faute_directe':
                joueur = point.get('joueur', '')
                if joueur:
                    html += f"        momentum['{joueur}'] = (momentum['{joueur}'] || 0) - 1;\n"
            elif point_type == 'point_gagnant':
                joueur = point.get('joueur', '')
                if joueur:
                    html += f"        momentum['{joueur}'] = (momentum['{joueur}'] || 0) + 2;\n"
            elif point_type == 'faute_provoquee':
                attaquant = point.get('attaquant', '')
                defenseur = point.get('defenseur', '')
                if attaquant:
                    html += f"        momentum['{attaquant}'] = (momentum['{attaquant}'] || 0) + 1;\n"
                if defenseur:
                    html += f"        momentum['{defenseur}'] = (momentum['{defenseur}'] || 0) - 1;\n"
            
            # Ajouter un point de données tous les N points
            if i % 5 == 0 or i == len(points) - 1:
                html += f"        momentumData.push({{ x: {timestamp:.1f}"
                for joueur in joueurs:
                    html += f", '{joueur}': momentum['{joueur}'] || 0"
                html += " });\n"
        
        html += """
        
        const momentumDatasets = [];
        const momentumColors2 = ['#667eea', '#ff6b6b', '#51cf66', '#ffd43b'];
"""
        
        for idx, joueur in enumerate(joueurs):
            html += f"""
        momentumDatasets.push({{
            label: '{joueur}',
            data: momentumData.map(d => ({{ x: d.x, y: d['{joueur}'] || 0 }})),
            borderColor: momentumColors2[{idx}],
            backgroundColor: momentumColors2[{idx}] + '33',
            tension: 0.4,
            fill: true
        }});
"""
        
        html += """
        
        new Chart(momentumCtx, {
            type: 'line',
            data: {
                datasets: momentumDatasets
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'bottom' },
                    title: {
                        display: true,
                        text: 'Évolution du momentum (score virtuel cumulé: +2 pts gagnants, +1 FP générées, -1 fautes)'
                    }
                },
                scales: {
                    x: {
                        type: 'linear',
                        title: { display: true, text: 'Temps (secondes)' }
                    },
                    y: {
                        title: { display: true, text: 'Momentum' }
                    }
                }
            }
        }});
        
        // Graphique: Impact des joueurs
        const impactCtx = document.getElementById('impactChart');
        const impactData = {{"""
        
        # Préparer les données d'impact par joueur
        player_labels = []
        player_impact = []
        
        for joueur in joueurs:
            player_stats = stats.get(joueur, {})
            player_labels.append(joueur)
            fd = player_stats.get('fautes_directes', 0)
            pg = player_stats.get('points_gagnants', 0)
            fp_gen = player_stats.get('fautes_provoquees_generees', 0)
            fp_sub = player_stats.get('fautes_provoquees_subies', 0)
            # Impact = points gagnants + fautes provoquées - fautes directes - fautes subies
            impact = pg + fp_gen - fd - fp_sub
            player_impact.append(impact)
        
        html += f"""
            labels: {json.dumps(player_labels)},
            impact: {json.dumps(player_impact)}
        }};
        
        // Trier par impact décroissant
        const impactPairs = impactData.labels.map((l, i) => ({{ label: l, value: impactData.impact[i] }}));
        impactPairs.sort((a, b) => b.value - a.value);
        const sortedLabels = impactPairs.map(p => p.label);
        const sortedImpact = impactPairs.map(p => p.value);

        new Chart(impactCtx, {{
            type: 'bar',
            data: {{
                labels: sortedLabels,
                datasets: [
                    {{
                        label: 'Impact sur le match',
                        data: sortedImpact,
                        backgroundColor: sortedImpact.map(v => v > 3 ? '#4ecca3' : v > 0 ? '#51cf66' : v > -5 ? '#ff6b6b' : '#c92a2a'),
                        borderColor: 'white',
                        borderWidth: 2
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: true,
                plugins: {{
                    legend: {{ display: false }},
                    tooltip: {{
                        callbacks: {{
                            label: (context) => {{
                                const value = context.parsed.y;
                                return `Impact: ${{value > 0 ? '+' : ''}}${{value}} points`;
                            }}
                        }}
                    }},
                    title: {{
                        display: false
                    }}
                }},
                scales: {{
                    y: {{ 
                        beginAtZero: true,
                        grid: {{
                            color: 'rgba(255, 255, 255, 0.1)'
                        }},
                        ticks: {{
                            color: '#666',
                            font: {{
                                size: 12,
                                weight: 'bold'
                            }}
                        }}
                    }},
                    x: {{ 
                        ticks: {{ 
                            autoSkip: false,
                            color: '#333',
                            font: {{
                                size: 14,
                                weight: 'bold'
                            }}
                        }},
                        grid: {{
                            display: false
                        }}
                    }}
                }}
            }}
        }});
        

        const progressionCtx = document.getElementById('progressionChart');
"""
        
        # Générer données de progression pour chaque joueur
        if annotation_manager:
            joueur_names = joueurs
            colors = ['#667eea', '#ff6b6b', '#51cf66', '#ffd43b']
            
            html += """
        const progressionData = {
            labels: ['10%', '20%', '30%', '40%', '50%', '60%', '70%', '80%', '90%', '100%'],
            datasets: [
"""
            
            for idx, joueur in enumerate(joueur_names):
                try:
                    progression = annotation_manager.get_player_progression(joueur)
                    efficacites = [p.get('efficacite', 0) for p in progression]
                    
                    html += f"""
                {{
                    label: '{joueur}',
                    data: {efficacites},
                    borderColor: '{colors[idx % len(colors)]}',
                    backgroundColor: '{colors[idx % len(colors)]}33',
                    tension: 0.4,
                    fill: false
                }},
"""
                except:
                    pass
            
            html += """
            ]
        };
        
        new Chart(progressionCtx, {
            type: 'line',
            data: progressionData,
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'bottom' },
                    title: {
                        display: true,
                        text: 'Évolution de l\'efficacité par joueur (% de points gagnants vs actions totales)'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        title: { display: true, text: 'Efficacité (%)' }
                    },
                    x: {
                        title: { display: true, text: 'Progression du match' }
                    }
                }
            }
        });
"""
        
        html += """
        }); // fin window.load
    </script>
</body>
</html>
"""
        
        return html
