#!/usr/bin/env bash
# sync-skills-to-hermes.sh
#
# Bridge: Sync skills from Hermes-Argus/skills/ (product catalog)
# to ~/.hermes/skills/ (Hermes runtime store).
#
# Each skill is a SKILL.md file at skills/<lane>/<domain>/<skill-name>/SKILL.md
# (ICM three-lane layout). This script copies each into
# ~/.hermes/skills/<skill-name>/SKILL.md for runtime loading. The runtime store
# is FLAT by skill name — the repo's lane/domain folders are organizational only
# and do not change the runtime layout.
#
# Usage:
#   ./sync-skills-to-hermes.sh           # sync all skills
#   ./sync-skills-to-hermes.sh dry-run   # preview without copying
#   ./sync-skills-to-hermes.sh list      # list what would be synced

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SKILLS_SRC="$REPO_ROOT/skills"
HERMES_SKILLS="$HOME/.hermes/skills"
DRY_RUN=false

# Derive the runtime skill name from a SKILL.md path: the skill is the SKILL.md's
# parent directory name (lane/domain depth-agnostic). Sanitize for the runtime store.
skill_name_from() {
  local src="$1"
  local dir; dir="$(basename "$(dirname "$src")")"
  echo "$dir" | tr '[:upper:]' '[:lower:]' | sed 's/ /-/g; s/(//g; s/)//g; s/--/-/g; s/-$//'
}

if [ "${1:-}" = "dry-run" ]; then
  DRY_RUN=true
elif [ "${1:-}" = "list" ]; then
  echo "Skills in $SKILLS_SRC (product catalog):"
  echo "---"
  find "$SKILLS_SRC" -name "SKILL.md" | sort | while read -r f; do
    rel="${f#$SKILLS_SRC/}"
    skilldir="$(dirname "$rel")"          # <lane>/<domain>/<skill-name>
    skill="$(basename "$skilldir")"       # <skill-name>
    category="$(dirname "$skilldir")"     # <lane>/<domain>
    echo "  [${category}] ${skill}"
  done
  exit 0
fi

echo "=== Hermes-Argus Skill Sync ==="
echo "Source (product catalog): $SKILLS_SRC"
echo "Target (Hermes runtime):  $HERMES_SKILLS"
echo ""

SYNCED=0
SKIPPED=0

find "$SKILLS_SRC" -name "SKILL.md" | sort | while read -r src; do
  sanitized="$(skill_name_from "$src")"
  target_dir="$HERMES_SKILLS/$sanitized"
  target_file="$target_dir/SKILL.md"

  # Skip if target is newer
  if [ -f "$target_file" ] && [ "$src" -ot "$target_file" ]; then
    echo "  [SKIP] $sanitized (target is current)"
    SKIPPED=$((SKIPPED + 1))
    continue
  fi

  if [ "$DRY_RUN" = true ]; then
    echo "  [DRY-RUN] Would copy: ${src#$SKILLS_SRC/} -> $target_file"
  else
    mkdir -p "$target_dir"
    cp "$src" "$target_file"
    echo "  [SYNC] $sanitized"
    SYNCED=$((SYNCED + 1))
  fi
done

if [ "$DRY_RUN" = false ]; then
  # Remove orphaned skill directories (skills in ~/.hermes/skills/ not in repo)
  echo ""
  echo "Checking for orphaned skill directories..."
  for dir in "$HERMES_SKILLS"/*/; do
    dname="$(basename "$dir")"
    # Skip bundled Hermes skill categories (they have subdirectories, not just SKILL.md)
    if [ -d "$dir" ] && [ ! -f "$dir/SKILL.md" ]; then
      continue  # bundled category, skip
    fi
    # Check if this skill exists in the repo
    repo_match=$(find "$SKILLS_SRC" -name "SKILL.md" | while read -r f; do
      if [ "$(skill_name_from "$f")" = "$dname" ]; then echo "$dname"; fi
    done)
    if [ -z "$repo_match" ]; then
      echo "  [ORPHAN] ~/.hermes/skills/$dname/ has no matching source in repo"
    fi
  done
fi

echo ""
echo "Done. Synced: $SYNCED, Skipped: $SKIPPED."
