#!/bin/sh
# What the Commit Check image runs.
#
#   no arguments        check the merge or pull request this CI job runs for;
#                       a Bitbucket pipe starts the image this way
#   options (-m, ...)   run commit-check with them
#   anything else       run it as a command; GitLab CI starts its job shell
#                       this way, and `commit-check-ci --message=false` works too
set -e

if [ "$#" -eq 0 ]; then
    exec commit-check-ci
fi

case "$1" in
    -*) exec commit-check "$@" ;;
esac

exec "$@"
