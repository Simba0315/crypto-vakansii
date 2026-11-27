#!/usr/bin/env bash
# The site watch (watch.yml). One round checks what a visitor and Google need from the live site; the workflow runs a round every
# 10 minutes. Why: on 26 Nov 2026 job pages and search were down from 06:57 to 08:09 UTC and the owner found out first.
#
# A problem opens ONE issue labelled "site-watch" (GitHub emails the owner). While it lasts, the issue gets a comment only when
# the list of problems changes. When everything answers normally again the issue is closed with the time.
# It also restarts the Google indexing chain (indexing.yml) if no run of it is alive: no issue for that, a line in the log.
#
#   bash watch.sh            one round, issues and restarts for real (needs GH_TOKEN and REPO)
#   DRY_RUN=1 bash watch.sh  one round, prints what it would do and touches nothing on GitHub
set -u
SITE=${SITE:-https://jobseveryhour.com}
REPO=${REPO:-Simba0315/crypto-vakansii}
UA="JobsEveryHour-watch/1.0 (+https://github.com/$REPO)"   # its own name, so the site's logs can leave these requests out
NEW_JOBS_MAX_MIN=${NEW_JOBS_MAX_MIN:-180}   # live.py adds jobs every few minutes; three hours without one means it stopped
CERT_MIN_DAYS=${CERT_MIN_DAYS:-10}
STATE=${STATE:-/tmp/site-watch}              # last round's problems, to comment only on a change
mkdir -p "$STATE"
P="$STATE/problems"; : > "$P"
now() { date -u '+%H:%M UTC'; }

get() {   # url -> $CODE, the body in $STATE/body
  CODE=$(curl -s -o "$STATE/body" -w '%{http_code}' --max-time 20 -A "$UA" "$1" 2>/dev/null) || true
  [ -n "${CODE:-}" ] || CODE=000
}
page() {  # name url text-the-answer-must-contain: three tries 20 s apart, so a single slow answer or a 503 Busy is not a problem
  local try
  for try in 1 2 3; do
    get "$2"
    if [ "$CODE" = 200 ] && grep -q -- "$3" "$STATE/body"; then echo "  ok   $1"; return 0; fi
    [ "$try" -lt 3 ] && sleep 20
  done
  echo "  FAIL $1: HTTP $CODE"
  if [ "$CODE" = 200 ]; then
    echo "- **$1** ($2): answers, but the page is not right (\"$3\" missing), three times in a minute" >> "$P"
  else
    echo "- **$1** ($2): HTTP $CODE three times in a minute" >> "$P"
  fi
}

echo "Round at $(now)"
page "Home page" "$SITE/" "Jobs Every Hour"
page "Job list" "$SITE/jobs/" "Jobs Every Hour"
page "Search" "$SITE/api/search?q=nurse" '"total"'

get "$SITE/api/latest"
slug=$(grep -o '"slug":"[^"]*"' "$STATE/body" | head -1 | cut -d'"' -f4)
# found_at is when we found the job; "ts" is the employer's own date (often midnight), so it says nothing about our freshness
newest=$(grep -o '"found_at":"[^"]*"' "$STATE/body" | cut -d'"' -f4 | sort | tail -1 | python3 -c 'import sys,datetime; s=sys.stdin.read().strip(); print(int(datetime.datetime.fromisoformat(s.replace("Z","+00:00")).timestamp()) if s else 0)')
if [ -z "$slug" ]; then
  echo "  FAIL Newest jobs: HTTP $CODE, no job in the answer"
  echo "- **Newest jobs** ($SITE/api/latest): HTTP $CODE, no job in the answer" >> "$P"
else
  # ?watch= gets past nginx's 5-minute copy, so serve.py itself has to build the page
  page "A job page" "$SITE/job/$slug/?watch=$(date +%s)" "/job/$slug/"
  age=$(( ($(date +%s) - ${newest:-0}) / 60 ))
  if [ "$age" -gt "$NEW_JOBS_MAX_MIN" ]; then
    echo "  FAIL New jobs: the newest is $age minutes old"
    echo "- **New jobs**: the newest job on the site was found $age minutes ago; live.py normally adds jobs every few minutes" >> "$P"
  else
    echo "  ok   New jobs (newest $age min ago)"
  fi
fi

# The certificate visitors get (Cloudflare's or the server's): a renewal that failed shows up here 10 days ahead
end=$(echo | openssl s_client -servername "${SITE#https://}" -connect "${SITE#https://}:443" 2>/dev/null | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)
if [ -n "$end" ]; then
  left=$(( ( $(date -d "$end" +%s 2>/dev/null || date -j -f '%b %e %T %Y %Z' "$end" +%s) - $(date +%s) ) / 86400 ))
  if [ "$left" -lt "$CERT_MIN_DAYS" ]; then
    echo "  FAIL Certificate: $left days left"
    echo "- **HTTPS certificate**: expires in $left days ($end); renewal did not happen" >> "$P"
  else
    echo "  ok   Certificate ($left days left)"
  fi
fi

# The Google indexing chain: one run of indexing.yml should always be alive (it starts the next one itself)
alive=$(gh run list --repo "$REPO" --workflow indexing.yml -L 5 --json status -q '[.[]|select(.status!="completed")]|length' 2>/dev/null || echo "?")
if [ "$alive" = 0 ]; then
  if [ "${DRY_RUN:-}" ]; then echo "  would restart the Google indexing chain"
  else gh workflow run indexing.yml --repo "$REPO" --ref main && echo "  the Google indexing chain had stopped: started it again"; fi
else
  echo "  ok   Google indexing chain ($alive run alive)"
fi

# One issue per problem period
open=$(gh issue list --repo "$REPO" --label site-watch --state open --json number -q '.[0].number' 2>/dev/null || true)
run="${GITHUB_SERVER_URL:-https://github.com}/$REPO/actions/runs/${GITHUB_RUN_ID:-0}"
if [ -s "$P" ]; then
  if [ -z "$open" ]; then
    body=$(printf '@Simba0315 the site watch found a problem at %s:\n\n%s\n\nIt checks again every 10 minutes and closes this issue by itself when everything answers normally. Log: %s\n' "$(now)" "$(cat "$P")" "$run")
    if [ "${DRY_RUN:-}" ]; then echo "would open an issue:"; echo "$body"
    else
      gh label create site-watch --repo "$REPO" --color B60205 --description "The site watch found a problem" >/dev/null 2>&1 || true
      gh issue create --repo "$REPO" --label site-watch --title "Site problem, $(date -u '+%d %b %H:%M UTC')" --body "$body"
    fi
  elif ! cmp -s "$P" "$STATE/last"; then
    body=$(printf 'Still not right at %s:\n\n%s\n\nLog: %s\n' "$(now)" "$(cat "$P")" "$run")
    if [ "${DRY_RUN:-}" ]; then echo "would comment on #$open:"; echo "$body"
    else gh issue comment "$open" --repo "$REPO" --body "$body"; fi
  fi
  cp "$P" "$STATE/last"
else
  if [ -n "$open" ]; then
    if [ "${DRY_RUN:-}" ]; then echo "would close #$open"
    else gh issue close "$open" --repo "$REPO" --comment "Everything answers normally again at $(now)."; fi
  fi
  : > "$STATE/last"
fi
exit 0
