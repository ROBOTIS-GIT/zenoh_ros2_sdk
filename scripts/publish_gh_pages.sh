#!/usr/bin/env bash
set -euo pipefail

# Publish MkDocs output to the `gh-pages` branch (for GitHub Pages "Deploy from a branch").
#
# IMPORTANT:
# - This is a bash script. Run it with:
#     - `bash scripts/publish_gh_pages.sh`
#   or:
#     - `./scripts/publish_gh_pages.sh`
# - Do NOT run it with `python3`.
#
# Prereqs:
# - You have a git remote named `origin` with push access
# - You have mkdocs installed (recommended: `pip install -e ".[docs]"`)
#
# This script will:
# - build the site into ./site
# - create/update the `gh-pages` branch so its root contains the built HTML
# - force-push `gh-pages` to origin

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

if ! command -v mkdocs >/dev/null 2>&1; then
  echo "mkdocs not found. Install docs deps first: pip install -e \".[docs]\"" >&2
  exit 1
fi

echo "[1/4] Building docs..."
mkdocs build

if [ ! -d "site" ] || [ ! -f "site/index.html" ]; then
  echo "Expected mkdocs output in ./site (missing site/index.html)" >&2
  exit 1
fi

echo "[2/4] Preparing gh-pages worktree..."
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

git worktree add --force "${TMP_DIR}" gh-pages 2>/dev/null || {
  # branch may not exist yet
  git worktree add --force -b gh-pages "${TMP_DIR}"
}

echo "[3/4] Copying built site to gh-pages root..."
rm -rf "${TMP_DIR:?}/"*
cp -R site/. "${TMP_DIR}/"
touch "${TMP_DIR}/.nojekyll"

(
  cd "${TMP_DIR}"
  git add -A
  if git diff --cached --quiet; then
    echo "No changes to publish."
    exit 0
  fi
  git commit -m "docs: publish site"
)

echo "[4/4] Pushing gh-pages..."
git push origin gh-pages --force

echo "Done. In GitHub: Settings → Pages → Deploy from a branch → gh-pages / (root)"

