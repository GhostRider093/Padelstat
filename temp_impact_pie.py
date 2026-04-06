import json
import matplotlib.pyplot as plt
import numpy as np

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

# Normalisation selon ta méthode
impacts_list = list(impact.values())
min_impact = min(impacts_list)
max_impact = max(impacts_list)
plage_totale = max_impact - min_impact

print(f"\nImpact minimum : {min_impact}")
print(f"Impact maximum : {max_impact}")
print(f"Plage totale : {plage_totale} points = 100%\n")

# Normaliser les valeurs (décaler pour avoir que des positifs)
impact_normalise = {joueur: val - min_impact for joueur, val in impact.items()}

# Créer le graphique en camembert
fig, ax = plt.subplots(figsize=(10, 8))

noms = list(impact_normalise.keys())
valeurs = list(impact_normalise.values())
impacts_bruts = [impact[nom] for nom in noms]

# Couleurs selon l'impact brut (positif/négatif)
couleurs = []
for val_brut in impacts_bruts:
    if val_brut > 0:
        couleurs.append('#51cf66')  # Vert pour positif
    elif val_brut < 0:
        couleurs.append('#ff6b6b')  # Rouge pour négatif
    else:
        couleurs.append('#aaaaaa')  # Gris pour neutre

# Créer les labels avec l'impact brut et le pourcentage
labels = [f"{nom}\n({impacts_bruts[i]:+d} pts)" for i, nom in enumerate(noms)]

# Créer le camembert
wedges, texts, autotexts = ax.pie(valeurs, labels=labels, colors=couleurs,
                                    autopct='%1.1f%%', startangle=90,
                                    textprops={'fontsize': 12, 'weight': 'bold'},
                                    explode=[0.05] * len(valeurs))

# Améliorer l'apparence
for autotext in autotexts:
    autotext.set_color('white')
    autotext.set_fontsize(11)
    autotext.set_weight('bold')

ax.set_title('Repartition de l\'impact des joueurs\n(Normalise sur la plage totale)', 
             fontsize=16, fontweight='bold', pad=20)

# Ajouter une note explicative
note = f"Plage totale: {plage_totale} points (de {min_impact} a +{max_impact})"
plt.figtext(0.5, 0.02, note, ha='center', fontsize=10, style='italic')

plt.tight_layout()
plt.show()

# Afficher les détails
print("="*50)
print("REPARTITION DE L'IMPACT")
print("="*50)
for nom in noms:
    impact_brut = impact[nom]
    impact_norm = impact_normalise[nom]
    pourcentage = (impact_norm / plage_totale * 100) if plage_totale > 0 else 0
    print(f"{nom:15} : {impact_brut:+3d} pts -> {pourcentage:5.1f}%")
print("="*50)
