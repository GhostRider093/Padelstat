import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
import os

# Charger les données du dernier autosave
autosave_file = r'e:\projet\padel stat\data\autosave_VID_20251217_120454_20251219_232206.json'

with open(autosave_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

points = data.get('points', [])
joueurs = data.get('match_info', {}).get('joueurs', [])

# Calculer l'évolution de l'impact au fil du match
evolution = {joueur: [0] for joueur in joueurs}  # Commencer à 0
impact_cumul = {joueur: 0 for joueur in joueurs}

for i, point in enumerate(points):
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
    
    # Enregistrer l'impact cumulé après chaque point
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
        print(f"✅ Police Bebas Neue chargée: {font_path}")
        break

# Créer le graphique
fig, ax = plt.subplots(figsize=(16, 8), facecolor='#1a1a2e')
ax.set_facecolor('#16213e')

# Couleurs pour chaque joueur
colors = ['#4ecca3', '#ffd43b', '#ff6b6b', '#845ef7']

# Tracer l'évolution pour chaque joueur
x = list(range(len(evolution[joueurs[0]])))

for i, joueur in enumerate(joueurs):
    y = evolution[joueur]
    color = colors[i % len(colors)]
    
    # Ligne avec marqueurs
    ax.plot(x, y, color=color, linewidth=3, marker='o', markersize=4, 
            label=joueur.upper(), alpha=0.9)
    
    # Remplir sous la courbe
    ax.fill_between(x, 0, y, color=color, alpha=0.15)

# Ligne de référence à 0
ax.axhline(y=0, color='white', linestyle='-', linewidth=2, alpha=0.5)

# Personnaliser le graphique
ax.set_xlabel('Points du match', fontsize=18, fontweight='bold', color='white',
              fontproperties=bebas_font if bebas_font else None)
ax.set_ylabel('Impact cumulé', fontsize=18, fontweight='bold', color='white',
              fontproperties=bebas_font if bebas_font else None)
ax.set_title('ÉVOLUTION TEMPORELLE DE L\'IMPACT', fontsize=36, fontweight='bold', 
            color='white', pad=30,
            fontproperties=bebas_font if bebas_font else None)

# Grille
ax.grid(True, alpha=0.2, linestyle='--', color='white')

# Légende
legend = ax.legend(loc='upper left', fontsize=14, framealpha=0.9, facecolor='#16213e', 
                   edgecolor='white', labelcolor='white')
if bebas_font:
    for text in legend.get_texts():
        text.set_fontproperties(bebas_font)

# Personnaliser les ticks
ax.tick_params(colors='white', labelsize=12)
for spine in ax.spines.values():
    spine.set_color('white')
    spine.set_linewidth(1.5)

plt.tight_layout()

# Sauvegarder
output_folder = r'e:\projet\padel stat\data\graphs'
os.makedirs(output_folder, exist_ok=True)
output_path = os.path.join(output_folder, 'evolution_temporelle.png')
plt.savefig(output_path, dpi=150, facecolor='#1a1a2e', edgecolor='none')
print(f"✅ Graphique sauvegardé: {output_path}")

plt.show()
