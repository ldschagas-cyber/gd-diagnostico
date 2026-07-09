# Guia de Deploy — Ubuntu Server 24.04
**GD Frete Diagnóstico v2.0.0 · GD Conecta**

---

## Pré-requisitos

- Ubuntu Server 24.04 LTS
- Acesso root ou sudo
- Domínio apontado para o IP do servidor (ex: `app.gdconecta.com.br`)
- Porta 80 e 443 abertas no firewall

---

## 1. Atualização do Sistema

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git ufw
```

---

## 2. Instalação do Docker

```bash
# Remove versões antigas
sudo apt remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

# Instala dependências
sudo apt install -y ca-certificates gnupg lsb-release

# Adiciona repositório Docker
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) \
  signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin

# Adiciona usuário ao grupo docker (evita sudo)
sudo usermod -aG docker $USER
newgrp docker

# Verifica
docker --version
docker compose version
```

---

## 3. Configuração do Firewall

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status
```

---

## 4. Clone do Projeto

```bash
sudo mkdir -p /opt/gd-frete
sudo chown $USER:$USER /opt/gd-frete
cd /opt/gd-frete
git clone https://github.com/sua-org/gd-frete-diagnostico.git .
# Ou copie os arquivos via SCP/SFTP
```

---

## 5. Configuração das Variáveis de Ambiente

```bash
cd /opt/gd-frete
cp backend/.env.example backend/.env
nano backend/.env
```

**Valores obrigatórios para produção:**

```env
ENVIRONMENT=production
DEBUG=false
DATABASE_URL=postgresql+psycopg2://gd_user:SENHA_FORTE@db:5432/gd_frete
SECRET_KEY=$(openssl rand -hex 32)          # gere e cole aqui
BACKEND_CORS_ORIGINS=https://app.gdconecta.com.br
FIRST_SUPERUSER_PASSWORD=SenhaForteAqui@2026
POSTGRES_USER=gd_user
POSTGRES_PASSWORD=SENHA_FORTE
POSTGRES_DB=gd_frete
```

> **ATENÇÃO:** Nunca commite o `.env` no repositório. Guarde as credenciais em um gerenciador de secrets (ex: Bitwarden, AWS Secrets Manager).

---

## 6. Primeiro Deploy

```bash
cd /opt/gd-frete

# Build e sobe todos os serviços
docker compose -f docker-compose.prod.yml up -d --build

# Verifica se os serviços subiram
docker compose -f docker-compose.prod.yml ps

# Acompanha logs
docker compose -f docker-compose.prod.yml logs -f --tail=50
```

---

## 7. Configuração do Nginx Externo (HTTPS / SSL)

O container frontend já tem um Nginx interno, mas recomenda-se um Nginx no host para gerenciar TLS.

### 7.1 Instalar Nginx e Certbot

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
```

### 7.2 Criar Configuração do Site

```bash
sudo nano /etc/nginx/sites-available/gd-frete
```

```nginx
server {
    listen 80;
    server_name app.gdconecta.com.br;

    # Certbot vai adicionar o bloco HTTPS automaticamente
    location / {
        proxy_pass http://localhost:80;   # container frontend
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 50M;
        proxy_read_timeout 120s;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/gd-frete /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 7.3 Obter Certificado SSL (Let's Encrypt)

```bash
sudo certbot --nginx -d app.gdconecta.com.br
```

O Certbot configura o redirecionamento HTTP→HTTPS automaticamente e agenda renovação automática.

---

## 8. Verificação Pós-Deploy

```bash
# Status dos containers
docker compose -f docker-compose.prod.yml ps

# Teste da API
curl https://app.gdconecta.com.br/api/v1/auth/login \
  -X POST -d "username=admin@gdconecta.com.br&password=SuaSenha"

# Logs de erro
docker compose -f docker-compose.prod.yml logs backend --tail=100
```

---

## 9. Backup Automático do Banco de Dados

### 9.1 Script de Backup

```bash
sudo nano /opt/gd-frete/scripts/backup.sh
```

```bash
#!/bin/bash
set -e
BACKUP_DIR="/opt/backups/gd-frete"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/gd_frete_$DATE.sql.gz"

mkdir -p "$BACKUP_DIR"

# Executa pg_dump dentro do container
docker exec gd_frete_db pg_dump \
  -U gd_user gd_frete | gzip > "$BACKUP_FILE"

echo "Backup criado: $BACKUP_FILE"

# Remove backups com mais de 30 dias
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +30 -delete
echo "Backups antigos removidos."
```

```bash
sudo chmod +x /opt/gd-frete/scripts/backup.sh
```

### 9.2 Agendar via Cron

```bash
sudo crontab -e
```

```
# Backup diário às 2h da madrugada
0 2 * * * /opt/gd-frete/scripts/backup.sh >> /var/log/gd-frete-backup.log 2>&1
```

---

## 10. Restore do Banco de Dados

```bash
# Para o backend para evitar conflitos
docker compose -f docker-compose.prod.yml stop backend

# Restaura o backup
gunzip -c /opt/backups/gd-frete/gd_frete_20260101_020000.sql.gz \
  | docker exec -i gd_frete_db psql -U gd_user gd_frete

# Reinicia o backend
docker compose -f docker-compose.prod.yml start backend
```

---

## 11. Atualização da Aplicação (Nova Versão)

```bash
cd /opt/gd-frete

# 1. Baixa nova versão
git pull origin main

# 2. Rebuild e restart (sem downtime: --no-deps sobe os containers modificados)
docker compose -f docker-compose.prod.yml up -d --build

# 3. As migrations são aplicadas automaticamente no startup do backend
# Verifique os logs:
docker compose -f docker-compose.prod.yml logs backend --tail=50

# 4. Verifica se tudo está saudável
docker compose -f docker-compose.prod.yml ps
```

---

## 12. Monitoramento Básico

```bash
# Uso de recursos
docker stats

# Logs em tempo real
docker compose -f docker-compose.prod.yml logs -f

# Healthcheck
watch -n 5 "docker compose -f docker-compose.prod.yml ps"
```
