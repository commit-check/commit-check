#!/bin/sh
# Start a built Commit Check image the three ways it gets started, on
# repositories shaped like a Bitbucket step's and a GitLab Runner's checkout.
#
#   python -m pip wheel --no-deps -w dist . && docker build -t commit-check .
#   sh docker/test.sh commit-check
set -eu

image="${1:?usage: sh docker/test.sh IMAGE}"
work="$(mktemp -d)"
# The container runs as root and leaves a ref behind that this user cannot
# always remove.
trap 'rm -rf "$work" 2>/dev/null || true' EXIT

as_dev() { git -c user.name="Dev One" -c user.email=dev@example.com -c commit.gpgsign=false "$@"; }

# expect CODE TEXT COMMAND...: the command exits with CODE and prints TEXT.
expect() {
    code="$1"
    text="$2"
    shift 2
    set +e
    output="$("$@" 2>&1)"
    got="$?"
    set -e
    printf '%s\n' "$output"
    if [ "$got" -ne "$code" ]; then
        echo "FAILED: expected exit $code, got $got"
        exit 1
    fi
    case "$output" in
        *"$text"*) ;;
        *) echo "FAILED: expected the output to contain: $text"; exit 1 ;;
    esac
}

# The repository on the server: main, and a branch whose first commit has a
# message the default rules reject.
server="$work/project.git"
mkdir "$server"
as_dev -C "$server" init --quiet --initial-branch=main
as_dev -C "$server" commit --quiet --allow-empty -m "feat: start the project"
base="$(git -C "$server" rev-parse HEAD)"
as_dev -C "$server" checkout --quiet -b feature/login
as_dev -C "$server" commit --quiet --allow-empty -m "added the login form"
as_dev -C "$server" commit --quiet --allow-empty -m "fix: trim the user name"
head="$(git -C "$server" rev-parse HEAD)"
as_dev -C "$server" checkout --quiet main

echo "== Options go to commit-check"
expect 0 "commit-check " docker run --rm "$image" --version

echo "== No arguments: a Bitbucket pipe"
as_dev clone --quiet --branch feature/login "$server" "$work/bitbucket"
expect 1 "1 of 3 failed." docker run --rm \
    --volume "$work/bitbucket:/opt/atlassian/pipelines/agent/build" \
    --workdir /opt/atlassian/pipelines/agent/build \
    --env BITBUCKET_PR_ID=12 \
    --env BITBUCKET_BRANCH=feature/login \
    --env BITBUCKET_PR_DESTINATION_BRANCH=main \
    --env "BITBUCKET_PR_DESTINATION_COMMIT=$base" \
    --env "BITBUCKET_COMMIT=$head" \
    "$image"

echo "== A command: the shell GitLab CI starts for its job"
mkdir "$work/gitlab"
as_dev -C "$work/gitlab" init --quiet
as_dev -C "$work/gitlab" remote add origin "$server"
as_dev -C "$work/gitlab" fetch --quiet origin "+$head:refs/pipelines/1"
as_dev -C "$work/gitlab" checkout --quiet --detach "$head"
gitlab() {
    script="$1"
    docker run --rm \
        --volume "$work:$work" \
        --workdir "$work/gitlab" \
        --env CI_MERGE_REQUEST_IID=7 \
        --env CI_MERGE_REQUEST_TARGET_BRANCH_NAME=main \
        --env CI_MERGE_REQUEST_SOURCE_BRANCH_NAME=feature/login \
        --env "CI_MERGE_REQUEST_DIFF_BASE_SHA=$base" \
        --env "CI_COMMIT_SHA=$head" \
        --env CI_PROJECT_ID=1 \
        --env CI_MERGE_REQUEST_PROJECT_ID=1 \
        "$image" sh -c "$script"
}
expect 1 "1 of 3 failed." gitlab "commit-check-ci --message=true --branch=true"
expect 0 "All 1 passed." gitlab "commit-check-ci --message=false --branch=true"

echo "The image works."
