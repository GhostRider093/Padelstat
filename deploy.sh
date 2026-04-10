#!/bin/bash

# Script de déploiement Padel Stat
# Usage : ./deploy.sh "message du commit"

set -e

MSG=${1:-"deploy: mise à jour"}

echo ">>> Commit & push GitHub..."
git add -A
git commit -m "$MSG" || echo "(rien à committer)"
git push origin main

echo ">>> Git pull sur le VPS..."
python3 -c "
import paramiko, sys

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('57.129.110.251', username='ubuntu', password='Nano+0056255431', timeout=15)

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
