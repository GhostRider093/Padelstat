# 🎤 Nouveau Système de Commandes Vocales - Double OK

## 📋 Changements Importants

### ✅ Nouveau Format Obligatoire

**Format unique : "OK [commande] OK"**

Exemples :
- `OK point Arnaud service OK`
- `OK faute directe Pierre OK`
- `OK point Thomas smash OK`

### 🔄 Simplification "point gagnant" → "point"

Au lieu de dire "point gagnant", dites juste **"point"** :
- ✅ `OK point Arnaud service OK`
- ❌ `OK point gagnant Arnaud service OK` (fonctionne aussi, mais plus long)

## 🎯 Comment ça marche

### Méthode 1 : Format Complet (Recommandé)

Dire tout d'un coup : **"OK point Arnaud service OK"**

→ La commande est parsée, validée et exécutée immédiatement

### Méthode 2 : Format en 2 Temps

1. Dire : **"OK point Arnaud service"**
   - Le système affiche : `⏳ EN ATTENTE : Arnaud - service → Dites 'OK' pour valider`

2. Dire : **"OK"**
   - Le système valide et enregistre le point

## 📝 Commandes Disponibles

### Annotations de Points

```
OK point [joueur] [type_coup] OK
OK faute directe [joueur] OK
OK faute provoquée [joueur] [type_coup] OK
```

**Joueurs** : Arnaud, Pierre, Thomas, Lucas (selon votre config)

**Types de coup** :
- service
- volée / volé / vollée
- smash
- bandeja
- víbora / vibora
- coup droit
- revers
- lob
- chiquita
- amorti
- fond de court
- balle haute

**Exemples complets** :
```
OK point Arnaud service OK
OK point Pierre volée OK
OK point Thomas smash OK
OK faute directe Lucas OK
OK faute provoquée Pierre revers OK
OK point Arnaud bandeja OK
```

### Commandes de Contrôle

```
OK pause OK
OK lecture OK
OK supprimer OK
OK sauvegarder OK
OK rapport OK
```

## ⚠️ Validation Stricte

Le système **rejette** les commandes incomplètes :

❌ `OK point Arnaud OK` → Manque le type de coup
✅ `OK point Arnaud service OK` → Complet, enregistré

❌ `OK faute directe OK` → Manque le joueur
✅ `OK faute directe Pierre OK` → Complet, enregistré

## 🔍 Logs Automatiques

Toutes les commandes sont loggées dans `data/voice_commands.log` :
- Transcription brute
- Format détecté (OK...OK ou OK... en attente)
- Parsing
- Validation
- Action effectuée

Pour voir les logs :
```bash
# Dernières commandes
python show_voice_logs.py -n 10

# Ou menu interactif
show_voice_logs.bat
```

## 💡 Conseils

1. **Articulez bien** les noms de joueurs
2. **Dites "OK" fermement** au début et à la fin
3. **Séparez les mots** : "OK - point - Arnaud - service - OK"
4. **Vérifiez l'écran** : le statut indique ce qui a été compris
5. **En cas d'erreur** : `OK supprimer OK` puis recommencez

## 🐛 Problèmes Fréquents

### "EN ATTENTE" mais pas de validation

**Cause** : Le système a compris "OK point Arnaud service" mais attend le "OK" final

**Solution** : Dites juste "OK" pour valider

### "COMMANDE INCOMPLÈTE"

**Cause** : Il manque un champ obligatoire (joueur ou type de coup)

**Solution** : Vérifiez les logs (`show_voice_logs.py -n 1`) pour voir ce qui manque

### Le joueur n'est pas reconnu

**Cause** : 
- Nom mal prononcé
- Nom pas dans la config

**Solution** : 
1. Vérifiez `app/config/players.json`
2. Consultez les logs pour voir la transcription exacte
3. Ajoutez le nom si nécessaire

## 📊 Exemples de Sessions

### Session Simple
```
Vous: "OK point Arnaud service OK"
App:  ✅ Point enregistré : Arnaud - service

Vous: "OK point Pierre volée OK"
App:  ✅ Point enregistré : Pierre - volée

Vous: "OK supprimer OK"
App:  🗑️ Point supprimé
```

### Session en 2 Temps
```
Vous: "OK point Thomas smash"
App:  ⏳ EN ATTENTE : Thomas - smash → Dites 'OK' pour valider

Vous: "OK"
App:  ✅ Point enregistré : Thomas - smash
```

### Session avec Erreur
```
Vous: "OK point Lucas OK"
App:  ❌ COMMANDE INCOMPLÈTE

Logs: "⚠️ CHAMPS MANQUANTS: TYPE DE COUP"

Vous: "OK point Lucas service OK"
App:  ✅ Point enregistré : Lucas - service
```

## 🚀 Migration depuis l'ancien système

| Ancien Format | Nouveau Format |
|--------------|----------------|
| `point gagnant Arnaud service` | `OK point Arnaud service OK` |
| `OK point gagnant Pierre volée` | `OK point Pierre volée OK` |
| `FAUTE directe Thomas` | `OK faute directe Thomas OK` |
| `OK pause` | `OK pause OK` |

## 📞 Support

En cas de problème :
1. Consultez les logs : `show_voice_logs.bat`
2. Regardez la transcription brute
3. Vérifiez le parsing et la validation
4. Ajustez votre prononciation
