#!/usr/bin/env bash
set -Eeuo pipefail

REPO="${REPO:-swissairone/escrow-gigs-bot}"   # override: REPO=org/repo ./codex.sh ...

usage() {
  cat <<EOF
Codex helper for $REPO

USAGE
  ./codex.sh status              # show open PRs + mergeability
  ./codex.sh nudge               # ask Codex to rebase conflicted PRs & enable auto-merge
  ./codex.sh auto <PR...>        # queue auto-merge for PR(s)
  ./codex.sh watch <PR...>       # poll until clean; merge when possible
  ./codex.sh merge <PR>          # try squash-merge now
  ./codex.sh deploy              # rebuild app and tail logs
  ./codex.sh new "<title>"       # create an empty Codex issue (opens editor)
EOF
}

status() {
  gh pr list -R "$REPO" --state open --json number,title,mergeStateStatus,headRefName \
    -q '.[] | "#"+(.number|tostring)+"  "+.title+"  ["+.mergeStateStatus+"]  ("+.headRefName+")"'
}

nudge() {
  for pr in 3 4 6; do
    gh pr comment -R "$REPO" $pr -b "Please **rebase** onto main (after #8 i18n and #5 wallet), resolve conflicts, and enable **auto-merge**."
  done
  echo "Left rebase+auto-merge comments on PRs #3, #4, #6."
}

auto() {
  [ $# -gt 0 ] || { echo "Usage: ./codex.sh auto <PR...>"; exit 1; }
  for pr in "$@"; do
    echo "Queueing auto-merge for #$pr ..."
    gh pr merge -R "$REPO" "$pr" --squash --auto || {
      echo "Could not queue auto-merge yet for #$pr (probably conflicts). Nudge Codex: ./codex.sh nudge"
    }
  done
}

watch() {
  [ $# -gt 0 ] || { echo "Usage: ./codex.sh watch <PR...>"; exit 1; }
  local prs=("$@")
  echo "Watching PRs: ${prs[*]} (Ctrl-C to stop)"
  while true; do
    for pr in "${prs[@]}"; do
      state="$(gh pr view -R "$REPO" "$pr" --json mergeStateStatus -q .mergeStateStatus 2>/dev/null || echo UNKNOWN)"
      printf "#%-3s %-10s  " "$pr" "$state"
      if [[ "$state" == "CLEAN" || "$state" == "UNSTABLE" || "$state" == "BEHIND" || "$state" == "HAS_HOOKS" ]]; then
        gh pr merge -R "$REPO" "$pr" --squash --delete-branch >/dev/null 2>&1 && echo "merged ✔" || echo "not ready"
      else
        echo "waiting…"
      fi
    done
    sleep 30
  done
}

merge_now() {
  local pr="${1:-}"; [ -n "$pr" ] || { echo "Provide PR number"; exit 1; }
  gh pr merge -R "$REPO" "$pr" --squash --delete-branch
}

deploy() {
  docker compose up -d --build app
  docker compose logs -f app
}

new_issue() {
  local title="${1:-Codex task}"
  gh issue create -R "$REPO" -t "$title" -l codex
}

cmd="${1:-}"; shift || true
case "$cmd" in
  status) status ;;
  nudge)  nudge ;;
  auto)   auto "$@" ;;
  watch)  watch "$@" ;;
  merge)  merge_now "$@" ;;
  deploy) deploy ;;
  new)    new_issue "$@" ;;
  *)      usage ;;
esac
