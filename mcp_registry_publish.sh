#!/bin/bash
# Lists the site's MCP connector (https://jobseveryhour.com/mcp) in the official MCP Registry under com.jobseveryhour/jobs, from
# where Glama, VS Code, GitHub and other clients pick it up.
#
# The registry checks the domain: it reads https://jobseveryhour.com/.well-known/mcp-registry-auth (written by build.py from
# mcp_registry_auth.txt, the public half of an Ed25519 key) and accepts a login signed with the private half, which stays on the
# owner's Mac in ~/.config/jobseveryhour/ and never in the repository. Run it again with a higher VERSION after a change.
#
#     VERSION=1.0.1 ./mcp_registry_publish.sh
set -euo pipefail
KEY="${KEY:-$HOME/.config/jobseveryhour/mcp-registry-ed25519.pem}"
VERSION="${VERSION:-1.0.0}"
REG=https://registry.modelcontextprotocol.io
OPENSSL="${OPENSSL:-openssl}"

proof=$(curl -fsS -A 'mcp-registry/1.0' -H 'Accept: text/plain' https://jobseveryhour.com/.well-known/mcp-registry-auth)
want=$(cat "$(dirname "$0")/mcp_registry_auth.txt")
[ "$proof" = "$want" ] || { echo "the site does not serve the proof yet (got: $proof)"; exit 1; }

tmp=$(mktemp)
ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
printf '%s' "$ts" > "$tmp"
sig=$("$OPENSSL" pkeyutl -sign -inkey "$KEY" -rawin -in "$tmp" | xxd -p | tr -d '\n')
rm -f "$tmp"
token=$(curl -fsS -X POST "$REG/v0/auth/http" -H 'Content-Type: application/json' -H 'Accept: application/json' \
  -d "{\"domain\":\"jobseveryhour.com\",\"timestamp\":\"$ts\",\"signed_timestamp\":\"$sig\"}" | python3 -c 'import sys,json; print(json.load(sys.stdin)["registry_token"])')

curl -sS -X POST "$REG/v0/publish" -H "Authorization: Bearer $token" -H 'Content-Type: application/json' -w '\nHTTP %{http_code}\n' -d @- <<EOF
{
  "\$schema": "https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json",
  "name": "com.jobseveryhour/jobs",
  "description": "Search open jobs read every hour from employers' own career pages; closed jobs removed",
  "version": "$VERSION",
  "remotes": [{"type": "streamable-http", "url": "https://jobseveryhour.com/mcp"}]
}
EOF
