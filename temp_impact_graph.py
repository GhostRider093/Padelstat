import json
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
import os

# Charger la police Bebas Neue si disponible
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

# Lire le fichier autosave
with open(r'e:\projet\padel stat\data\autosave_VID_20251217_120454_20251219_232206.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Récupérer les joueurs
joueurs = [j['nom'] for j in data['match']['joueurs']]
points = data['points']

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
            fontsize=24, fontweight='bold', color='white',
            fontproperties=bebas_font if bebas_font else None)
    
    # Valeur de l'impact
    ax.text(bar.get_x() + bar.get_width()/2., height/2,
            f'{int(height):+d}',
            ha='center', va='center',
            fontsize=28, fontweight='bold', color='white',
            fontproperties=bebas_font if bebas_font else None)

# Personnaliser le graphique
ax.set_ylabel('Impact (Points)', fontsize=16, fontweight='bold', color='white',
               fontproperties=bebas_font if bebas_font else None)
ax.set_title('IMPACT DES JOUEURS', fontsize=36, fontweight='bold', 
             color='white', pad=30,
             fontproperties=bebas_font if bebas_font else None)
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
plt.show()

# Afficher aussi les détails
print("\n" + "="*50)
print("IMPACT DES JOUEURS")
print("="*50)
for joueur in impact_trie.keys():
    print(f"{joueur:15} : {impact_trie[joueur]:+3d} points")
print("="*50)
