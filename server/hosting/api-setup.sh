#!/usr/bin/env bash
# Installs or updates the Jobs Every Hour API on the Hostinger server, next to the page server (setup.sh did that part on 14 Nov).
# Run as root from a copy of the repository's server/ folder; running it again is safe: it updates the code and restarts.
#   bash server/hosting/api-setup.sh                 (DOMAIN=jobseveryhour.com unless given)
# What it does, in order (each step can be run again):
#   1. Node 22.13 or newer (node:sqlite without a flag): the official build from nodejs.org, its checksum checked, into /opt.
#   2. The user hrnapi, /srv/hrn/api (code, owned by root) and /srv/hrn/api/data (the database, owned by hrnapi, 700).
#   3. /srv/hrn/api.env, the settings, if it is missing: the site, the mail server, a random ADMIN_TOKEN. Never overwritten.
#      Secrets are added later with api-secret.sh, typed in by the owner (HOSTING.md).
#   4. hrn-api.service (the API on 127.0.0.1:8787) and hrn-alerts.timer (the hourly alert run). If the new code does not answer
#      /api/health within 20 seconds, the previous code is put back.
#   5. nginx: the API's addresses (nginx-hrn-api.conf) and the site's server block from nginx-hrn.conf. If nginx refuses the
#      result, both files are put back as they were and nothing is reloaded.
# Payments stay off: the settings file has no PAYMENTS_LIVE, and without it prod.mjs ignores any payment key.
# It does not touch hypestkey, the page server's files, or the job records.
set -euo pipefail
DOMAIN=${DOMAIN:-jobseveryhour.com}
here=$(cd "$(dirname "$0")" && pwd)
src=$(dirname "$here")                                  # the server/ folder this script came with
[ "$(id -u)" = 0 ] || { echo "run as root"; exit 1; }
[ -f "$src/prod.mjs" ] && [ -f "$src/src/worker.js" ] && [ -f "$src/schema.sql" ] || { echo "run it from the repository's server/hosting folder"; exit 1; }
backup=/root/hrn-api-setup; install -d -m 700 "$backup"

# 1. Node 22.13+
node_ok() { "$1" -e 'const [a, b] = process.versions.node.split(".").map(Number); process.exit(a > 22 || (a === 22 && b >= 13) ? 0 : 1)' 2>/dev/null; }
NODE=$(command -v node || true)
if [ -z "$NODE" ] || ! node_ok "$NODE"; then
  case $(uname -m) in x86_64) arch=x64 ;; aarch64) arch=arm64 ;; *) echo "no Node build for $(uname -m)"; exit 1 ;; esac
  base=https://nodejs.org/dist/latest-v22.x tmp=$(mktemp -d)
  curl -fsSL "$base/SHASUMS256.txt" -o "$tmp/SHASUMS256.txt"
  file=$(grep -oE "node-v22\.[0-9]+\.[0-9]+-linux-$arch\.tar\.xz" "$tmp/SHASUMS256.txt" | head -1)
  [ -n "$file" ] || { echo "no Node 22 build listed at $base"; exit 1; }
  curl -fsSL "$base/$file" -o "$tmp/$file"
  (cd "$tmp" && grep " $file\$" SHASUMS256.txt | sha256sum -c -)
  dir=/opt/${file%.tar.xz}
  rm -rf "$dir"; mkdir -p "$dir"; tar -xJf "$tmp/$file" -C "$dir" --strip-components=1
  ln -sf "$dir/bin/node" /usr/local/bin/node
  rm -rf "$tmp"
  NODE=/usr/local/bin/node
fi
node_ok "$NODE" || { echo "$NODE is not Node 22.13 or newer"; exit 1; }
[ -e /usr/local/bin/node ] || ln -s "$NODE" /usr/local/bin/node      # one path for the commands in HOSTING.md
echo "node: $NODE $("$NODE" -v)"

# 2. user, folders, code
id hrnapi >/dev/null 2>&1 || useradd --system --no-create-home --home-dir /srv/hrn/api --shell /usr/sbin/nologin hrnapi
[ -d /srv/hrn ] || { echo "/srv/hrn is missing: run setup.sh first"; exit 1; }
install -d -m 755 -o root -g root /srv/hrn/api
install -d -m 700 -o hrnapi -g hrnapi /srv/hrn/api/data
new=/srv/hrn/api/server.new
rm -rf "$new"; mkdir -p "$new"; cp -r "$src/." "$new/"
chown -R root:root "$new"; chmod -R u+rwX,go+rX,go-w "$new"
rm -rf /srv/hrn/api/server.old
[ -d /srv/hrn/api/server ] && mv /srv/hrn/api/server /srv/hrn/api/server.old
mv "$new" /srv/hrn/api/server

# 3. settings (kept if they exist; a missing ADMIN_TOKEN is added)
envf=/srv/hrn/api.env
if [ ! -f "$envf" ]; then
  (umask 027; cat > "$envf" <<EOF
# Jobs Every Hour API settings, read by hrn-api and hrn-alerts. Readable by root and the service user only.
# Add a secret without it showing anywhere:  sudo bash /srv/hrn/api/server/hosting/api-secret.sh NAME
# After editing by hand: systemctl restart hrn-api
SITE_URL=https://$DOMAIN
SMTP_HOST=smtp.beget.com
SMTP_PORT=465
SMTP_USER=support@$DOMAIN
MAIL_FROM="Jobs Every Hour <support@$DOMAIN>"
MAIL_DAILY_CAP=300
# Payments stay off until the owner adds PAYMENTS_LIVE=1 (and the payment keys). Without it any payment key here is ignored.
EOF
  )
fi
grep -q '^ADMIN_TOKEN=' "$envf" || printf 'ADMIN_TOKEN="%s"\n' "$(openssl rand -hex 32)" >> "$envf"
chown root:hrnapi "$envf"; chmod 640 "$envf"

# 4. services
for unit in hrn-api.service hrn-alerts.service; do sed "s#NODEBIN#$NODE#" "$here/$unit" > "/etc/systemd/system/$unit"; done
install -m 644 "$here/hrn-alerts.timer" /etc/systemd/system/hrn-alerts.timer
systemctl daemon-reload
systemctl enable hrn-api.service hrn-alerts.timer >/dev/null
systemctl restart hrn-api.service
healthy() { for _ in $(seq 1 20); do curl -fsS http://127.0.0.1:8787/api/health >/dev/null 2>&1 && return 0; sleep 1; done; return 1; }
if ! healthy; then
  journalctl -u hrn-api -n 30 --no-pager || true
  if [ -d /srv/hrn/api/server.old ]; then
    rm -rf /srv/hrn/api/server.bad; mv /srv/hrn/api/server /srv/hrn/api/server.bad; mv /srv/hrn/api/server.old /srv/hrn/api/server
    systemctl restart hrn-api.service; echo "the new API did not start: the previous code is back (the new one is in /srv/hrn/api/server.bad)"
  else
    systemctl stop hrn-api.service; echo "the API did not start (see the log above); nginx was not changed"
  fi
  exit 1
fi
systemctl start hrn-alerts.timer
echo "hrn-api answers on 127.0.0.1:8787; hrn-alerts.timer runs every hour"

# 5. nginx: the API's addresses and the site's server block, taken back together if nginx refuses them
snip=/etc/nginx/snippets/hrn-api.conf site=/etc/nginx/sites-available/hrn.conf
[ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ] || { echo "no certificate for $DOMAIN: run setup.sh with DOMAIN first; nginx was not changed"; exit 1; }
install -d /etc/nginx/snippets
rm -f "$backup/hrn-api.conf.before" "$backup/hrn.conf.before"
[ -f "$snip" ] && cp -f "$snip" "$backup/hrn-api.conf.before"
[ -f "$site" ] && cp -f "$site" "$backup/hrn.conf.before"
install -m 644 "$here/nginx-hrn-api.conf" "$snip"
sed "s/DOMAIN/$DOMAIN/g" "$here/nginx-hrn.conf" > "$site"
ln -sf "$site" /etc/nginx/sites-enabled/hrn.conf
if ! nginx -t; then
  # never leave a config nginx refuses: the next reload of hypestkey would fail too
  if [ -f "$backup/hrn-api.conf.before" ]; then cp -f "$backup/hrn-api.conf.before" "$snip"; else rm -f "$snip"; fi
  if [ -f "$backup/hrn.conf.before" ]; then cp -f "$backup/hrn.conf.before" "$site"; fi
  nginx -t || true
  echo "nginx refused the new configuration: both files are back as they were and nothing was reloaded"; exit 1
fi
systemctl reload nginx
sleep 1
if curl -fsS --resolve "$DOMAIN:443:127.0.0.1" "https://$DOMAIN/api/health" >/dev/null; then echo "https://$DOMAIN/api/health answers through nginx"; else echo "warning: /api/health does not answer through nginx yet"; fi
mail=$(grep -q '^SMTP_PASS=' "$envf" && echo on || echo "off: add the mailbox password with api-secret.sh SMTP_PASS (HOSTING.md)")
echo "ready. mail: $mail. The admin token is in $envf (sudo grep ^ADMIN_TOKEN= $envf)."
