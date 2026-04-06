"""
Script simple pour générer un rapport HTML à partir d'un autosave
"""
import json
from datetime import datetime

# Charger les données
json_path = r"E:\projet\padel stat\data\autosave_VID_20251217_120454_20251220_002108.json"
output_path = r"E:\projet\padel stat\data\rapport_simple.html"

print(f"📂 Chargement: {json_path}")
with open(json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

points = data.get('points', [])
match_info = data.get('match', {})
joueurs_raw = match_info.get('joueurs', [])
joueurs = [j if isinstance(j, str) else j.get('nom', 'Joueur') for j in joueurs_raw]

print(f"✅ {len(points)} points - Joueurs: {', '.join(joueurs)}")

# Calculer stats basiques
stats = {j: {'PG': 0, 'FD': 0, 'FP': 0, 'FS': 0} for j in joueurs}

for pt in points:
    joueur = pt.get('joueur')
    type_coup = pt.get('type')
    if joueur in stats and type_coup in stats[joueur]:
        stats[joueur][type_coup] += 1

# Générer HTML
html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Rapport Padel - {datetime.now().strftime('%d/%m/%Y')}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Inter', sans-serif;
            background: #f5f7fa;
            padding: 20px;
            position: relative;
        }}
        body::before {{
            content: '';
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background-image: url('../assets/logo_nanoapp.png');
            background-repeat: no-repeat;
            background-position: center;
            background-size: 40%;
            opacity: 0.3;
            z-index: -1;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
            color: white;
            padding: 40px;
            border-bottom: 3px solid #0ea5e9;
        }}
        .header h1 {{ font-size: 2em; margin-bottom: 10px; }}
        .content {{ padding: 40px; }}
        .section {{ margin-bottom: 40px; }}
        .section h2 {{
            color: #1e293b;
            font-size: 1.5em;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e2e8f0;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
        }}
        .card {{
            background: #f8fafc;
            padding: 24px;
            border-radius: 8px;
            border: 1px solid #e2e8f0;
        }}
        .card h3 {{
            color: #2c5282;
            margin-bottom: 16px;
            font-size: 1.2em;
        }}
        .stat-line {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #e2e8f0;
        }}
        .stat-line:last-child {{ border-bottom: none; }}
        .stat-label {{ color: #64748b; }}
        .stat-value {{
            font-weight: 600;
            color: #1e293b;
        }}
        .summary-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 30px;
        }}
        .summary-card {{
            background: linear-gradient(135deg, #2c5282 0%, #1e3a5f 100%);
            color: white;
            padding: 24px;
            border-radius: 8px;
            text-align: center;
        }}
        .summary-card h4 {{
            font-size: 0.9em;
            opacity: 0.9;
            margin-bottom: 8px;
        }}
        .summary-card .number {{
            font-size: 2.5em;
            font-weight: 700;
            margin: 8px 0;
        }}
        
        /* Media queries pour mobile */
        @media (max-width: 768px) {{
            body {{ padding: 10px; }}
            .container {{
                margin: 0;
                border-radius: 0;
            }}
            .header {{
                padding: 24px 20px;
            }}
            .header h1 {{ font-size: 1.6em; }}
            .content {{ padding: 20px 16px; }}
            .section h2 {{ font-size: 1.3em; }}
            .stats-grid {{
                grid-template-columns: 1fr;
                gap: 15px;
            }}
            .summary-cards {{
                grid-template-columns: 1fr;
                gap: 12px;
            }}
            .summary-card {{
                padding: 20px;
            }}
            .summary-card .number {{
                font-size: 2em;
            }}
            .card {{
                padding: 20px;
            }}
            .card h3 {{
                font-size: 1.1em;
            }}
        }}
        
        @media (max-width: 480px) {{
            .header h1 {{ font-size: 1.4em; }}
            .section h2 {{ font-size: 1.2em; }}
            .summary-card .number {{
                font-size: 1.8em;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏆 Rapport Match Padel</h1>
            <p>{datetime.now().strftime('%d %B %Y')}</p>
        </div>
        
        <div class="content">
            <div class="section">
                <h2>📊 Résumé du Match</h2>
                <div class="summary-cards">
                    <div class="summary-card">
                        <h4>Total Points</h4>
                        <div class="number">{len(points)}</div>
                    </div>
                    <div class="summary-card">
                        <h4>Joueurs</h4>
                        <div class="number">{len(joueurs)}</div>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <h2>👥 Statistiques par Joueur</h2>
                <div class="stats-grid">
"""

for joueur in joueurs:
    st = stats[joueur]
    total = sum(st.values())
    html += f"""
                    <div class="card">
                        <h3>{joueur}</h3>
                        <div class="stat-line">
                            <span class="stat-label">🏆 Points Gagnants</span>
                            <span class="stat-value">{st['PG']}</span>
                        </div>
                        <div class="stat-line">
                            <span class="stat-label">🎯 Fautes Provoquées</span>
                            <span class="stat-value">{st['FP']}</span>
                        </div>
                        <div class="stat-line">
                            <span class="stat-label">❌ Fautes Directes</span>
                            <span class="stat-value">{st['FD']}</span>
                        </div>
                        <div class="stat-line">
                            <span class="stat-label">📊 Total Actions</span>
                            <span class="stat-value">{total}</span>
                        </div>
                    </div>
"""

html += """
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""

# Sauvegarder
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"\n✅ Rapport généré: {output_path}")
