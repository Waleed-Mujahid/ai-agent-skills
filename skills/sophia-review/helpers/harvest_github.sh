#!/usr/bin/env zsh
# harvest_github.sh — Fetch GitHub PRs, reviews, comments for a user
# Usage: ./harvest_github.sh <github_username> <date_from> <orgs_csv> <output_dir>
#
# Requires: gh CLI authenticated

set -e

GH_USER="${1:?Usage: $0 <username> <date_from> <orgs_csv> <output_dir>}"
DATE_FROM="${2:?date_from required (YYYY-MM-DD)}"
ORGS_CSV="${3:-edly-io,openedx,overhangio}"
OUTDIR="${4:-.}"

mkdir -p "$OUTDIR"

# ── Agent A: Authored PRs per org ────────────────────────────────────────────
echo "# GitHub PRs — authored by $GH_USER since $DATE_FROM" > "$OUTDIR/a_github_edly_prs.md"
echo "" >> "$OUTDIR/a_github_edly_prs.md"
echo "| date | repo | #PR | title | state | impact | link |" >> "$OUTDIR/a_github_edly_prs.md"
echo "|------|------|-----|-------|-------|--------|------|" >> "$OUTDIR/a_github_edly_prs.md"

IFS=',' read -rA ORGS <<< "$ORGS_CSV"
for org in "${ORGS[@]}"; do
  org=$(echo "$org" | tr -d ' ')
  echo "Fetching PRs for org: $org ..." >&2
  gh search prs "author:$GH_USER" --owner "$org" --created ">$DATE_FROM" \
    --json url,title,createdAt,repository,state,number \
    --limit 200 2>/dev/null \
  | python3 -c "
import json, sys
prs = json.load(sys.stdin)
for p in prs:
    date = p['createdAt'][:10]
    repo = p['repository']['name']
    num = p['number']
    title = p['title'][:60]
    state = p['state']
    link = p['url']
    print(f'| {date} | {repo} | #{num} | {title} | {state} | | [link]({link}) |')
" >> "$OUTDIR/a_github_edly_prs.md"
done

echo "Wrote $OUTDIR/a_github_edly_prs.md" >&2

# ── Agent B: Upstream PRs (not in specified orgs) ────────────────────────────
echo "# GitHub PRs — upstream contributions (non-org) since $DATE_FROM" > "$OUTDIR/b_github_upstream_prs.md"
echo "" >> "$OUTDIR/b_github_upstream_prs.md"
echo "| date | repo | #PR | title | state | link |" >> "$OUTDIR/b_github_upstream_prs.md"
echo "|------|------|-----|-------|-------|------|" >> "$OUTDIR/b_github_upstream_prs.md"

EDLY_ORGS_PYTHON="['$(echo $ORGS_CSV | sed "s/,/','/g")']"

gh search prs "author:$GH_USER" --created ">$DATE_FROM" \
  --json url,title,createdAt,repository,state,number \
  --limit 200 2>/dev/null \
| python3 -c "
import json, sys
exclude_orgs = set(o.strip() for o in '$ORGS_CSV'.split(','))
prs = json.load(sys.stdin)
for p in prs:
    owner = p['repository']['owner']['login'] if 'owner' in p['repository'] else p['repository']['nameWithOwner'].split('/')[0]
    if owner in exclude_orgs:
        continue
    date = p['createdAt'][:10]
    repo = p['repository']['nameWithOwner']
    num = p['number']
    title = p['title'][:60]
    state = p['state']
    link = p['url']
    print(f'| {date} | {repo} | #{num} | {title} | {state} | [link]({link}) |')
" >> "$OUTDIR/b_github_upstream_prs.md"

echo "Wrote $OUTDIR/b_github_upstream_prs.md" >&2

# ── Agent C: Reviews & Comments ───────────────────────────────────────────────
echo "# GitHub Reviews & Comments — $GH_USER since $DATE_FROM" > "$OUTDIR/c_github_reviews.md"
echo "" >> "$OUTDIR/c_github_reviews.md"
echo "| date | repo | PR_title | role | link |" >> "$OUTDIR/c_github_reviews.md"
echo "|------|------|----------|------|------|" >> "$OUTDIR/c_github_reviews.md"

gh search prs "reviewed-by:$GH_USER" --created ">$DATE_FROM" \
  --json url,title,createdAt,repository,number \
  --limit 100 2>/dev/null \
| python3 -c "
import json, sys
prs = json.load(sys.stdin)
for p in prs:
    date = p['createdAt'][:10]
    repo = p['repository']['nameWithOwner']
    title = p['title'][:60]
    link = p['url']
    print(f'| {date} | {repo} | {title} | reviewer | [link]({link}) |')
" >> "$OUTDIR/c_github_reviews.md"

# Also search for PR comments
gh api "search/issues?q=commenter:$GH_USER+type:pr+created:>$DATE_FROM&per_page=100" \
  --jq '.items[] | "| \(.created_at[:10]) | \(.repository_url | split("/")[-2:] | join("/")) | \(.title[:60]) | commenter | [link](\(.html_url)) |"' \
  2>/dev/null >> "$OUTDIR/c_github_reviews.md" || true

echo "Wrote $OUTDIR/c_github_reviews.md" >&2
