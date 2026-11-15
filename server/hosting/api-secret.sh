#!/usr/bin/env bash
# Writes one setting of the API into /srv/hrn/api.env without it showing on the screen, in the shell history or in the list of
# processes, then restarts the API. For the mailbox password (the owner types it; nobody else sees it):
#   sudo bash /srv/hrn/api/server/hosting/api-secret.sh SMTP_PASS
# Any other setting the same way (ADMIN_TOKEN, later the payment keys). Typing nothing changes nothing.
set -euo pipefail
name=${1:-}
[[ $name =~ ^[A-Z][A-Z0-9_]{1,40}$ ]] || { echo "say which setting, in capitals: api-secret.sh SMTP_PASS"; exit 1; }
[ "$(id -u)" = 0 ] || { echo "run it with sudo"; exit 1; }
file=${API_ENV:-/srv/hrn/api.env}
[ -f "$file" ] || { echo "$file is missing: run api-setup.sh first"; exit 1; }
read -rsp "Value for $name (nothing is shown while you type; Enter to finish): " value; echo
[ -n "$value" ] || { echo "nothing typed: nothing changed"; exit 1; }
case $value in *$'\n'*|*$'\r'*) echo "one line only: nothing changed"; exit 1 ;; esac
tmp=$(mktemp "$file.XXXXXX")
grep -v "^$name=" "$file" > "$tmp" || true
printf '%s="%s"\n' "$name" "$value" >> "$tmp"            # printf is part of bash: the value never appears as a process argument
unset value
chown root:hrnapi "$tmp"; chmod 640 "$tmp"; mv -f "$tmp" "$file"
systemctl restart hrn-api && echo "$name saved; hrn-api restarted"
