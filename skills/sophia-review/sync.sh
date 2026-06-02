#!/usr/bin/env bash
# Sync the repo skill -> the active personal skill at ~/.claude/skills/sophia-review.
# Run after editing anything in the repo copy. Idempotent.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL="$HOME/.claude/skills/sophia-review"
mkdir -p "$LOCAL/helpers" "$LOCAL/templates"
cp "$REPO/sophia-review.md" "$LOCAL/SKILL.md"     # personal skills use SKILL.md
cp "$REPO/README.md"        "$LOCAL/README.md"
cp -R "$REPO/helpers/."   "$LOCAL/helpers/"
cp -R "$REPO/templates/." "$LOCAL/templates/"
rm -rf "$REPO/helpers/__pycache__" "$LOCAL/helpers/__pycache__"
echo "synced repo -> $LOCAL"
