#!/bin/bash

# Script de déploiement Padel Stat
# Usage : ./deploy.sh "message du commit"
#
# Le mot de passe SSH n'est plus écrit dans ce fichier : il est lu depuis
# la variable PADELSTAT_SSH_PASSWORD, elle-même chargée depuis .env
# (ignoré par git). Voir .env.example pour le gabarit.

set -e

MSG=${1:-"deploy: mise à jour"}

VPS_HOST=${PADELSTAT_SSH_HOST:-57.129.110.251}
VPS_USER=${PADELSTAT_SSH_USER:-ubuntu}

# Charge .env s'il existe, sans écraser une variable déjà exportée.
if [ -f .env ]; then
  set -a
  . ./.env
  set +a
fi

if [ -z "$PADELSTAT_SSH_PASSWORD" ]; then
  echo "ERREUR : PADELSTAT_SSH_PASSWORD n'est pas defini." >&2
  echo "Copiez .env.example vers .env et renseignez le mot de passe." >&2
  exit 1
fi

# Un « git add -A » aveugle emportait tout ce qui trainait dans l'arbre de
# travail, y compris des fichiers sans rapport avec le deploiement. On montre
# desormais ce qui partirait, et on demande confirmation.
if [ -n "$(git status --porcelain)" ]; then
  echo ">>> Fichiers qui seraient commites :"
  git status --short
  echo
  read -r -p ">>> Commiter ces fichiers ? [o/N] " REPONSE
  case "$REPONSE" in
    o|O|oui|OUI)
      git add -A
      git commit -m "$MSG"
      ;;
    *)
      echo "Commit annule. Commitez ce que vous voulez deployer, puis relancez." >&2
      exit 1
      ;;
  esac
else
  echo ">>> Arbre de travail propre, rien a commiter."
fi

echo ">>> Push GitHub..."
git push origin main

echo ">>> Git pull sur le VPS..."
# Le secret passe par l'environnement, jamais par la ligne de commande :
# il n'apparait donc pas dans la liste des processus.
PADELSTAT_SSH_HOST="$VPS_HOST" PADELSTAT_SSH_USER="$VPS_USER" python3 -c "
import os, sys, paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(
    os.environ['PADELSTAT_SSH_HOST'],
    username=os.environ['PADELSTAT_SSH_USER'],
    password=os.environ['PADELSTAT_SSH_PASSWORD'],
    timeout=15,
)

_, out, err = ssh.exec_command('cd /srv/docker/padelstat && git pull origin main 2>&1')
output = out.read().decode()
print(output)
e = err.read().decode()
if e:
    print('ERR:', e)

ssh.close()

if 'error' in output.lower():
    sys.exit(1)
"

echo ">>> Déploiement terminé !"
