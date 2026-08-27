#!/usr/bin/env bash
# Local-testing helper for validation-ui.
#
# Lets you run this app against your LOCAL checkouts of the other repos it
# depends on, instead of whatever is currently pushed to GitHub -- so you can
# check that everything works before pushing.
#
# Two independent mechanisms are used, because the dependencies work
# differently:
#
#   - vetting-adapter and nomenclature-adapter are plain Python packages.
#     `on` editable-installs them from their local checkouts directly into
#     this repo's .venv, so even UNCOMMITTED edits there take effect
#     immediately.
#
#   - transience-nomenclature-definitions / iamcompact-nomenclature-definitions
#     / common-definitions are not Python packages: nomenclature_adapter
#     resolves them by `git clone`-ing the URL in
#     nomenclature-adapter/profiles/<profile>.yaml into a cache directory
#     (normally under ~/Library/Caches or $NOMENCLATURE_PROFILE_CACHE) on
#     first use, then `git fetch`-ing that same clone on every later call.
#     `on` pre-seeds a *separate* cache directory (.local-dev-cache/, used
#     only by `run` below, never your real cache) with clones whose remote
#     points at your local checkout instead of GitHub. Because this goes
#     through a real `git fetch`, only your LOCALLY COMMITTED changes are
#     picked up (working-tree edits are not) -- commit locally before
#     testing, no push required.
#
# Usage:
#   scripts/local_dev.sh on       # switch to local sources (safe to re-run)
#   scripts/local_dev.sh run      # streamlit run ui/main.py, using local-dev cache
#   scripts/local_dev.sh off      # restore the git-pinned versions (uv sync)
#   scripts/local_dev.sh clean    # delete .local-dev-cache/ entirely
#   scripts/local_dev.sh status   # show what's currently active
#
# Typical flow: commit your changes locally in the sibling repos, then:
#   scripts/local_dev.sh on
#   scripts/local_dev.sh run
# ... check the app in your browser, Ctrl-C to stop, iterate as needed ...
#   scripts/local_dev.sh off

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SIBLINGS_ROOT="$(cd "$REPO_ROOT/.." && pwd)"
CACHE_DIR="$REPO_ROOT/.local-dev-cache"
NOM_ADAPTER_DIR="$SIBLINGS_ROOT/nomenclature-adapter"

# repo name (as used as a key under `repositories:` in a profiles/*.yaml
# manifest) -> name of its local sibling checkout directory next to
# validation-ui. Extend this if you add more definitions repos/profiles.
#
# NB! common-definitions is deliberately NOT included here: its manifest
# entries pin an exact upstream commit SHA (not a branch), and a routine
# local clone of it won't necessarily contain that specific historical
# commit (older commits can become unreachable after upstream rewrites
# history, and a shallow/partial clone won't have it either) -- `git
# checkout <sha>` then fails. It's also not a repo this workflow is meant to
# let you test local edits to. Add it back below (and ensure your local
# checkout actually contains the pinned SHA) if you need that specifically.
REPO_NAME_TO_DIR=(
  "transience-defs:transience-nomenclature-definitions"
  "iamcompact-nomenclature-definitions:iamcompact-nomenclature-definitions"
)

log() { echo "==> $*"; }

require_repo_root() {
  if [ ! -f "$REPO_ROOT/pyproject.toml" ]; then
    echo "error: could not find validation-ui's pyproject.toml at $REPO_ROOT" >&2
    exit 1
  fi
}

do_on() {
  require_repo_root
  log "Editable-installing local vetting-adapter and nomenclature-adapter..."
  local py_dirs=()
  for name in vetting-adapter nomenclature-adapter; do
    if [ -d "$SIBLINGS_ROOT/$name" ]; then
      py_dirs+=("-e" "$SIBLINGS_ROOT/$name")
    else
      echo "  - skipping $name: no local checkout at $SIBLINGS_ROOT/$name"
    fi
  done
  if [ "${#py_dirs[@]}" -gt 0 ]; then
    (cd "$REPO_ROOT" && uv pip install "${py_dirs[@]}" --no-deps)
  fi

  log "Preparing local-source cache for definitions repositories..."
  mkdir -p "$CACHE_DIR/definition_repos"
  local profile_file profile
  for profile_file in "$NOM_ADAPTER_DIR"/profiles/*.yaml; do
    [ -f "$profile_file" ] || continue
    profile="$(basename "$profile_file" .yaml)"
    local pair repo_name dir_name local_path target
    for pair in "${REPO_NAME_TO_DIR[@]}"; do
      repo_name="${pair%%:*}"
      dir_name="${pair##*:}"
      # Only act on repos this profile's manifest actually references.
      grep -qE "^  ${repo_name}:" "$profile_file" || continue
      local_path="$SIBLINGS_ROOT/$dir_name"
      if [ ! -d "$local_path/.git" ]; then
        echo "  - skipping $profile/$repo_name: no local checkout at $local_path"
        continue
      fi
      target="$CACHE_DIR/definition_repos/$profile/$repo_name"
      if [ -d "$target/.git" ]; then
        git -C "$target" remote set-url origin "$local_path"
        git -C "$target" fetch --quiet origin
        echo "  - refreshed $profile/$repo_name from $local_path"
      else
        mkdir -p "$(dirname "$target")"
        git clone --quiet "$local_path" "$target"
        echo "  - cloned $profile/$repo_name from $local_path"
      fi
    done
  done

  log "Done. Next: scripts/local_dev.sh run"
}

kill_stale_server() {
  # Python only imports a package once per process, and Streamlit's
  # file-watcher hot-reload only re-runs this app's own ui/*.py scripts --
  # it does NOT reimport vetting-adapter/nomenclature-adapter, so a server
  # left running from before a local edit (or before switching `on`/`off`)
  # keeps serving the OLD code indefinitely, no matter how many times `on`
  # refreshes the venv/cache on disk. Kill any prior instance of *this*
  # app (matched by both command line and working directory, so this never
  # touches an unrelated streamlit app you might have running elsewhere)
  # before starting a fresh one.
  local pids pid cwd comm
  pids="$(pgrep -f 'streamlit run ui/main\.py' 2>/dev/null || true)"
  [ -z "$pids" ] && return
  for pid in $pids; do
    # Belt and braces beyond the pgrep pattern match: also require the
    # process's own executable to actually be streamlit/python, and its cwd
    # to be this repo. Guards against matching an unrelated process (e.g. a
    # shell) whose command line merely *mentions* the search string, rather
    # than being the server itself.
    comm="$(ps -p "$pid" -o comm= 2>/dev/null || true)"
    case "$comm" in
      *[Ss]treamlit*|*[Pp]ython*) ;;
      *) continue ;;
    esac
    cwd="$(lsof -a -d cwd -p "$pid" -Fn 2>/dev/null | sed -n 's/^n//p')"
    if [ "$cwd" = "$REPO_ROOT" ]; then
      log "Stopping previous local-dev server (pid $pid) so it picks up the latest code..."
      kill "$pid" 2>/dev/null || true
      for _ in 1 2 3 4 5 6 7 8 9 10; do
        kill -0 "$pid" 2>/dev/null || break
        sleep 0.5
      done
      kill -9 "$pid" 2>/dev/null || true
    fi
  done
}

do_run() {
  require_repo_root
  kill_stale_server
  # Always refresh -- both the editable installs and the definitions-repo
  # cache -- so `run` never silently serves stale code just because a cache
  # directory happens to exist from an earlier session. `on` is cheap and
  # idempotent (a local `git fetch` per repo plus a `uv pip install -e`).
  do_on
  log "Starting streamlit with NOMENCLATURE_PROFILE_CACHE=$CACHE_DIR"
  cd "$REPO_ROOT"
  NOMENCLATURE_PROFILE_CACHE="$CACHE_DIR" exec uv run streamlit run ui/main.py "$@"
}

do_off() {
  require_repo_root
  log "Restoring git-pinned vetting-adapter and nomenclature-adapter (uv sync)..."
  (cd "$REPO_ROOT" && uv sync)
  log "Done. (.local-dev-cache/ left in place -- run 'clean' to remove it.)"
}

do_clean() {
  log "Removing $CACHE_DIR"
  rm -rf "$CACHE_DIR"
}

do_status() {
  require_repo_root
  log "Python packages (via $REPO_ROOT/.venv):"
  for name in vetting-adapter nomenclature-adapter; do
    local pkg_underscore="${name//-/_}"
    local src
    src="$("$REPO_ROOT/.venv/bin/python" -c "
import importlib
try:
    m = importlib.import_module('$pkg_underscore')
    print(m.__file__)
except Exception as e:
    print(f'NOT INSTALLED ({e})')
" 2>/dev/null || echo "unknown")"
    if [[ "$src" == "$SIBLINGS_ROOT/$name/"* ]]; then
      echo "  - $name: LOCAL ($src)"
    else
      echo "  - $name: git-pinned ($src)"
    fi
  done
  log "Local-dev definitions cache:"
  if [ -d "$CACHE_DIR" ]; then
    local found=0
    while IFS= read -r -d '' git_dir; do
      found=1
      echo "  - ${git_dir%/.git}" | sed "s|$CACHE_DIR/definition_repos/||"
    done < <(find "$CACHE_DIR/definition_repos" -mindepth 3 -maxdepth 3 \
        -name .git -print0 2>/dev/null)
    if [ "$found" -eq 0 ]; then
      echo "  (none yet)"
    fi
  else
    echo "  (none -- run 'on' to set it up)"
  fi
}

case "${1:-}" in
  on) do_on ;;
  run) shift; do_run "$@" ;;
  off) do_off ;;
  clean) do_clean ;;
  status) do_status ;;
  *)
    echo "Usage: $0 {on|run|off|clean|status}" >&2
    exit 1
    ;;
esac
