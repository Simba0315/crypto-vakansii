#!/usr/bin/env bash
# Lucene for the job search: OpenSearch on this server, for the page server only. It listens on 127.0.0.1:9200 (nothing outside the
# machine can reach it, and UFW closes the port too), so its security plugin is off. 1 GB heap; at most 2 GB of memory and one
# processor, so the shop keeps its share. Safe to run again. Run as root from this folder, after setup.sh.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)

if ! dpkg -s opensearch >/dev/null 2>&1; then
  # the release key and repository named in OpenSearch's own install guide; the Release file is checked against the key by apt
  for k in opensearch-release opensearch; do curl -fsSL "https://artifacts.opensearch.org/publickeys/$k.pgp" | gpg --dearmor --batch --yes -o "/usr/share/keyrings/$k.gpg"; done
  echo "deb [signed-by=/usr/share/keyrings/opensearch-release.gpg,/usr/share/keyrings/opensearch.gpg] https://artifacts.opensearch.org/releases/bundle/opensearch/3.x/apt stable main" > /etc/apt/sources.list.d/opensearch-3.x.list
  if ! apt-get update -o Dir::Etc::sourcelist=sources.list.d/opensearch-3.x.list -o Dir::Etc::sourceparts=- -o APT::Get::List-Cleanup=0; then
    rm -f /etc/apt/sources.list.d/opensearch-3.x.list; echo "the OpenSearch repository did not verify; nothing installed"; exit 1
  fi
  # the package asks for an admin password even though the security plugin is turned off below; it is kept for root only
  umask 077; pw="$(openssl rand -hex 16)Aa1!"; echo "$pw" > /root/hrn-setup/opensearch-admin-password; umask 022
  OPENSEARCH_INITIAL_ADMIN_PASSWORD="$pw" DEBIAN_FRONTEND=noninteractive apt-get install -y -q opensearch
fi

cat > /etc/opensearch/opensearch.yml <<'YML'
cluster.name: hrn
node.name: hrn-1
path.data: /var/lib/opensearch
path.logs: /var/log/opensearch
network.host: 127.0.0.1
http.port: 9200
discovery.type: single-node
plugins.security.disabled: true
action.auto_create_index: false
YML
install -d /etc/opensearch/jvm.options.d
printf -- '-Xms1g\n-Xmx1g\n' > /etc/opensearch/jvm.options.d/hrn-heap.options
echo 'vm.max_map_count=262144' > /etc/sysctl.d/90-hrn-opensearch.conf
sysctl -q -p /etc/sysctl.d/90-hrn-opensearch.conf
install -d /etc/systemd/system/opensearch.service.d
printf '[Service]\nMemoryMax=2G\nCPUQuota=100%%\nNice=5\n' > /etc/systemd/system/opensearch.service.d/hrn.conf

# loading the records into the index: whenever the hourly upload puts a new data/jobs.db in place, and once now
install -m 644 "$here/hrn-index.service" "$here/hrn-index.path" /etc/systemd/system/
install -d /etc/systemd/system/hrn-site.service.d
printf '[Unit]\nAfter=opensearch.service\n[Service]\nEnvironment=HRN_OPENSEARCH=http://127.0.0.1:9200\n' > /etc/systemd/system/hrn-site.service.d/opensearch.conf
systemctl daemon-reload
systemctl enable -q opensearch hrn-index.path
systemctl restart opensearch
for i in $(seq 1 60); do curl -fs http://127.0.0.1:9200/ >/dev/null && break; sleep 2; done
curl -fs http://127.0.0.1:9200/ | grep -E '"number"|"lucene_version"' || { echo "OpenSearch did not start"; exit 1; }
systemctl start hrn-index.path
[ -f /srv/hrn/app/data/jobs.db ] && systemctl start hrn-index.service
systemctl restart hrn-site
echo "OpenSearch is up; the search index is loaded and reloads after every upload"
