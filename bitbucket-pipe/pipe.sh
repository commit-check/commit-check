#!/bin/sh
# Runs commit-check-ci with the pipe's variables as its options: MESSAGE
# becomes --message, PR_TITLE becomes --pr-title, and so on. A variable that
# is not set leaves the check at commit-check-ci's default.
set -eu

set --
for pair in \
  MESSAGE:message \
  BRANCH:branch \
  AUTHOR_NAME:author-name \
  AUTHOR_EMAIL:author-email \
  FILES:files \
  PR_TITLE:pr-title \
  PR_BODY_AI_ATTRIBUTION:pr-body-ai-attribution
do
  name=${pair%%:*}
  option=${pair#*:}
  eval "value=\${$name-}"
  [ -n "$value" ] || continue
  # Case and surrounding spaces do not matter, as for commit-check-ci.
  case $(printf '%s' "$value" | tr -d '[:space:]' | tr '[:upper:]' '[:lower:]') in
    true) set -- "$@" "--$option=true" ;;
    false) set -- "$@" "--$option=false" ;;
    *)
      echo "Error: $name must be true or false, got '$value'" >&2
      exit 2
      ;;
  esac
done

# Pipelines starts the pipe in the clone already; this keeps a pipe started
# from another directory checking the right repository.
cd "${BITBUCKET_CLONE_DIR:-.}"
exec commit-check-ci "$@"
