# Configuration Biomech (Résumé)

## Environnement IA
- `ultralytics` installé (YOLOv8 pose).
- PyTorch CUDA activé (`torch` + `torchvision` build `cu121`).
- GPU détecté : NVIDIA GeForce RTX 4070 Ti.

## Script principal
- Fichier : `biomech_gui.py`.
- Interface Tkinter pour analyse vidéo + pose.

## Fonctions UI disponibles
- Chargement vidéo via explorateur.
- Pré‑analyse vidéo (frames, FPS, durée, résolution, taille).
- Sélecteur modèle YOLO pose (`yolov8n/s/m/l/x-pose.pt`).
- Sélecteur device (`auto`, `cpu`, `cuda:0`).
- Option `FP16` (uniquement CUDA).
- Mode `Frames max` et `Stride`.
- Option “Traiter toute la vidéo”.
- Sélecteur unités : `pixels` ou `metres`.
- Bouton `Calibration` (homographie demi‑terrain haut).
- Aperçu vidéo annoté.
- Boutons d’accès aux sorties : `Ouvrir dossier`, `Ouvrir HTML`, `Ouvrir JSON`, `Ouvrir CSV`.

## Calibration (mode mètres)
- 4 points cliqués dans l’ordre :
  1. Filet gauche
  2. Haut gauche
  3. Haut droit
  4. Filet droit
- Demi‑terrain haut pris comme rectangle 10 m × 10 m.
- Point de contrôle optionnel : intersection ligne de service × ligne centrale (attendu à 5 m, 3 m).
- Fichier sauvegardé : `*_calibration.json`.

## Exports générés
- Vidéo annotée : `*_pose.mp4`.
- Données brutes :
  - JSON : `*_pose.json`
  - CSV : `*_pose.csv` (inclut `track_id`, bbox, positions, keypoints, + coordonnées mètres si calibration).
- Analyse globale :
  - JSON : `*_pose_analysis.json`
  - CSV : `*_pose_analysis.csv`
  - HTML : `*_pose_analysis.html`

## Tracking & Stats ajoutés
- Tracking simple (IDs stables par proximité).
- Distance parcourue par joueur.
- Vitesse moyenne par joueur.
- Compteurs “coup droit / revers” (heuristique pose, joueurs droitiers).

## Où sont les fichiers
- Tous les fichiers de sortie sont écrits **dans le même dossier que la vidéo analysée**.
