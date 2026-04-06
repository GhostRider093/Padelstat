# 🐛 Guide de Debug des Commandes Vocales

## 📋 Système de Logging Automatique

Le système enregistre automatiquement **toutes** les commandes vocales dans un fichier de log détaillé.

### 📁 Localisation

Fichier de log : `data/voice_commands.log`

### 📊 Informations Enregistrées

Chaque commande vocale est tracée avec :

1. **TRANSCRIPTION BRUTE** : Ce que Google Speech Recognition a entendu
2. **APRÈS NETTOYAGE** : Texte normalisé (lowercase, trim)
3. **DÉTECTION MOT DE RÉVEIL** : OK/POINT/FAUTE détecté ?
4. **RÉSULTAT DU PARSING** : Extraction des champs (joueur, type_coup, etc.)
5. **VALIDATION** : La commande est-elle complète ?
6. **ACTION** : Ce qui a été fait (ENREGISTRÉ/REJETÉ/IGNORÉ)
7. **ERREUR** : Message d'erreur si problème

### 🎯 Exemple de Log

```
================================================================================
COMMANDE #12 - 2025-12-22 15:30:45.123
================================================================================

[1] TRANSCRIPTION BRUTE:
    'OK point gagnant Arnaud service'

[2] APRÈS NETTOYAGE:
    'ok point gagnant arnaud service'

[3] DÉTECTION MOT DE RÉVEIL:
    ✅ Détecté: 'OK'
    → Commande extraite: 'point gagnant arnaud service'

[4] RÉSULTAT DU PARSING:
    ✅ Parsing réussi:
       • action: nouveau_point
       • joueur: Arnaud
       • type_point: point_gagnant
       • type_coup: service

[5] VALIDATION:
    ✅ VALIDE: Commande complète

[6] ACTION:
    ✅ ENREGISTRÉ: point_gagnant - Arnaud - service

--------------------------------------------------------------------------------
```

## 🔍 Visualisation des Logs

### Méthode 1 : Script Batch (Recommandé)

Double-cliquez sur `show_voice_logs.bat`

Options disponibles :
- **1** : Voir les 10 dernières commandes
- **2** : Voir les 20 dernières commandes
- **3** : Voir tous les logs
- **4** : Rechercher un mot spécifique
- **5** : Effacer les logs (backup auto)
- **6** : Ouvrir dans Notepad

### Méthode 2 : Ligne de Commande

```bash
# Voir les 10 dernières commandes
python show_voice_logs.py -n 10

# Voir les 20 dernières
python show_voice_logs.py -n 20

# Rechercher "service"
python show_voice_logs.py -s service

# Rechercher "Arnaud"
python show_voice_logs.py -s Arnaud

# Voir tout
python show_voice_logs.py

# Effacer les logs (backup auto)
python show_voice_logs.py -c
```

### Méthode 3 : Éditeur de Texte

Ouvrir directement : `data\voice_commands.log`

## 🐛 Comment Déboguer un Problème

### Problème : "Commande non reconnue"

1. Vérifier **[4] RÉSULTAT DU PARSING**
2. Si `❌ Parsing échoué` → La commande n'a pas matché de pattern
3. Vérifier que vous utilisez les bons mots-clés :
   - `point gagnant`, `faute directe`, `faute provocquée`
   - `service`, `volée`, `smash`, etc.

### Problème : "POINT INCOMPLET"

1. Vérifier **[5] VALIDATION**
2. Le message indique quel champ manque :
   - `❌ INVALIDE: Il manque le nom du joueur`
   - `❌ INVALIDE: Il manque le type de coup`
3. Regarder **[4] RÉSULTAT DU PARSING** pour voir ce qui a été extrait

### Problème : "Joueur non reconnu"

1. Vérifier **[4] RÉSULTAT DU PARSING**
2. Si `joueur: None` → Le nom n'a pas été détecté
3. Causes possibles :
   - Nom mal prononcé/transcrit
   - Nom pas dans la config (`app/config/players.json`)
   - Parser pas synchronisé (bug interne)

### Problème : "Pas de mot de réveil"

1. Vérifier **[3] DÉTECTION MOT DE RÉVEIL**
2. Si `❌ Aucun mot de réveil détecté` :
   - Commencer par "OK", "POINT" ou "FAUTE"
   - Vérifier la transcription brute **[1]**

## 📈 Statistiques d'Utilisation

Le logger compte automatiquement :
- Nombre total de commandes
- Horodatage de début de session
- Taille du fichier de log

## 🧹 Nettoyage des Logs

### Backup Automatique

La commande `python show_voice_logs.py -c` crée automatiquement un backup :
- Format : `voice_commands.log.backup_20251222_153045`
- Conservé dans le même dossier `data/`

### Logs Multiples

Les logs s'accumulent dans **un seul fichier** par session.
Pour une nouvelle session propre, effacez les logs avant de lancer l'application.

## 🔧 Debug Avancé

### Activer les Logs Console

Les logs sont **aussi** affichés dans la console de l'application :

```
[Voice] Commande reçue: 'ok point gagnant Arnaud service'
[Voice Status] ✅ Point enregistré
```

### Parser Debug

Pour tester le parser en isolation :
```bash
python test_parser_debug.py
```

## 💡 Conseils

1. **Consultez les logs après chaque problème** pour comprendre ce qui s'est passé
2. **Recherchez par joueur** : `python show_voice_logs.py -s Arnaud`
3. **Recherchez par type** : `python show_voice_logs.py -s service`
4. **Gardez les logs** pour analyse ultérieure (backup auto)
5. **Vérifiez la transcription brute** pour voir si Google a bien compris

## ❓ Problèmes Fréquents

| Symptôme | Cause Probable | Solution |
|----------|---------------|----------|
| Rien ne s'enregistre | Pas de mot de réveil | Dire "OK", "POINT" ou "FAUTE" avant |
| Joueur = None | Nom mal prononcé | Vérifier transcription brute dans logs |
| Type_coup = None | Mot-clé non reconnu | Utiliser "service", "volée", "smash", etc. |
| Validation échoue | Champ manquant | Vérifier parsing - dire la commande complète |
| Log vide | Logger pas initialisé | Vérifier que VoiceLogger est importé |

## 📞 Support

Si un problème persiste :
1. Copiez les logs de la commande problématique
2. Notez la transcription brute **[1]**
3. Notez le message d'erreur **[7]**
4. Partagez ces infos pour analyse
