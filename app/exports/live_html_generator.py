"""
Générateur de rapport HTML live pour l'analyse en temps réel
S'auto-rafraîchit pendant l'annotation du match
"""

from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
import json
import sys

# Import des fonctions Ollama qui marchent
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
try:
    from ollama_chat import (
        analyze_match_stats,
        format_match_context,
        chat_with_ollama,
        check_ollama_status
    )
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    print("[LiveHTML] Ollama non disponible")


class LiveHTMLGenerator:
    """Génère un rapport HTML interactif qui se rafraîchit automatiquement"""
    
    def __init__(self, output_path: Path = None):
        self.output_path = output_path or Path("data/live_analysis.html")
        self.ollama_url = "http://localhost:11434/api/generate"
        self.model_name = "llama3.2:3b"
        
        # Fichier historique pour l'IA (même répertoire que le HTML)
        self.history_file = self.output_path.parent / "ai_history.json"
        
    def generate_html(self, match_data: Dict, force_analyze: bool = False):
        """
        Génère le rapport HTML à partir des données en mémoire
        
        Args:
            match_data: Dictionnaire des données du match (annotation_manager.export_to_dict())
            force_analyze: Force une nouvelle analyse IA (sinon uniquement tous les 3 points)
        """
        if not match_data:
            print(f"[LiveHTML] Aucune donnée de match")
            return False
            
        try:
            # Analyser les stats
            if OLLAMA_AVAILABLE:
                stats = analyze_match_stats(match_data)
            else:
                stats = self._compute_basic_stats(match_data)
            
            points_count = len(match_data.get("points", []))
            
            # Analyse IA en thread de faible priorité : à chaque point ou manuellement
            ai_analysis = ""
            if OLLAMA_AVAILABLE and check_ollama_status() and (force_analyze or (points_count > 0 and points_count % 3 == 0)):
                ai_analysis = self._get_ai_analysis(match_data, stats)
            
            # Générer le HTML
            html = self._build_html(match_data, stats, ai_analysis, points_count)
            
            # Écrire le fichier
            with open(self.output_path, 'w', encoding='utf-8') as f:
                f.write(html)
            
            print(f"[LiveHTML] Rapport généré: {self.output_path}")
            return True
            
        except Exception as e:
            print(f"[LiveHTML] Erreur: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _get_ai_analysis(self, match_data: Dict, stats: Dict) -> str:
        """Obtient l'analyse IA via ollama_chat.py avec HISTORIQUE conversationnel"""
        try:
            # Lire l'historique existant
            history = self._load_history()
            
            # Construire le prompt avec contexte actuel
            context = format_match_context(match_data, stats)
            points_count = len(match_data.get("points", []))
            
            # Prompt avec référence à l'historique
            if history:
                last_analysis = history[-1].get("analysis", "")
                last_points = history[-1].get("points_count", 0)
                
                prompt = f"""HISTORIQUE: Lors de ton analyse précédente ({last_points} points), tu as dit:
\"{last_analysis}\"

{context}

Maintenant ({points_count} points), donne une analyse ÉVOLUTIVE COURTE (2-3 phrases MAX).
Compare avec ton analyse précédente si pertinent. Focus sur ce qui a CHANGÉ.
Utilise des émojis pour rendre ça vivant."""
            else:
                # Première analyse
                prompt = f"""{context}

Donne une analyse COURTE et PERCUTANTE du match en cours (2-3 phrases MAX).
Focus sur les tendances actuelles et les profils de joueurs.
Utilise des émojis pour rendre ça vivant."""
            
            # Appeler Ollama (mode non-stream pour récupérer le texte)
            analysis = chat_with_ollama(prompt, stream=False, timeout=15)
            
            if analysis:
                # Sauvegarder dans l'historique
                self._save_to_history(analysis, points_count, stats)
                return analysis
            else:
                return "⌛ Analyse en cours..."
            
        except Exception as e:
            print(f"[LiveHTML] Erreur analyse IA: {e}")
            return f"❌ Erreur: {str(e)}"
    
    def _load_history(self) -> list:
        """Charge l'historique des analyses IA depuis le fichier JSON"""
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"[LiveHTML] Erreur lecture historique: {e}")
        return []
    
    def _save_to_history(self, analysis: str, points_count: int, stats: Dict):
        """Sauvegarde l'analyse actuelle dans l'historique"""
        try:
            history = self._load_history()
            
            # Ajouter la nouvelle entrée
            entry = {
                "timestamp": datetime.now().isoformat(),
                "points_count": points_count,
                "analysis": analysis,
                "total_points": stats.get("total_points", 0)
            }
            
            history.append(entry)
            
            # Limiter à 10 dernières analyses pour ne pas surcharger
            if len(history) > 10:
                history = history[-10:]
            
            # Sauvegarder
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"[LiveHTML] Erreur sauvegarde historique: {e}")
    
    def _compute_basic_stats(self, match_data: Dict) -> Dict:
        """Utilise les stats déjà calculées par l'AnnotationManager"""
        # Utiliser les stats DEJA CALCULEES dans match_data["stats"]
        # qui contiennent fautes_provoquees_generees et fautes_provoquees_subies
        match_stats = match_data.get("stats", {})
        points = match_data.get("points", [])
        
        stats = {
            "total_points": len(points),
            "joueurs": {},
            "fautes": {"directes": 0, "provoquees": 0},
            "types_coups": {}
        }
        
        # Convertir les stats de l'AnnotationManager vers le format LiveHTML
        for joueur_nom, joueur_stats in match_stats.items():
            pg = joueur_stats.get("points_gagnants", 0)
            fd = joueur_stats.get("fautes_directes", 0)
            # IMPORTANT: Utiliser les stats calculées par l'AnnotationManager
            fp_generees = joueur_stats.get("fautes_provoquees_generees", 0)
            fp_subies = joueur_stats.get("fautes_provoquees_subies", 0)
            
            stats["joueurs"][joueur_nom] = {
                "points_gagnes": pg,
                "fautes_directes": fd,
                "fautes_provoquees": fp_generees,  # Fautes que ce joueur a PROVOQUEES
                "fautes_subies": fp_subies,  # Fautes que ce joueur a SUBIES
                "impact": (pg + fp_generees) - (fd + fp_subies)
            }
            
            stats["fautes"]["directes"] += fd
            stats["fautes"]["provoquees"] += fp_generees
        
        return stats
    
    def _build_html(self, match_data: Dict, stats: Dict, ai_analysis: str, points_count: int) -> str:
        """Construit le HTML complet"""
        match_info = match_data.get("match", {})
        joueurs = match_info.get("joueurs", [])
        joueurs_str = ", ".join([p if isinstance(p, str) else p.get("nom", "") for p in joueurs])
        
        now = datetime.now().strftime("%H:%M:%S")
        
        # Charger l'historique des analyses
        history = self._load_history()
        
        # Générer le HTML des erreurs vocales si présentes
        voice_errors_html = ""
        voice_errors = match_data.get("voice_errors", [])
        if voice_errors:
            voice_errors_html = """
        <div class="ai-analysis" style="background: #fee; border: 2px solid #EF4444; margin-bottom: 20px;">
            <h2 style="color: #EF4444;">⚠️ ERREURS DE COMMANDES VOCALES</h2>
            <p style="margin-bottom: 15px;"><strong>Points incomplets détectés - Validation stricte active</strong></p>
"""
            for err in voice_errors:
                timestamp = err.get("timestamp", "")
                command = err.get("command", "")
                error_msg = err.get("error", "")
                
                voice_errors_html += f"""
            <div style="background: white; padding: 12px; border-radius: 8px; margin-bottom: 10px; border-left: 4px solid #EF4444;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                    <strong style="color: #EF4444;">🕐 {timestamp}</strong>
                </div>
                <p style="margin: 5px 0; color: #666;"><strong>Commande:</strong> "{command}"</p>
                <p style="margin: 5px 0; color: #EF4444; font-weight: bold;">{error_msg}</p>
            </div>
"""
            
            voice_errors_html += """
            <p style="margin-top: 15px; padding: 10px; background: #fff3cd; border-radius: 5px; color: #856404;">
                💡 <strong>Pour corriger:</strong> Dites "OK supprimer" puis répétez la commande complète
            </p>
        </div>
"""
        
        # Construction des stats par joueur
        joueurs_html = ""
        for joueur, player_stats in stats.get("joueurs", {}).items():
            pg = player_stats.get("points_gagnes", 0)
            fd = player_stats.get("fautes_directes", 0)
            fp = player_stats.get("fautes_provoquees", 0)
            fs = player_stats.get("fautes_subies", 0)
            efficacite = round((pg / max(pg + fd, 1)) * 100, 1)
            
            # Ratio fautes provoquées/subies pour le graphique
            total_fautes = fp + fs
            fp_percent = round((fp / max(total_fautes, 1)) * 100, 1)
            fs_percent = round((fs / max(total_fautes, 1)) * 100, 1)
            
            # Impact net = points gagnants + fautes provoquées - fautes directes - fautes subies
            impact = (pg + fp) - (fd + fs)
            impact_color = "#28a745" if impact > 0 else ("#dc3545" if impact < 0 else "#ffc107")
            impact_text = f"+{impact}" if impact > 0 else str(impact)
            
            joueurs_html += f"""
            <div class="player-card">
                <h3>👤 {joueur}</h3>
                <div class="stat-row">
                    <span class="stat-label">Points gagnants</span>
                    <span class="stat-value success">{pg}</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Fautes directes</span>
                    <span class="stat-value error">{fd}</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Efficacité</span>
                    <span class="stat-value">{efficacite}%</span>
                </div>
                
                <div class="divider"></div>
                
                <div class="stat-row">
                    <span class="stat-label">⚔️ Fautes provoquées</span>
                    <span class="stat-value success">{fp}</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">🛡️ Fautes subies</span>
                    <span class="stat-value error">{fs}</span>
                </div>
                <div class="stat-row highlight">
                    <span class="stat-label">💥 Impact Match</span>
                    <span class="stat-value" style="color: {impact_color}; font-size: 1.4em;">{impact_text}</span>
                </div>
                
                <div class="impact-chart">
                    <div class="chart-label">Influence sur le jeu:</div>
                    <div class="chart-bar">
                        <div class="bar-segment provoquees" style="width: {fp_percent}%">
                            {fp}
                        </div>
                        <div class="bar-segment subies" style="width: {fs_percent}%">
                            {fs}
                        </div>
                    </div>
                    <div class="chart-legend">
                        <span class="legend-item"><span class="color-box provoquees"></span> Provoquées</span>
                        <span class="legend-item"><span class="color-box subies"></span> Subies</span>
                    </div>
                </div>
            </div>
            """
        
        html_content = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="5">
    <title>📊 Analyse Live - Padel</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        .header {{
            background: white;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        .header .subtitle {{
            color: #666;
            font-size: 1.1em;
        }}
        
        .match-info {{
            background: #f8f9fa;
            border-radius: 10px;
            padding: 15px;
            margin-top: 15px;
        }}
        
        .match-info p {{
            margin: 5px 0;
            font-size: 0.95em;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}
        
        .player-card {{
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }}
        
        .player-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 25px rgba(0,0,0,0.15);
        }}
        
        .player-card h3 {{
            font-size: 1.5em;
            margin-bottom: 15px;
            color: #667eea;
        }}
        
        .stat-row {{
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #eee;
        }}
        
        .stat-row:last-child {{
            border-bottom: none;
        }}
        
        .stat-label {{
            font-weight: 500;
            color: #666;
        }}
        
        .stat-value {{
            font-weight: bold;
            font-size: 1.2em;
            color: #667eea;
        }}
        
        .stat-value.success {{
            color: #28a745;
        }}
        
        .stat-value.error {{
            color: #dc3545;
        }}
        
        .divider {{
            height: 2px;
            background: linear-gradient(90deg, transparent, #667eea, transparent);
            margin: 15px 0;
        }}
        
        .highlight {{
            background: #f8f9fa;
            padding: 12px 10px !important;
            border-radius: 8px;
            margin-top: 10px;
        }}
        
        .impact-chart {{
            margin-top: 20px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 10px;
        }}
        
        .chart-label {{
            font-weight: bold;
            color: #667eea;
            margin-bottom: 10px;
            font-size: 0.95em;
        }}
        
        .chart-bar {{
            display: flex;
            height: 35px;
            background: #e9ecef;
            border-radius: 20px;
            overflow: hidden;
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .bar-segment {{
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 0.9em;
            transition: all 0.3s ease;
        }}
        
        .bar-segment.provoquees {{
            background: linear-gradient(135deg, #28a745, #20c997);
        }}
        
        .bar-segment.subies {{
            background: linear-gradient(135deg, #dc3545, #fd7e14);
        }}
        
        .chart-legend {{
            display: flex;
            gap: 20px;
            margin-top: 10px;
            justify-content: center;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.85em;
            color: #666;
        }}
        
        .color-box {{
            width: 15px;
            height: 15px;
            border-radius: 3px;
        }}
        
        .color-box.provoquees {{
            background: linear-gradient(135deg, #28a745, #20c997);
        }}
        
        .color-box.subies {{
            background: linear-gradient(135deg, #dc3545, #fd7e14);
        }}
        
        .ai-analysis {{
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        
        .ai-analysis h2 {{
            font-size: 1.8em;
            margin-bottom: 15px;
            color: #667eea;
        }}
        
        .ai-analysis p {{
            line-height: 1.8;
            font-size: 1.1em;
            color: #444;
            white-space: pre-wrap;
        }}
        
        .refresh-info {{
            text-align: center;
            color: white;
            margin-top: 20px;
            font-size: 0.9em;
            opacity: 0.8;
        }}
        
        .pulse {{
            display: inline-block;
            width: 10px;
            height: 10px;
            background: #28a745;
            border-radius: 50%;
            margin-right: 8px;
            animation: pulse 2s infinite;
        }}
        
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.3; }}
        }}
        
        .badge {{
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: bold;
            margin-left: 10px;
        }}
        
        /* Media queries pour mobile */
        @media (max-width: 768px) {{
            body {{
                padding: 10px;
            }}
            
            .container {{
                margin: 0;
            }}
            
            .header {{
                padding: 20px 15px;
                border-radius: 10px;
            }}
            
            .header h1 {{
                font-size: 1.8em;
            }}
            
            .header .subtitle {{
                font-size: 0.95em;
            }}
            
            .match-info {{
                padding: 12px;
            }}
            
            .match-info p {{
                font-size: 0.85em;
            }}
            
            .stats-grid {{
                grid-template-columns: 1fr;
                gap: 15px;
            }}
            
            .player-card {{
                padding: 20px 15px;
            }}
            
            .player-card h3 {{
                font-size: 1.3em;
            }}
            
            .stat-row {{
                padding: 8px 0;
            }}
            
            .stat-label {{
                font-size: 0.9em;
            }}
            
            .stat-value {{
                font-size: 1.1em;
            }}
            
            .ai-analysis {{
                padding: 20px 15px;
                border-radius: 10px;
            }}
            
            .ai-analysis h2 {{
                font-size: 1.4em;
            }}
            
            .ai-analysis p {{
                font-size: 1em;
                line-height: 1.6;
            }}
            
            .badge {{
                display: block;
                margin: 10px 0 0 0;
                width: fit-content;
            }}
            
            .chart-bar {{
                height: 30px;
            }}
            
            .bar-segment {{
                font-size: 0.8em;
            }}
        }}
        
        @media (max-width: 480px) {{
            .header h1 {{
                font-size: 1.5em;
            }}
            
            .player-card h3 {{
                font-size: 1.2em;
            }}
            
            .ai-analysis h2 {{
                font-size: 1.2em;
            }}
            
            .ai-analysis p {{
                font-size: 0.95em;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Analyse Live PADEL</h1>
            <p class="subtitle">🤖 Powered by Ollama AI <span class="badge">{points_count} points</span></p>
            
            <div class="match-info">
                <p><strong>⚡ Joueurs:</strong> {joueurs_str}</p>
                <p><strong>📅 Date:</strong> {match_info.get('date', 'Inconnue')}</p>
                <p><strong>🕐 Dernière mise à jour:</strong> {now}</p>
            </div>
        </div>
        
        <div class="stats-grid">
            {joueurs_html}
        </div>
        
        {voice_errors_html}
        
        <div class="ai-analysis">
            <h2>💡 Analyse IA Évolutive</h2>
            <p>{ai_analysis if ai_analysis else '⏳ Analyse automatique tous les 3 points avec HISTORIQUE CONVERSATIONNEL (l\'IA compare avec ses analyses précédentes)... Thread de faible priorité.'}</p>
        </div>
"""
        
        # Ajouter l'historique des analyses si disponible
        if history and len(history) > 1:
            html_content += """
        <div class="ai-analysis" style="margin-top: 20px;">
            <h2>📜 Historique des Analyses</h2>
            <div style="max-height: 400px; overflow-y: auto;">
"""
            # Afficher les 5 dernières analyses (en ordre inverse, plus récent en haut)
            for entry in reversed(history[-6:-1]):  # Les 5 avant la dernière (qui est déjà affichée)
                timestamp = entry.get("timestamp", "")
                pts = entry.get("points_count", 0)
                analysis_text = entry.get("analysis", "")
                
                # Formater le timestamp
                try:
                    dt = datetime.fromisoformat(timestamp)
                    time_str = dt.strftime("%H:%M:%S")
                except:
                    time_str = timestamp
                
                html_content += f"""
                <div style="background: #f8f9fa; padding: 15px; border-radius: 10px; margin-bottom: 10px; border-left: 4px solid #667eea;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                        <strong style="color: #667eea;">⏱️ {time_str}</strong>
                        <span style="background: #667eea; color: white; padding: 2px 10px; border-radius: 12px; font-size: 0.85em;">{pts} points</span>
                    </div>
                    <p style="margin: 0; color: #444; line-height: 1.6;">{analysis_text}</p>
                </div>
"""
            
            html_content += """
            </div>
        </div>
"""
        
        # Section de débogage pour vérifier les données brutes
        debug_html = "<div class='ai-analysis' style='margin-top: 30px; background: #2d3748; color: #e2e8f0;'>"
        debug_html += "<h2 style='color: #fbbf24;'>🔍 DEBUG - Données Brutes</h2>"
        
        for joueur_nom, joueur_stats in stats.get("joueurs", {}).items():
            fp = joueur_stats.get("fautes_provoquees", 0)
            fs = joueur_stats.get("fautes_subies", 0)
            pg = joueur_stats.get("points_gagnes", 0)
            fd = joueur_stats.get("fautes_directes", 0)
            
            debug_html += f"""
            <div style='background: #1a202c; padding: 15px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #fbbf24;'>
                <h3 style='color: #90cdf4; margin-bottom: 10px;'>{joueur_nom}</h3>
                <div style='font-family: monospace; font-size: 0.9em;'>
                    <p>• fautes_provoquees: <strong style='color: #48bb78;'>{fp}</strong></p>
                    <p>• fautes_subies: <strong style='color: #f56565;'>{fs}</strong></p>
                    <p>• points_gagnes: <strong style='color: #90cdf4;'>{pg}</strong></p>
                    <p>• fautes_directes: <strong style='color: #ed8936;'>{fd}</strong></p>
                </div>
            </div>
            """
        
        debug_html += "</div>"
        html_content += debug_html
        
        html_content += """
        <div class="refresh-info">
            <span class="pulse"></span>
            Auto-actualisation toutes les 5 secondes
        </div>
    </div>
</body>
</html>"""

        return html_content


def generate_live_report(match_data: Dict, force_analyze: bool = False) -> bool:
    """
    Fonction helper pour générer rapidement un rapport
    
    Args:
        match_data: Dictionnaire des données du match (annotation_manager.export_to_dict())
        force_analyze: Force l'analyse IA
        
    Returns:
        True si succès
    """
    generator = LiveHTMLGenerator()
    return generator.generate_html(match_data, force_analyze)
