# Cahier des Charges — Tracking des Joueurs (Padel)

## 1. Objectif
Définir un système de **tracking des joueurs** à partir d’une vidéo de match de padel, permettant d’identifier et suivre chaque joueur dans le temps, avec un identifiant stable, pour alimenter les analyses vidéo/statistiques.

## 2. Périmètre
- Vidéo **caméra fixe** (idéalement vue globale du terrain).
- 4 joueurs simultanés sur le terrain.
- Tracking en **temps quasi‑réel** ou batch (post‑traitement).

## 3. Définitions
- **Détection** : localiser un joueur dans une frame (bbox ou pose).
- **Tracking** : associer une détection à un identifiant stable à travers le temps.
- **ID Switch** : erreur d’identité (un joueur prend l’ID d’un autre).
- **Occlusion** : joueur partiellement ou totalement masqué.

## 4. Exigences Fonctionnelles
1. **Détection des joueurs** par frame.
2. **Assignation d’un ID stable** pour chaque joueur (4 IDs).
3. **Résistance aux occlusions** courtes (ex. 1–3 secondes).
4. **Export des trajectoires** :
   - JSON: positions par frame (x, y, w, h) + timestamp.
   - CSV: format tabulaire pour analyse.
5. **Aperçu visuel** (vidéo annotée avec IDs).

## 5. Exigences Non Fonctionnelles
- **Robustesse** : taux d’ID switch < 5% sur une séquence test.
- **Performance** : traitement ≥ 10 FPS (objectif), ≥ 5 FPS (minimum).
- **Compatibilité** : Windows + GPU CUDA si disponible.

## 6. Données & Entrées
### Entrées minimales
- Fichier vidéo `.mp4` (résolution ≥ 720p recommandé).

### Entrées optionnelles
- Calibration du terrain (zones de jeu, lignes).
- Annotations manuelles (pour évaluer le tracking).

## 7. Sorties attendues
### JSON
```json
{
  "meta": { "video": "match.mp4", "fps": 30 },
  "frames": [
    {
      "frame": 123,
      "timestamp_sec": 4.10,
      "players": [
        { "id": 1, "bbox": [x1,y1,x2,y2], "conf": 0.92 },
        { "id": 2, "bbox": [x1,y1,x2,y2], "conf": 0.88 }
      ]
    }
  ]
}
```

### CSV (exemple)
```
frame,timestamp,id,x1,y1,x2,y2,conf
123,4.10,1,100,200,180,320,0.92
```

### Vidéo annotée
`match_tracking.mp4` (bboxes + IDs + couleurs fixes).

## 8. Pipeline Cible (Haute Niveau)
1. **Détection** (YOLO/Pose).
2. **Association** frame‑to‑frame (tracker : ByteTrack, DeepSORT, OC‑SORT).
3. **Stabilisation** des IDs.
4. **Export & visualisation**.

## 9. Métriques d’Évaluation
- **MOTA / IDF1**
- **# ID Switches**
- **Precision/Recall de détection**
- **Taux de frames sans détection**

## 10. Hypothèses
- Caméra fixe (pas de mouvement).
- Champ de vision couvrant tout le terrain.
- Luminosité suffisante.

## 11. Contraintes
- Occlusions fréquentes (croisements, doubles au filet).
- Joueurs avec tenues similaires.

## 12. Livrables
1. Script de tracking (CLI/GUI).
2. Exports JSON/CSV.
3. Vidéo annotée.
4. Rapport d’évaluation (sur vidéo test).

## 13. Risques & Contournements
- **ID switch** : utiliser tracker + ré‑identification.
- **Mauvaise détection** : finetune modèle ou masque du terrain.
- **Occlusions longues** : relier par position + modèle de mouvement.

## 14. Questions Ouvertes
- Caméra unique ou multi‑cam ?
- Besoin de ré‑identification sur plusieurs matchs ?
- Niveau de précision attendu (amateur vs pro) ?
- Intégration directe dans l’app principale ?
