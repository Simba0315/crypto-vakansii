#!/usr/bin/env bash
# One-time setup of Hiring Right Now on the Hostinger server, next to hypestkey. Run as root from this folder; running it again is safe.
#   DOMAIN=jobseveryhour.com DEPLOY_KEY="ssh-ed25519 AAAA... github-deploy" bash setup.sh
#   DEPLOY_KEY="..." bash setup.sh       (no domain yet: everything but nginx; run again with DOMAIN once it points here)
# Before: the domain's A record points at this server (certbot checks it). After: the GitHub workflow uploads the site every hour.
# It adds a user, a folder, a service and an nginx site. It does not touch hypestkey: not its files, its database, PHP or Redis.
set -euo pipefail
DOMAIN=${DOMAIN:-}      # empty: only the user, the folder and the service; nginx and the certificate wait for the domain
here=$(cd "$(dirname "$0")" && pwd)

# 1. The user hrn owns /srv/hrn and nothing else. The workflow logs in as hrn with its own key, and that key can only run rsync.
id hrn >/dev/null 2>&1 || useradd --system --create-home --home-dir /srv/hrn --shell /bin/bash hrn
install -d -o hrn -g hrn /srv/hrn/app /srv/hrn/app/site /srv/hrn/app/data
install -d -m 700 -o hrn -g hrn /srv/hrn/.ssh
if [ -n "${DEPLOY_KEY:-}" ]; then
  line="command=\"rrsync /srv/hrn/app\",no-agent-forwarding,no-port-forwarding,no-pty,no-X11-forwarding $DEPLOY_KEY"
  touch /srv/hrn/.ssh/authorized_keys
  grep -qxF "$line" /srv/hrn/.ssh/authorized_keys || echo "$line" >> /srv/hrn/.ssh/authorized_keys
  chown hrn:hrn /srv/hrn/.ssh/authorized_keys; chmod 600 /srv/hrn/.ssh/authorized_keys
fi
command -v rrsync >/dev/null || { [ -x /usr/share/doc/rsync/scripts/rrsync ] && ln -sf /usr/share/doc/rsync/scripts/rrsync /usr/local/bin/rrsync; } || apt-get install -y rsync
python3 -c 'import sys, sqlite3; assert sys.version_info >= (3, 12)' || { echo "needs Python 3.12 or newer"; exit 1; }

# 2. The program that builds job pages from records.
install -m 644 "$here/hrn-site.service" /etc/systemd/system/hrn-site.service
systemctl daemon-reload
systemctl enable hrn-site >/dev/null
[ -f /srv/hrn/app/serve.py ] && systemctl restart hrn-site || echo "hrn-site starts after the first upload (serve.py is not there yet)"

if [ -z "$DOMAIN" ]; then echo "no DOMAIN: the user, the folder and the service are ready; run again with DOMAIN=... for nginx and the certificate"; exit 0; fi

# 3. Behind Cloudflare every visitor arrives from a Cloudflare address and the real one is in CF-Connecting-IP; without this the
#    per-visitor limits in nginx-hrn.conf would count the whole of Cloudflare as one visitor. The ranges come from Cloudflare's lists.
install -d /etc/nginx/snippets
if v4=$(curl -fsS https://www.cloudflare.com/ips-v4) && v6=$(curl -fsS https://www.cloudflare.com/ips-v6); then
  { printf '%s\n%s\n' "$v4" "$v6" | sed '/^$/d; s/^/set_real_ip_from /; s/$/;/'; echo 'real_ip_header CF-Connecting-IP;'; } > /etc/nginx/snippets/hrn-cloudflare.conf
else
  : > /etc/nginx/snippets/hrn-cloudflare.conf      # the lists did not load: visitors are counted by the address nginx sees
fi

# 4. nginx: first the plain-http part, so certbot can prove the domain; then the full site with its certificate.
install -d /var/www/letsencrypt /var/cache/nginx/hrn
chown www-data:www-data /var/cache/nginx/hrn
if [ ! -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
  printf 'server { listen 80; listen [::]:80; server_name %s www.%s; location /.well-known/acme-challenge/ { root /var/www/letsencrypt; } location / { return 404; } }\n' "$DOMAIN" "$DOMAIN" > /etc/nginx/sites-available/hrn.conf
  ln -sf /etc/nginx/sites-available/hrn.conf /etc/nginx/sites-enabled/hrn.conf
  nginx -t && systemctl reload nginx
  certbot certonly --webroot -w /var/www/letsencrypt -d "$DOMAIN" -d "www.$DOMAIN" --non-interactive --agree-tos --register-unsafely-without-email
fi
sed "s/DOMAIN/$DOMAIN/g" "$here/nginx-hrn.conf" > /etc/nginx/sites-available/hrn.conf
ln -sf /etc/nginx/sites-available/hrn.conf /etc/nginx/sites-enabled/hrn.conf
nginx -t && systemctl reload nginx
echo "ready: https://$DOMAIN/ (the site appears after the first upload from GitHub)"
