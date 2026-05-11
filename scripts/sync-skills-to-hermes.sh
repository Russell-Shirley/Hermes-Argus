#!/usr/bin/env bash
# sync-skills-to-hermes.sh
# 
# Bridge: Sync skills from Hermes-Argus/skills/ (product catalog)
# to ~/.hermes/skills/ (Hermes runtime store).
#
# Each skill in Hermes-Argus/skills/ is a SKILL.md file in Hermes format
# (YAML frontmatter + markdown body). This script copies them into
# ~/.hermes/skills/<skill-name>/SKILL.md for runtime loading.
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

if [ "${1:-}" = "dry-run" ]; then
  DRY_RUN=true
elif [ "${1:-}" = "list" ]; then
  echo "Skills in $SKILLS_SRC (product catalog):"
  echo "---"
  find "$SKILLS_SRC" -name "*.md" ! -name "_context.md" | sort | while read -r f; do
    rel="${f#$SKILLS_SRC/}"
    category="$(dirname "$rel")"
    skill="$(basename "$rel" .md)"
    echo "  [${category%/}] ${skill}"
  done
  exit 0
fi

echo "=== Hermes-Argus Skill Sync ==="
echo "Source (product catalog): $SKILLS_SRC"
echo "Target (Hermes runtime):  $HERMES_SKILLS"
echo ""

SYNCED=0
SKIPPED=0

find "$SKILLS_SRC" -name "*.md" ! -name "_context.md" | sort | while read -r src; do
  rel="${src#$SKILLS_SRC/}"
  category="$(dirname "$rel")"
  # Remove category prefix for skill name — use filename only
  basename_file="$(basename "$src")"
  skill_name="${basename_file%.md}"
  
  # Sanitize: lowercase, replace spaces with hyphens, strip parens
  sanitized="$(echo "$skill_name" | tr '[:upper:]' '[:lower:]' | sed 's/ /-/g; s/(//g; s/)//g; s/--/-/g; s/-$//')"
  target_dir="$HERMES_SKILLS/$sanitized"
  target_file="$target_dir/SKILL.md"

  # Skip if target is newer
  if [ -f "$target_file" ] && [ "$src" -ot "$target_file" ]; then
    echo "  [SKIP] $sanitized (target is current)"
    SKIPPED=$((SKIPPED + 1))
    continue
  fi

  if [ "$DRY_RUN" = true ]; then
    echo "  [DRY-RUN] Would copy: $rel -> $target_file"
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
    repo_match=$(find "$SKILLS_SRC" -name "*.md" ! -name "_context.md" | while read -r f; do
      basename_file="$(basename "$f")"
      skill_name="${basename_file%.md}"
      sanitized="$(echo "$skill_name" | tr '[:upper:]' '[:lower:]' | sed 's/ /-/g; s/(//g; s/)//g; s/--/-/g; s/-$//')"
      if [ "$sanitized" = "$dname" ]; then echo "$dname"; fi
    done)
    if [ -z "$repo_match" ]; then
      echo "  [ORPHAN] ~/.hermes/skills/$dname/ has no matching source in repo"
    fi
  done
fi

echo ""
echo "Done. Synced: $SYNCED, Skipped: $SKIPPED."
