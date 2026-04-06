"""
Génère un tableau chronologique unifié pour comparer les 4 joueurs côte à côte
"""
import re
from bs4 import BeautifulSoup

def extraire_donnees_chrono_html(html_path):
    """Extrait les données chronologiques du rapport HTML"""
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # Trouver la section "Analyse chronologique"
    section_chrono = None
    for h2 in soup.find_all('h2'):
        if 'Analyse chronologique' in h2.get_text():
            section_chrono = h2.parent
            break
    
    if not section_chrono:
        print("❌ Section chronologique non trouvée")
        return {}
    
    # Extraire les données de chaque joueur
    data_joueurs = {}
    stat_cards = section_chrono.find_all('div', class_='stat-card')
    
    for card in stat_cards:
        # Nom du joueur
        h3 = card.find('h3')
        if not h3:
            continue
        joueur = h3.get_text().strip()
        
        # Initialiser les tranches
        data_joueurs[joueur] = {
            "0-20%": {"FD": 0, "PG": 0, "FP": 0, "FS": 0},
            "20-40%": {"FD": 0, "PG": 0, "FP": 0, "FS": 0},
            "40-60%": {"FD": 0, "PG": 0, "FP": 0, "FS": 0},
            "60-80%": {"FD": 0, "PG": 0, "FP": 0, "FS": 0},
            "80-100%": {"FD": 0, "PG": 0, "FP": 0, "FS": 0}
        }
        
        # Extraire les stats de chaque tranche
        tranche_actuelle = None
        for item in card.find_all('div'):
            text = item.get_text().strip()
            
            # Détecter la tranche
            if '🕒' in text and 'du match' in text:
                match = re.search(r'(\d+-\d+%)', text)
                if match:
                    tranche_actuelle = match.group(1)
            
            # Extraire les valeurs
            elif tranche_actuelle:
                if '⚠️ Fautes directes' in text:
                    valeur = re.search(r'(\d+)$', text)
                    if valeur:
                        data_joueurs[joueur][tranche_actuelle]["FD"] = int(valeur.group(1))
                elif '🏆 Points gagnants' in text:
                    valeur = re.search(r'(\d+)$', text)
                    if valeur:
                        data_joueurs[joueur][tranche_actuelle]["PG"] = int(valeur.group(1))
                elif '🎯 Fautes provoquées' in text:
                    valeur = re.search(r'(\d+)$', text)
                    if valeur:
                        data_joueurs[joueur][tranche_actuelle]["FP"] = int(valeur.group(1))
                elif '🚫 Fautes subies' in text:
                    valeur = re.search(r'(\d+)$', text)
                    if valeur:
                        data_joueurs[joueur][tranche_actuelle]["FS"] = int(valeur.group(1))
    
    return data_joueurs

def generer_tableau_unifie(data_joueurs, output_path):
    """Génère un tableau HTML unifié avec tous les joueurs côte à côte"""
    
    joueurs = list(data_joueurs.keys())
    tranches = ["0-20%", "20-40%", "40-60%", "60-80%", "80-100%"]
    stats = [
        ("⚠️ Fautes directes", "FD"),
        ("🏆 Points gagnants", "PG"),
        ("🎯 Fautes provoquées", "FP"),
        ("🚫 Fautes subies", "FS")
    ]
    
    couleurs_joueurs = {
        joueurs[0]: "#667eea",
        joueurs[1]: "#ff6b6b",
        joueurs[2]: "#51cf66",
        joueurs[3]: "#ffd43b"
    } if len(joueurs) >= 4 else {}
    
    html = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Tableau Chronologique Unifié</title>
    <style>
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            background: #f8f9fa;
            padding: 40px;
        }
        .container {
            max-width: 1600px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            padding: 40px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        h1 {
            color: #1e293b;
            text-align: center;
            margin-bottom: 10px;
        }
        .subtitle {
            color: #666;
            text-align: center;
            margin-bottom: 40px;
        }
        .tranche-section {
            margin-bottom: 50px;
        }
        .tranche-section h2 {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            font-size: 1.3em;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        thead tr {
            background: #f8f9fa;
        }
        th {
            padding: 15px;
            text-align: center;
            font-weight: 600;
            color: #1e293b;
            border-bottom: 2px solid #e2e8f0;
        }
        th:first-child {
            text-align: left;
            width: 200px;
        }
        td {
            padding: 15px;
            text-align: center;
            border-bottom: 1px solid #e2e8f0;
        }
        td:first-child {
            font-weight: 600;
            text-align: left;
            color: #667eea;
        }
        tbody tr:hover {
            background: #f8f9fa;
        }
        .best-value {
            background: #d3f9d8 !important;
            font-weight: bold;
        }
        .worst-value {
            background: #ffe0e0 !important;
        }
        .player-header {
            font-weight: 700;
            font-size: 1.1em;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Analyse Chronologique Unifiée</h1>
        <p class="subtitle">Comparaison des 4 joueurs par tranches de 20% du match</p>
"""
    
    # Générer un tableau pour chaque tranche
    for tranche in tranches:
        html += f"""
        <div class="tranche-section">
            <h2>🕒 {tranche} du match</h2>
            <table>
                <thead>
                    <tr>
                        <th>Statistique</th>
"""
        
        # En-têtes des colonnes (joueurs)
        for joueur in joueurs:
            couleur = couleurs_joueurs.get(joueur, "#667eea")
            html += f'                        <th class="player-header" style="color: {couleur};">{joueur}</th>\n'
        
        html += """                    </tr>
                </thead>
                <tbody>
"""
        
        # Lignes de statistiques
        for label, key in stats:
            html += f"""                    <tr>
                        <td>{label}</td>
"""
            
            # Valeurs pour chaque joueur
            valeurs = [data_joueurs[j][tranche][key] for j in joueurs]
            
            # Trouver la meilleure et la pire valeur
            # Pour FD et FS, le meilleur est le plus bas
            if key in ["FD", "FS"]:
                valeurs_non_nulles = [v for v in valeurs if v > 0]
                best = min(valeurs_non_nulles) if valeurs_non_nulles else None
                worst = max(valeurs) if any(v > 0 for v in valeurs) else None
            else:
                best = max(valeurs) if any(v > 0 for v in valeurs) else None
                worst = min(valeurs) if any(v > 0 for v in valeurs) else None
            
            for joueur in joueurs:
                val = data_joueurs[joueur][tranche][key]
                classe = ""
                if val == best and best is not None and val != 0 and len([v for v in valeurs if v == best]) == 1:
                    classe = ' class="best-value"'
                elif val == worst and worst is not None and val != 0 and len([v for v in valeurs if v == worst]) == 1 and best != worst:
                    classe = ' class="worst-value"'
                
                html += f'                        <td{classe}>{val}</td>\n'
            
            html += """                    </tr>
"""
        
        html += """                </tbody>
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
</body>
</html>
"""
    
    # Sauvegarder
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ Tableau unifié généré: {output_path}")

# Charger le dernier rapport HTML
import glob
import os

rapports = glob.glob("data/rapport_*.html")
if rapports:
    dernier_rapport = max(rapports, key=os.path.getctime)
    print(f"📄 Analyse du rapport: {dernier_rapport}")
    
    # Extraire les données
    data = extraire_donnees_chrono_html(dernier_rapport)
    
    if data:
        print(f"\n✅ {len(data)} joueurs trouvés: {', '.join(data.keys())}")
        
        # Afficher un aperçu
        for joueur, tranches in data.items():
            total = sum(sum(t.values()) for t in tranches.values())
            print(f"  - {joueur}: {total} actions au total")
        
        # Générer le tableau unifié
        output = "data/test_tableau_chrono_unifie.html"
        generer_tableau_unifie(data, output)
    else:
        print("❌ Aucune donnée chronologique trouvée")
else:
    print("❌ Aucun rapport HTML trouvé dans data/")
