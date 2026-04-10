# Déploiement Padel Stat

## Infrastructure

- **VPS** : `57.129.110.251` (Ubuntu)
- **Utilisateur** : `ubuntu`
- **Container Docker** : `padelstat` (nginx:alpine, port **8012**)
- **Dossier sur le VPS** : `/srv/docker/padelstat/`
- **Dépôt GitHub** : https://github.com/GhostRider093/Padelstat
- **Fichier principal** : `index.html` (servi directement par nginx)

## Fonctionnement

nginx sert le contenu de `/srv/docker/padelstat/` directement.  
Le fichier `index.html` = l'application complète (`padel_frontend.html` renommé).

## Processus de déploiement

1. Faire les modifications en local
2. Commit + push sur GitHub (`main`)
3. SSH sur le VPS → `git pull` dans `/srv/docker/padelstat/`

Le script `deploy.sh` (à la racine) automatise les étapes 2 et 3.

## Déploiement rapide

```bash
./deploy.sh "message du commit"
```

## Structure clé sur le VPS

```
/srv/docker/padelstat/
├── index.html              ← application principale
├── app/
│   └── exports/
│       ├── html_generator.py
│       ├── live_html_generator.py
│       └── ai_analyzer.py
├── docker-compose.yml
└── deploy.sh
```
