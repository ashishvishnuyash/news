#!/usr/bin/env bash
# One-VM deployment for The Republic Bulletin.
#
# Public traffic:
#   https://news.example.com/       -> Next.js on 127.0.0.1:3000
#   https://news.example.com/api/   -> FastAPI on 127.0.0.1:8000
#   https://news.example.com/media/ -> FastAPI on 127.0.0.1:8000
#
# Usage:
#   sudo bash deploy.sh --domain news.example.com --email admin@example.com
#   sudo bash deploy.sh --domain 203.0.113.10 --http-only

set -Eeuo pipefail

APP_NAME="republic-bulletin"
API_PORT="8000"
WEB_PORT="3000"
DOMAIN=""
EMAIL=""
HTTP_ONLY=false

log() {
  printf '\n[%s] %s\n' "$APP_NAME" "$*"
}

fail() {
  printf '\n[%s] ERROR: %s\n' "$APP_NAME" "$*" >&2
  exit 1
}

show_service_logs() {
  command -v journalctl >/dev/null 2>&1 || return 0
  journalctl -u "${APP_NAME}-api" -u "${APP_NAME}-web" -n 60 --no-pager 2>/dev/null || true
}

on_error() {
  local exit_code=$?
  local line_number="${1:-unknown}"
  printf '\n[%s] Deployment failed near line %s (exit %s).\n' "$APP_NAME" "$line_number" "$exit_code" >&2
  show_service_logs
  exit "$exit_code"
}
trap 'on_error $LINENO' ERR

usage() {
  cat <<'EOF'
Usage:
  sudo bash deploy.sh --domain <domain> --email <email> [--http-only]

Options:
  --domain <domain>  DNS name or public IP pointing to this VM.
  --email <email>    Let's Encrypt email. Required unless --http-only is used.
  --http-only        Skip TLS. Use for a private VM, an IP address, or initial testing.
  -h, --help         Show this help.

The script is safe to run again after a code update. Every run installs dependencies,
rebuilds Next.js, rewrites the systemd/Nginx configuration, and restarts both services.
Existing backend/.env database settings and application data are preserved.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --domain)
      [[ $# -ge 2 ]] || fail "--domain requires a value"
      DOMAIN="$2"
      shift 2
      ;;
    --email)
      [[ $# -ge 2 ]] || fail "--email requires a value"
      EMAIL="$2"
      shift 2
      ;;
    --http-only)
      HTTP_ONLY=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage >&2
      fail "Unknown option: $1"
      ;;
  esac
done

[[ "$EUID" -eq 0 ]] || fail "Run with sudo: sudo bash deploy.sh --domain <domain> --email <email>"
[[ -n "$DOMAIN" ]] || fail "--domain is required"
[[ "$DOMAIN" =~ ^[A-Za-z0-9.-]+$ ]] || fail "--domain must not include a protocol, port, slash, or path"
[[ "$DOMAIN" != .* && "$DOMAIN" != *. ]] || fail "--domain has an invalid leading or trailing dot"

if [[ "$HTTP_ONLY" == false ]]; then
  [[ -n "$EMAIL" ]] || fail "--email is required unless --http-only is used"
  [[ ! "$DOMAIN" =~ ^[0-9.]+$ ]] || fail "Let's Encrypt requires a DNS name; use --http-only for an IP address"
fi

command -v apt-get >/dev/null 2>&1 || fail "This deployer supports Ubuntu/Debian systems with apt-get"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
BACKEND_ENV="$BACKEND_DIR/.env"
FRONTEND_ENV="$FRONTEND_DIR/.env.local"

[[ -f "$BACKEND_DIR/app/main.py" ]] || fail "Backend not found at $BACKEND_DIR"
[[ -f "$FRONTEND_DIR/package.json" ]] || fail "Frontend not found at $FRONTEND_DIR"
[[ -f "$FRONTEND_DIR/package-lock.json" ]] || fail "frontend/package-lock.json is required for npm ci"

if [[ -n "${SUDO_USER:-}" && "$SUDO_USER" != "root" ]]; then
  DEPLOY_USER="$SUDO_USER"
else
  DEPLOY_USER="$(stat -c '%U' "$SCRIPT_DIR")"
fi
id "$DEPLOY_USER" >/dev/null 2>&1 || fail "Deployment user '$DEPLOY_USER' does not exist"
DEPLOY_GROUP="$(id -gn "$DEPLOY_USER")"

if [[ "$DEPLOY_USER" == "root" ]]; then
  printf '[%s] Warning: services will run as root because the repository is root-owned.\n' "$APP_NAME" >&2
  printf '[%s] Prefer cloning as a normal user and invoking this script with sudo.\n' "$APP_NAME" >&2
fi

PUBLIC_SCHEME="https"
COOKIE_SECURE="true"
if [[ "$HTTP_ONLY" == true ]]; then
  PUBLIC_SCHEME="http"
  COOKIE_SECURE="false"
fi
PUBLIC_ORIGIN="${PUBLIC_SCHEME}://${DOMAIN}"
INTERNAL_API_ORIGIN="http://127.0.0.1:${API_PORT}"

set_env() {
  local file="$1"
  local key="$2"
  local value="$3"
  touch "$file"
  if grep -qE "^${key}=" "$file"; then
    sed -i "s|^${key}=.*|${key}=${value}|" "$file"
  else
    printf '%s=%s\n' "$key" "$value" >> "$file"
  fi
}

set_default_env() {
  local file="$1"
  local key="$2"
  local value="$3"
  grep -qE "^${key}=" "$file" 2>/dev/null || printf '%s=%s\n' "$key" "$value" >> "$file"
}

run_as_deploy_user() {
  if [[ "$DEPLOY_USER" == "root" ]]; then
    "$@"
  else
    runuser -u "$DEPLOY_USER" -- "$@"
  fi
}

wait_for_url() {
  local label="$1"
  local url="$2"
  local attempt
  for attempt in $(seq 1 30); do
    if curl --fail --silent --show-error --max-time 5 "$url" >/dev/null 2>&1; then
      printf '[%s] %s is ready.\n' "$APP_NAME" "$label"
      return 0
    fi
    sleep 2
  done
  printf '[%s] %s did not become ready: %s\n' "$APP_NAME" "$label" "$url" >&2
  show_service_logs
  return 1
}

log "Installing Ubuntu/Debian packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl gnupg nginx openssl python3 python3-venv certbot python3-certbot-nginx

NODE_MAJOR="0"
if command -v node >/dev/null 2>&1; then
  NODE_MAJOR="$(node -p 'process.versions.node.split(".")[0]')"
fi
if [[ "$NODE_MAJOR" -lt 20 ]]; then
  log "Installing Node.js 20"
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y nodejs
fi

log "Preparing FastAPI backend"
python3 -m venv "$BACKEND_DIR/venv"
"$BACKEND_DIR/venv/bin/python" -m pip install --upgrade pip
"$BACKEND_DIR/venv/bin/pip" install -r "$BACKEND_DIR/requirements.txt"

if [[ ! -f "$BACKEND_ENV" ]]; then
  install -o "$DEPLOY_USER" -g "$DEPLOY_GROUP" -m 600 /dev/null "$BACKEND_ENV"
fi

SECRET_KEY="$(grep -E '^SECRET_KEY=' "$BACKEND_ENV" | cut -d= -f2- || true)"
if [[ -z "$SECRET_KEY" || "$SECRET_KEY" == supersecret* || "$SECRET_KEY" == replace-with* ]]; then
  SECRET_KEY="$(openssl rand -hex 32)"
fi

set_default_env "$BACKEND_ENV" "DATABASE_URL" "sqlite+aiosqlite:///./news.db"
set_default_env "$BACKEND_ENV" "ACCESS_TOKEN_EXPIRE_MINUTES" "1440"
set_env "$BACKEND_ENV" "ENVIRONMENT" "production"
set_env "$BACKEND_ENV" "SECRET_KEY" "$SECRET_KEY"
set_env "$BACKEND_ENV" "COOKIE_SECURE" "$COOKIE_SECURE"
set_env "$BACKEND_ENV" "COOKIE_DOMAIN" ""
set_env "$BACKEND_ENV" "CORS_ORIGINS" "$PUBLIC_ORIGIN"
set_env "$BACKEND_ENV" "CORS_ORIGIN_REGEX" '^$'
set_env "$BACKEND_ENV" "ALLOWED_HOSTS" "$DOMAIN,localhost,127.0.0.1"
chown "$DEPLOY_USER:$DEPLOY_GROUP" "$BACKEND_ENV"
chmod 600 "$BACKEND_ENV"

install -d -o "$DEPLOY_USER" -g "$DEPLOY_GROUP" -m 755 "$BACKEND_DIR/uploads"
if grep -qF 'DATABASE_URL=sqlite+aiosqlite:///./news.db' "$BACKEND_ENV"; then
  if [[ ! -e "$BACKEND_DIR/news.db" ]]; then
    run_as_deploy_user touch "$BACKEND_DIR/news.db"
  fi
  chown "$DEPLOY_USER:$DEPLOY_GROUP" "$BACKEND_DIR/news.db"
  chmod 600 "$BACKEND_DIR/news.db"
fi

log "Preparing and building Next.js frontend"
if [[ ! -f "$FRONTEND_ENV" ]]; then
  install -o "$DEPLOY_USER" -g "$DEPLOY_GROUP" -m 600 /dev/null "$FRONTEND_ENV"
fi
set_env "$FRONTEND_ENV" "NODE_ENV" "production"
set_env "$FRONTEND_ENV" "API_INTERNAL_URL" "$INTERNAL_API_ORIGIN"
set_env "$FRONTEND_ENV" "NEXT_PUBLIC_API_BASE_URL" "$PUBLIC_ORIGIN"
set_env "$FRONTEND_ENV" "NEXT_PUBLIC_SITE_BASE_URL" "$PUBLIC_ORIGIN"
chown "$DEPLOY_USER:$DEPLOY_GROUP" "$FRONTEND_ENV"
chmod 600 "$FRONTEND_ENV"

run_as_deploy_user npm ci --include=dev --prefix "$FRONTEND_DIR"
run_as_deploy_user npm run build --prefix "$FRONTEND_DIR"
if [[ -d "$FRONTEND_DIR/.next" ]]; then
  chown -R "$DEPLOY_USER:$DEPLOY_GROUP" "$FRONTEND_DIR/.next"
fi

NPM_BIN="$(command -v npm)"

log "Writing systemd services"
cat > "/etc/systemd/system/${APP_NAME}-api.service" <<EOF
[Unit]
Description=The Republic Bulletin FastAPI API
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=$DEPLOY_USER
Group=$DEPLOY_GROUP
WorkingDirectory=$BACKEND_DIR
EnvironmentFile=$BACKEND_ENV
Environment=PYTHONUNBUFFERED=1
ExecStart=$BACKEND_DIR/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port $API_PORT --proxy-headers --forwarded-allow-ips=127.0.0.1
Restart=on-failure
RestartSec=3
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
EOF

cat > "/etc/systemd/system/${APP_NAME}-web.service" <<EOF
[Unit]
Description=The Republic Bulletin Next.js frontend
Wants=network-online.target
Requires=${APP_NAME}-api.service
After=network-online.target ${APP_NAME}-api.service

[Service]
Type=simple
User=$DEPLOY_USER
Group=$DEPLOY_GROUP
WorkingDirectory=$FRONTEND_DIR
EnvironmentFile=$FRONTEND_ENV
Environment=NODE_ENV=production
ExecStart=$NPM_BIN run start -- --hostname 127.0.0.1 --port $WEB_PORT
Restart=on-failure
RestartSec=3
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
EOF

log "Writing Nginx reverse-proxy configuration"
cat > "/etc/nginx/sites-available/$APP_NAME" <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN;
    server_tokens off;
    client_max_body_size 10m;

    location = /api {
        proxy_pass http://127.0.0.1:$API_PORT;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Host \$host;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Connection "";
        proxy_connect_timeout 5s;
        proxy_read_timeout 120s;
    }

    location ^~ /api/ {
        proxy_pass http://127.0.0.1:$API_PORT;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Host \$host;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Connection "";
        proxy_connect_timeout 5s;
        proxy_read_timeout 120s;
    }

    location ^~ /media/ {
        proxy_pass http://127.0.0.1:$API_PORT;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Host \$host;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Connection "";
        proxy_connect_timeout 5s;
        proxy_read_timeout 120s;
        expires 7d;
        add_header Cache-Control "public, max-age=604800";
    }

    location / {
        proxy_pass http://127.0.0.1:$WEB_PORT;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Host \$host;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_buffering off;
        proxy_connect_timeout 5s;
        proxy_read_timeout 120s;
    }
}
EOF

ln -sfn "/etc/nginx/sites-available/$APP_NAME" "/etc/nginx/sites-enabled/$APP_NAME"
rm -f /etc/nginx/sites-enabled/default
nginx -t

log "Restarting API, frontend, and Nginx"
systemctl daemon-reload
systemctl enable "${APP_NAME}-api.service" "${APP_NAME}-web.service" nginx >/dev/null

# Explicit restart is essential on repeat deployments. `enable --now` alone leaves
# an already-running process on the old backend/frontend code.
systemctl restart "${APP_NAME}-api.service"
wait_for_url "FastAPI" "http://127.0.0.1:${API_PORT}/api/health"
wait_for_url "FastAPI database query" "http://127.0.0.1:${API_PORT}/api/articles?limit=1"

systemctl restart "${APP_NAME}-web.service"
wait_for_url "Next.js" "http://127.0.0.1:${WEB_PORT}/"

systemctl restart nginx
systemctl is-active --quiet "${APP_NAME}-api.service"
systemctl is-active --quiet "${APP_NAME}-web.service"
systemctl is-active --quiet nginx

log "Checking public routing through local Nginx"
curl --fail --silent --show-error --resolve "$DOMAIN:80:127.0.0.1" "http://$DOMAIN/api/health" >/dev/null
curl --fail --silent --show-error --resolve "$DOMAIN:80:127.0.0.1" "http://$DOMAIN/" >/dev/null

if [[ "$HTTP_ONLY" == false ]]; then
  log "Configuring Let's Encrypt TLS"
  if ! certbot --nginx --non-interactive --agree-tos --keep-until-expiring --redirect --email "$EMAIL" -d "$DOMAIN"; then
    cat >&2 <<EOF

TLS setup failed, but the API, frontend, and local Nginx health checks passed.

Check the following before rerunning this same deploy command:
  1. The $DOMAIN A record points to this VM's public IPv4 address.
  2. Remove an AAAA record unless this VM has that exact public IPv6 address.
  3. Open inbound TCP ports 80 and 443 in the VM/cloud firewall.
  4. If Cloudflare proxying is enabled, temporarily switch the DNS record to
     "DNS only" while Certbot obtains the certificate.

After deployment, Cloudflare can be re-enabled with SSL/TLS mode "Full (strict)".
EOF
    exit 1
  fi

  nginx -t
  systemctl reload nginx
  curl --fail --silent --show-error --resolve "$DOMAIN:443:127.0.0.1" "https://$DOMAIN/api/health" >/dev/null
  curl --fail --silent --show-error --resolve "$DOMAIN:443:127.0.0.1" "https://$DOMAIN/" >/dev/null
fi

log "Deployment complete"
printf 'Site:    %s\n' "$PUBLIC_ORIGIN"
printf 'API:     %s/api/health\n' "$PUBLIC_ORIGIN"
printf 'Status:  systemctl status %s-api %s-web nginx\n' "$APP_NAME" "$APP_NAME"
printf 'Logs:    journalctl -u %s-api -u %s-web -f\n' "$APP_NAME" "$APP_NAME"
printf 'Redeploy: sudo bash deploy.sh --domain %s%s\n' "$DOMAIN" "$([[ "$HTTP_ONLY" == true ]] && printf ' --http-only' || printf ' --email %s' "$EMAIL")"
