#!/bin/bash
# Arranque de la instancia: deja Docker y el proyecto listos.
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y docker.io docker-compose-v2 git curl unzip

systemctl enable --now docker
usermod -aG docker ubuntu

mkdir -p /opt/aza
chown ubuntu:ubuntu /opt/aza

cat > /opt/aza/LEEME.txt <<'EOF'
AZA Analyzer - instancia preparada
==================================
1) Copiar el proyecto a /opt/aza:
     scp -i llave.pem -r App-Funcional/. ubuntu@IP:/opt/aza/
2) cd /opt/aza && cp .env.example .env && nano .env
3) docker compose up -d --build
EOF

echo "listo: docker $(docker --version)" > /var/log/aza-bootstrap.log
