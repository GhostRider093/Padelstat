# SimpleFileExplorer

Petit explorateur de fichiers Android, en Kotlin. Une seule activité, liste de
fichiers/dossiers, navigation par tap, ouverture des fichiers via l'app par
défaut du système.

Indépendant du reste du dépôt Padelstat (peut être déplacé tel quel).

## Fonctionnalités

- Liste les fichiers et dossiers (dossiers en haut, triés A→Z).
- Tap sur un dossier : entre dedans. Tap sur un fichier : ouvre via une autre app.
- Bouton retour : remonte au dossier parent.
- Affiche le chemin courant et la taille des fichiers.
- Demande la permission « Tous les fichiers » (Android 11+) ou
  `READ_EXTERNAL_STORAGE` (Android ≤ 10).

## Construire et installer

Tu as deux options :

### Option A — Android Studio (le plus simple)

1. Ouvre Android Studio → *Open an existing project* → choisis le dossier
   `SimpleFileExplorer/`.
2. Laisse Gradle se synchroniser (il téléchargera le wrapper la première fois).
3. Branche ton téléphone en USB avec le **debug USB** activé.
4. Clique *Run* (▶). L'app s'installe et démarre.

### Option B — Ligne de commande

```bash
cd SimpleFileExplorer
./gradlew assembleDebug
adb install app/build/outputs/apk/debug/app-debug.apk
```

(Il faut le SDK Android et `adb` installés. Si `gradle/wrapper/gradle-wrapper.jar`
manque, lance d'abord `gradle wrapper` une fois depuis un Gradle local pour le
générer.)

## Permissions

Au premier lancement, l'app ouvre la page des réglages pour accorder
« Accès à tous les fichiers » (sur Android 11+). Sans cette permission,
elle ne pourra pas lister la mémoire interne.

## Limites volontaires (resté simple)

- Pas de copier/coller, pas de suppression, pas de création de dossier.
- Pas de recherche, pas de tri configurable.
- Pas d'aperçu intégré : on délègue l'ouverture aux apps installées.
