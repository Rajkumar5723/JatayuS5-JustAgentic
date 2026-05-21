#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export FILTER_BRANCH_SQUELCH_WARNING=1

git filter-branch -f \
  --msg-filter "sed '/Co-authored-by: Cursor/d'" \
  --env-filter '
    if [ "$GIT_AUTHOR_NAME" = "Railway Agent" ]; then
      export GIT_AUTHOR_NAME="Rajkumar5723"
      export GIT_AUTHOR_EMAIL="g.p.rajkumar5@gmail.com"
    fi
  ' \
  875c451..HEAD

git log -5 --format='%h %an | %s%n%b---'
