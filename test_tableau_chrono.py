"""
Génération d'un tableau comparatif par tranches chronologiques de 20%
Test pour Arnaud uniquement
"""

import re
from pathlib import Path

# Données extraites du rapport pour tous les joueurs
data_joueurs = {
    "Arnaud": {
        "0-20%": {"fautes_directes": 2, "points_gagnants": 4, "fautes_provoquees": 4, "fautes_subies": 7},
        "20-40%": {"fautes_directes": 3, "points_gagnants": 3, "fautes_provoquees": 14, "fautes_subies": 9},
        "40-60%": {"fautes_directes": 4, "points_gagnants": 0, "fautes_provoquees": 7, "fautes_subies": 7},
        "60-80%": {"fautes_directes": 2, "points_gagnants": 0, "fautes_provoquees": 7, "fautes_subies": 3},
        "80-100%": {"fautes_directes": 2, "points_gagnants": 3, "fautes_provoquees": 5, "fautes_subies": 5}
    },
    "Fabrice": {
        "0-20%": {"fautes_directes": 10, "points_gagnants": 6, "fautes_provoquees": 3, "fautes_subies": 2},
        "20-40%": {"fautes_directes": 9, "points_gagnants": 1, "fautes_provoquees": 6, "fautes_subies": 4},
        "40-60%": {"fautes_directes": 4, "points_gagnants": 3, "fautes_provoquees": 4, "fautes_subies": 4},
        "60-80%": {"fautes_directes": 4, "points_gagnants": 2, "fautes_provoquees": 5, "fautes_subies": 1},
        "80-100%": {"fautes_directes": 5, "points_gagnants": 2, "fautes_provoquees": 6, "fautes_subies": 5}
    },
    "Laurent": {
        "0-20%": {"fautes_directes": 3, "points_gagnants": 2, "fautes_provoquees": 4, "fautes_subies": 8},
        "20-40%": {"fautes_directes": 5, "points_gagnants": 5, "fautes_provoquees": 3, "fautes_subies": 7},
        "40-60%": {"fautes_directes": 3, "points_gagnants": 1, "fautes_provoquees": 0, "fautes_subies": 5},
        "60-80%": {"fautes_directes": 1, "points_gagnants": 3, "fautes_provoquees": 5, "fautes_subies": 3},
        "80-100%": {"fautes_directes": 1, "points_gagnants": 3, "fautes_provoquees": 3, "fautes_subies": 6}
    },
    "Alex": {
        "0-20%": {"fautes_directes": 3, "points_gagnants": 5, "fautes_provoquees": 6, "fautes_subies": 0},
        "20-40%": {"fautes_directes": 1, "points_gagnants": 2, "fautes_provoquees": 6, "fautes_subies": 3},
        "40-60%": {"fautes_directes": 1, "points_gagnants": 4, "fautes_provoquees": 7, "fautes_subies": 2},
        "60-80%": {"fautes_directes": 1, "points_gagnants": 2, "fautes_provoquees": 3, "fautes_subies": 6},
        "80-100%": {"fautes_directes": 1, "points_gagnants": 1, "fautes_provoquees": 3, "fautes_subies": 14}
    }
}

def calculer_stats_avancees(data):
    """Calcule les stats avancées pour chaque tranche"""
    stats = {}
    
    for tranche, vals in data.items():
        fd = vals["fautes_directes"]
        pg = vals["points_gagnants"]
        fp = vals["fautes_provoquees"]
        fs = vals["fautes_subies"]
        
        # Total actions = TOUTES les actions (y compris fautes subies)
        total_actions = fd + pg + fp + fs
        
        # Ratio efficacité = (points gagnants + fautes provoquées) / (fautes directes + fautes subies)
        # Éviter division par zéro
        denominateur = fd + fs
        if denominateur > 0:
            ratio_efficacite = round((pg + fp) / denominateur, 2)
        else:
            ratio_efficacite = 0
        
        # % Actions positives = (points gagnants + fautes provoquées) / total actions * 100
        if total_actions > 0:
            pct_positives = round((pg + fp) / total_actions * 100, 1)
        else:
            pct_positives = 0
        
        stats[tranche] = {
            "total_actions": total_actions,
            "fautes_directes": fd,
            "points_gagnants": pg,
            "fautes_provoquees": fp,
            "fautes_subies": fs,
            "ratio_efficacite": ratio_efficacite,
            "pct_positives": pct_positives
        }
    
    return stats

# Calculer les stats pour tous les joueurs
stats_joueurs = {joueur: calculer_stats_avancees(data) for joueur, data in data_joueurs.items()}

# Générer le HTML
html = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Tableau Comparatif Chronologique - Tous les joueurs</title>
    <style>
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            background: #f8f9fa;
            padding: 40px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            padding: 40px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        h1 {
            color: #1e293b;
            margin-bottom: 10px;
            text-align: center;
        }
        .subtitle {
            color: #666;
            margin-bottom: 40px;
            text-align: center;
        }
        h2 {
            color: #667eea;
            margin-top: 50px;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e2e8f0;
            font-size: 1.5em;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            margin-bottom: 15px;
        }
        thead tr {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        th {
            padding: 15px;
            text-align: center;
            font-size: 14px;
            font-weight: 600;
        }
        th:first-child {
            text-align: left;
        }
        td {
            padding: 15px;
            text-align: center;
            border-top: 1px solid #e0e0e0;
        }
        td:first-child {
            font-weight: 600;
            color: #667eea;
            text-align: left;
        }
        tbody tr:nth-child(even) {
            background: #f8f9fa;
        }
        tbody tr:nth-child(odd) {
            background: white;
        }
        .best {
            font-weight: bold;
            background: #d3f9d8 !important;
        }
        .note {
            text-align: center;
            margin-top: 12px;
            margin-bottom: 40px;
            color: #666;
            font-size: 13px;
            font-style: italic;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Analyse Chronologique - Tous les joueurs</h1>
        <p class="subtitle">Évolution des statistiques par tranches de 20% du match</p>
"""

# Générer un tableau pour chaque joueur
couleurs_joueurs = {
    "Arnaud": "#667eea",
    "Fabrice": "#ff6b6b",
    "Laurent": "#51cf66",
    "Alex": "#ffd43b"
}

for joueur, stats in stats_joueurs.items():
    couleur = couleurs_joueurs.get(joueur, "#667eea")
    
    html += f"""
        <h2 style="color: {couleur};">📊 {joueur}</h2>
        <div style="overflow-x: auto; margin: 0 auto;">
            <table>
                <thead>
                    <tr style="background: linear-gradient(135deg, {couleur} 0%, #764ba2 100%); color: white;">
                        <th style="padding: 15px; text-align: left; font-size: 14px;">Statistique</th>
                        <th style="padding: 15px; text-align: center; font-size: 14px;">0-20%</th>
                        <th style="padding: 15px; text-align: center; font-size: 14px;">20-40%</th>
                        <th style="padding: 15px; text-align: center; font-size: 14px;">40-60%</th>
                        <th style="padding: 15px; text-align: center; font-size: 14px;">60-80%</th>
                        <th style="padding: 15px; text-align: center; font-size: 14px;">80-100%</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    # Données du tableau
    lignes = [
        ("🎾 Total actions", "total_actions"),
        ("⚠️ Fautes directes", "fautes_directes"),
        ("🏆 Points gagnants", "points_gagnants"),
        ("🎯 Fautes provoquées", "fautes_provoquees"),
        ("🚫 Fautes subies", "fautes_subies"),
        ("⚡ Ratio efficacité", "ratio_efficacite"),
        ("💪 % Actions positives", "pct_positives")
    ]
    
    for i, (label, key) in enumerate(lignes):
        bg = "#f8f9fa" if i % 2 == 0 else "white"
        html += f"""
                    <tr style="background: {bg};">
                        <td style="padding: 15px; font-weight: 600; color: {couleur}; border-top: 1px solid #e0e0e0;">{label}</td>
"""
        
        # Trouver la meilleure valeur pour mettre en vert
        tranches = ["0-20%", "20-40%", "40-60%", "60-80%", "80-100%"]
        valeurs = [stats[t][key] for t in tranches]
        
        # Pour les fautes directes et subies, le meilleur est le plus bas (mais pas 0)
        if key in ["fautes_directes", "fautes_subies"]:
            valeurs_non_nulles = [v for v in valeurs if v > 0]
            best_val = min(valeurs_non_nulles) if valeurs_non_nulles else None
        else:
            best_val = max(valeurs)
        
        # Ajouter les cellules
        for tranche in tranches:
            val = stats[tranche][key]
            is_best = (val == best_val and best_val is not None and val != 0)
            classe = " class=\"best\"" if is_best else ""
            html += f'                        <td{classe} style="padding: 15px; text-align: center; border-top: 1px solid #e0e0e0;">{val}</td>\n'
        
        html += "                    </tr>\n"
    
    html += """
                </tbody>
            </table>
        </div>
        <div class="note">
            💚 Les meilleures valeurs de chaque catégorie sont surlignées en vert
        </div>
"""

html += """
    </div>
</body>
</html>
"""

# Sauvegarder
output_path = "data/test_tableau_chrono_tous.html"
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"✅ Tableau généré: {output_path}")
print("\n📊 Aperçu des stats calculées pour tous les joueurs:")
print("="*60)
for joueur, stats in stats_joueurs.items():
    total = sum(s['total_actions'] for s in stats.values())
    print(f"\n{joueur}: {total} actions au total")
    for tranche, s in stats.items():
        print(f"  {tranche}: {s['total_actions']} actions, ratio {s['ratio_efficacite']}, {s['pct_positives']}% positives")
