#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/oilmine}"
SMOKE_EMAIL="${DEPLOY_SMOKE_EMAIL:-diegojavier20010@gmail.com}"
SESSION_COOKIE_NAME="${SESSION_COOKIE_NAME:-oilmine_session}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "[deploy] Missing required command: $1" >&2
    exit 1
  fi
}

sync_release() {
  echo "[deploy] Syncing release to ${APP_DIR}"
  sudo mkdir -p "${APP_DIR}"
  sudo chown "$(id -u):$(id -g)" "${APP_DIR}"

  if [[ "$(realpath "${ROOT_DIR}")" == "$(realpath "${APP_DIR}")" ]]; then
    echo "[deploy] Source and target are the same path; skipping rsync"
    return
  fi

  rsync -a --delete \
    --exclude ".git/" \
    --exclude ".github/" \
    --exclude ".env" \
    --exclude "data/" \
    --exclude ".runtime/" \
    --exclude "node_modules/" \
    --exclude "frontend/node_modules/" \
    --exclude "frontend/dist/" \
    --exclude "frontend/dist-local/" \
    --exclude "__pycache__/" \
    --exclude "*.pyc" \
    "${ROOT_DIR}/" "${APP_DIR}/"

  if [[ ! -f "${APP_DIR}/.env" ]]; then
    echo "[deploy] ${APP_DIR}/.env is required and was not found" >&2
    exit 1
  fi
}

ensure_postgres_env() {
  local env_file="${APP_DIR}/.env"
  if grep -q '^POSTGRES_PASSWORD=.' "${env_file}" 2>/dev/null; then
    return
  fi

  echo "[deploy] Setting POSTGRES_PASSWORD in ${env_file}"
  local password
  password="$(openssl rand -hex 24)"
  if grep -q '^POSTGRES_PASSWORD=' "${env_file}" 2>/dev/null; then
    sed -i "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=${password}/" "${env_file}"
  else
    printf '\nPOSTGRES_PASSWORD=%s\n' "${password}" >>"${env_file}"
  fi
}

configure_nginx() {
  if [[ ! -f "${APP_DIR}/deploy/nginx/oilmine.site.conf" ]]; then
    return
  fi
  echo "[deploy] Updating host Nginx config"
  local tmp_config
  tmp_config="$(mktemp)"

  if sudo test -f /etc/letsencrypt/live/oilmine.site/fullchain.pem \
    && sudo test -f /etc/letsencrypt/live/oilmine.site/privkey.pem; then
    cat >"${tmp_config}" <<'NGINX'
server {
  listen 80;
  server_name oilmine.site www.oilmine.site;
  return 301 https://$host$request_uri;
}

server {
  listen 443 ssl http2;
  server_name oilmine.site www.oilmine.site;

  ssl_certificate /etc/letsencrypt/live/oilmine.site/fullchain.pem;
  ssl_certificate_key /etc/letsencrypt/live/oilmine.site/privkey.pem;

  client_max_body_size 50m;

  location / {
    proxy_pass http://127.0.0.1:8088;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }
}
NGINX
  else
    cp "${APP_DIR}/deploy/nginx/oilmine.site.conf" "${tmp_config}"
  fi

  sudo install -m 0644 "${tmp_config}" /etc/nginx/sites-available/oilmine.site.conf
  rm -f "${tmp_config}"
  sudo ln -sf \
    /etc/nginx/sites-available/oilmine.site.conf \
    /etc/nginx/sites-enabled/oilmine.site.conf
  sudo rm -f /etc/nginx/sites-enabled/default
  sudo nginx -t
  sudo systemctl reload nginx
}

compose_up() {
  echo "[deploy] Building and starting Docker services"
  cd "${APP_DIR}"
  sudo docker compose build
  sudo docker compose up -d
  sudo docker compose ps
}

wait_for_http() {
  local url="$1"
  local name="$2"
  local attempts=30

  for _ in $(seq 1 "${attempts}"); do
    if curl -fsS --max-time 5 "${url}" >/dev/null; then
      echo "[deploy] ${name} is ready"
      return
    fi
    sleep 2
  done

  echo "[deploy] ${name} did not become ready: ${url}" >&2
  exit 1
}

make_smoke_token() {
  cd "${APP_DIR}"
  sudo docker compose exec -T api python - "${SMOKE_EMAIL}" <<'PY'
import sys

from src.infrastructure.auth_db import get_auth_db
from src.infrastructure.jwt_session import create_access_token
from src.infrastructure.membership_db import get_membership_db

email = sys.argv[1].lower().strip()
db = get_auth_db()
user = None
for org in db.list_orgs():
    for candidate in db.list_users_in_org(org.id):
        if candidate.email == email:
            user = candidate
            break
    if user is not None:
        break

if user is None:
    org = db.get_org_by_tenant("veyon") or db.create_org("veyon", "Veyon")
    user = db.create_user(f"deploy-check-{email}", email, org.id, "ADMIN")
else:
    org = db.get_org_by_id(user.org_id)
    if user.role != "ADMIN":
        db.update_user_role(user.id, user.org_id, "ADMIN")
        user = db.get_user_by_id(user.id)

get_membership_db().upsert(
    org_id=user.org_id,
    email=email,
    role="ADMIN",
    user_id=user.id,
    status="ACTIVE",
)

print(
    create_access_token(
        user_id=user.id,
        org_id=user.org_id,
        tenant_key=org.tenant_key,
        email=email,
        role=user.role,
        google_sub=user.google_sub,
    )
)
PY
}

smoke_tests() {
  echo "[deploy] Running smoke tests"
  wait_for_http "http://127.0.0.1:8088/api/health" "API"
  wait_for_http "http://127.0.0.1:8088/atlas-api/health" "Atlas"
  curl -fsSI --max-time 5 "http://127.0.0.1:8088/" >/dev/null

  local token
  token="$(make_smoke_token)"

  curl -fsS --max-time 10 \
    -H "Cookie: ${SESSION_COOKIE_NAME}=${token}" \
    "http://127.0.0.1:8088/api/me" >/dev/null
  curl -fsS --max-time 10 \
    -H "Cookie: ${SESSION_COOKIE_NAME}=${token}" \
    "http://127.0.0.1:8088/api/org/dataset/status" >/tmp/oilmine_dataset_status.json
  curl -fsS --max-time 20 \
    -H "Cookie: ${SESSION_COOKIE_NAME}=${token}" \
    "http://127.0.0.1:8088/api/org/dataset/download" >/tmp/oilmine_dataset_download.xlsx

  cd "${APP_DIR}"
  sudo docker compose exec -T atlas /opt/atlas-python/bin/python - <<'PY'
import matplotlib
import pandas

print("atlas-python-ok")
PY

  echo "[deploy] Smoke tests passed for ${SMOKE_EMAIL}"
}

main() {
  require_command rsync
  require_command curl
  require_command sudo
  require_command docker
  require_command openssl

  sync_release
  ensure_postgres_env
  configure_nginx
  compose_up
  smoke_tests
}

main "$@"
