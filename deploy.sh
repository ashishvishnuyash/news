#!/usr/bin/env bash
# Deploy The Republic Bulletin on one Ubuntu/Debian VM.
# Run from the cloned repository:
#   sudo bash deploy.sh --domain news.example.com --email admin@example.com

set -Eeuo pipefail

APP_NAME="republic-bulletin"
API_PORT=8000
WEB_PORT=3000
DOMAIN=""
EMAIL=""
HTTP_ONLY=false

usage() {
  cat <<'EOF'
Usage:
  sudo bash deploy.sh --domain <domain> --email <email> [--http-only]

Options:
  --domain <domain>  Public DNS name pointing to this VM (required).
  --email <email>    Let's Encrypt renewal email (required unless --http-only).
  --http-only        Do not request TLS. Intended only for a private VM or initial DNS setup.
  -h, --help         Show this help text.

The script installs Nginx, Python, Node.js 20, and Certbot; builds the app; and creates
systemd services for the FastAPI API and Next.js frontend. It keeps the database and
uploaded images in this cloned repository, so back up backend/news.db and backend/uploads.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --domain) DOMAIN="${2:-}"; shift 2 ;;
    --email) EMAIL="${2:-}"; shift 2 ;;
    --http-only) HTTP_ONLY=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
  esac
done

if [[ $EUID -ne 0 ]]; then
  echo "Run with sudo: sudo bash deploy.sh --domain <domain> --email <email>" >&2
  exit 1
fi
if [[ -z "$DOMAIN" ]]; then
  echo "--domain is required." >&2
  exit 1
fi
if [[ "$HTTP_ONLY" == false && -z "$EMAIL" ]]; then
  echo "--email is required when TLS is enabled." >&2
  exit 1
fi
if [[ ! "$DOMAIN" =~ ^[A-Za-z0-9.-]+$ ]]; then
  echo "--domain must be a DNS name or IP address without a protocol or path." >&2
  exit 1
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
DEPLOY_USER="${SUDO_USER:-root}"

for required_dir in "$BACKEND_DIR" "$FRONTEND_DIR"; do
  [[ -d "$required_dir" ]] || { echo "Missing expected directory: $required_dir" >&2; exit 1; }
done

if [[ "$HTTP_ONLY" == false && "$DOMAIN" =~ ^[0-9.]+$ ]]; then
  echo "Let's Encrypt requires a DNS name, not an IP address. Use --http-only or provide a domain." >&2
  exit 1
fi

set_env() {
  local file="$1" key="$2" value="$3"
  touch "$file"
  if grep -qE "^${key}=" "$file"; then
    sed -i "s|^${key}=.*|${key}=${value}|" "$file"
  else
    printf '%s=%s\n' "$key" "$value" >> "$file"
  fi
}

echo "Installing system packages..."
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl gnupg nginx openssl python3 python3-venv certbot python3-certbot-nginx

if ! command -v node >/dev/null 2>&1 || [[ "$(node -p 'process.versions.node.split(".")[0]')" -lt 20 ]]; then
  echo "Installing Node.js 20..."
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y nodejs
fi

echo "Preparing backend..."
python3 -m venv "$BACKEND_DIR/venv"
"$BACKEND_DIR/venv/bin/python" -m pip install --upgrade pip
"$BACKEND_DIR/venv/bin/pip" install -r "$BACKEND_DIR/requirements.txt"

BACKEND_ENV="$BACKEND_DIR/.env"
if [[ ! -f "$BACKEND_ENV" ]]; then
  install -m 600 /dev/null "$BACKEND_ENV"
fi
SECRET_KEY="$(grep -E '^SECRET_KEY=' "$BACKEND_ENV" | cut -d= -f2- || true)"
if [[ -z "$SECRET_KEY" || "$SECRET_KEY" == supersecret* ]]; then
  SECRET_KEY="$(openssl rand -hex 32)"
fi
COOKIE_SECURE=false
[[ "$HTTP_ONLY" == false ]] && COOKIE_SECURE=true

set_env "$BACKEND_ENV" "SECRET_KEY" "$SECRET_KEY"
set_env "$BACKEND_ENV" "COOKIE_SECURE" "$COOKIE_SECURE"

set_env "$BACKEND_ENV" "CORS_ORIGIN_REGEX" "^$"
set_env "$BACKEND_ENV" "ALLOWED_HOSTS" "*"
chmod 600 "$BACKEND_ENV"
install -d -m 755 "$BACKEND_DIR/uploads"

echo "Preparing frontend..."
FRONTEND_ENV="$FRONTEND_DIR/.env.local"
set_env "$FRONTEND_ENV" "NEXT_PUBLIC_API_BASE_URL" "https://$DOMAIN"
set_env "$FRONTEND_ENV" "NEXT_PUBLIC_SITE_BASE_URL" "https://$DOMAIN"
if [[ "$HTTP_ONLY" == true ]]; then
  set_env "$FRONTEND_ENV" "NEXT_PUBLIC_API_BASE_URL" "http://$DOMAIN"
  set_env "$FRONTEND_ENV" "NEXT_PUBLIC_SITE_BASE_URL" "http://$DOMAIN"
fi
chown "$DEPLOY_USER":"$DEPLOY_USER" "$FRONTEND_ENV" "$BACKEND_ENV"
chown -R "$DEPLOY_USER":"$DEPLOY_USER" "$BACKEND_DIR/uploads"
runuser -u "$DEPLOY_USER" -- npm ci --prefix "$FRONTEND_DIR"
runuser -u "$DEPLOY_USER" -- npm run build --prefix "$FRONTEND_DIR"

echo "Creating systemd services..."
cat > "/etc/systemd/system/${APP_NAME}-api.service" <<EOF
[Unit]
Description=The Republic Bulletin FastAPI service
After=network.target

[Service]
Type=simple
User=$DEPLOY_USER
WorkingDirectory=$BACKEND_DIR
EnvironmentFile=$BACKEND_ENV
ExecStart=$BACKEND_DIR/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port $API_PORT --proxy-headers
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat > "/etc/systemd/system/${APP_NAME}-web.service" <<EOF
[Unit]
Description=The Republic Bulletin Next.js service
After=network.target ${APP_NAME}-api.service

[Service]
Type=simple
User=$DEPLOY_USER
WorkingDirectory=$FRONTEND_DIR
EnvironmentFile=$FRONTEND_ENV
ExecStart=/usr/bin/npm run start -- --hostname 127.0.0.1 --port $WEB_PORT
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

echo "Configuring Nginx..."
cat > "/etc/nginx/sites-available/$APP_NAME" <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN;
    client_max_body_size 10m;

    location /api/ {
        proxy_pass http://127.0.0.1:$API_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /media/ {
        proxy_pass http://127.0.0.1:$API_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location / {
        proxy_pass http://127.0.0.1:$WEB_PORT;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF
ln -sfn "/etc/nginx/sites-available/$APP_NAME" "/etc/nginx/sites-enabled/$APP_NAME"
rm -f /etc/nginx/sites-enabled/default
nginx -t

systemctl daemon-reload
systemctl enable --now "${APP_NAME}-api" "${APP_NAME}-web"
systemctl enable --now nginx
systemctl is-active --quiet "${APP_NAME}-api"
systemctl is-active --quiet "${APP_NAME}-web"
systemctl is-active --quiet nginx

echo "Checking local reverse-proxy health..."
curl --fail --silent --show-error --resolve "$DOMAIN:80:127.0.0.1" "http://$DOMAIN/api/health" >/dev/null
curl --fail --silent --show-error --resolve "$DOMAIN:80:127.0.0.1" "http://$DOMAIN/" >/dev/null

if [[ "$HTTP_ONLY" == false ]]; then
  echo "Requesting a TLS certificate for $DOMAIN..."
  if ! certbot --nginx --non-interactive --agree-tos --redirect --email "$EMAIL" -d "$DOMAIN"; then
    cat >&2 <<EOF

TLS certificate request failed. The local Nginx and application health checks passed,
so verify the public DNS and any proxy/CDN configuration before trying again:
  1. Point the domain's A record to this VM's public IPv4 address.
  2. Remove its AAAA record unless this VM has the matching public IPv6 address.
  3. If Cloudflare is enabled, temporarily set the DNS record to "DNS only" (grey cloud).
  4. Ensure ports 80 and 443 are open in the VM/cloud firewall.

Then retry only the certificate command:
  sudo certbot --nginx --redirect --email "$EMAIL" -d "$DOMAIN"

After the certificate succeeds, Cloudflare may be re-enabled. Set Cloudflare SSL/TLS mode
to "Full (strict)" rather than "Flexible".
EOF
    exit 1
  fi
fi

echo
echo "Deployment complete: $([[ "$HTTP_ONLY" == true ]] && echo "http" || echo "https")://$DOMAIN"
echo "Status: systemctl status ${APP_NAME}-api ${APP_NAME}-web nginx"
echo "Logs:   journalctl -u ${APP_NAME}-api -u ${APP_NAME}-web -f"
