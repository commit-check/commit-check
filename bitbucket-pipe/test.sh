#!/bin/bash
# Runs the pipe's image the way Bitbucket Pipelines runs a pipe, against
# clones made the way a pull request pipeline makes them, and checks each
# exit code. Usage: bitbucket-pipe/test.sh <image>
set -euo pipefail

image=${1:?usage: $0 <image>}
work=$(mktemp -d)
# The container writes into the clones as root; leave what cannot be removed.
trap 'rm -rf "$work" 2>/dev/null || true' EXIT
failures=0

git_quiet() { git -c init.defaultBranch=main -c advice.detachedHead=false "$@" >/dev/null 2>&1; }

commit() {  # commit <repo> <message>
  local repo=$1 message=$2
  git -C "$repo" -c user.name="Ada Lovelace" -c user.email=ada@example.com \
    commit --quiet --allow-empty -m "$message"
}

# The repository on "bitbucket.org": main, and a feature branch off it.
origin=$work/origin
git_quiet init "$origin"
commit "$origin" "chore: start"
git -C "$origin" checkout --quiet -b feature/add-search
commit "$origin" "feat: add search"
commit "$origin" "fix: search empty input"
good=$(git -C "$origin" rev-parse HEAD)
git -C "$origin" checkout --quiet -b feature/bad-message
commit "$origin" "added stuff"
bad=$(git -C "$origin" rev-parse HEAD)
git -C "$origin" checkout --quiet main
commit "$origin" "docs: describe search"
destination=$(git -C "$origin" rev-parse HEAD)
git -C "$origin" checkout --quiet -b feature/rebased
commit "$origin" "feat: build on the docs"
rebased=$(git -C "$origin" rev-parse HEAD)
git -C "$origin" checkout --quiet main

# clone <branch> <source commit>: the checkout a pull request pipeline makes
# (shallow, destination merged in). It is then handed to another user, as the
# clone a pipe's container sees is not owned by the container's user.
clone() {
  local branch=$1 source=$2 root
  root=$(mktemp -d "$work/build-XXXX")
  build=$root/opt/atlassian/pipelines/agent/build
  mkdir -p "$build"
  (
    cd "$build"
    # As Pipelines does: everything in the clone is writable to every user.
    umask 000
    git_quiet init
    git_quiet remote add origin "file://$origin"
    git_quiet fetch origin "$source:refs/remotes/origin/$branch" --no-tags --depth 4
    git_quiet fetch origin "$destination" --no-tags --depth 2
    git_quiet checkout -B "$branch" "refs/remotes/origin/$branch"
    git_quiet -c user.name=bitbucket-pipelines -c user.email=commits-noreply@bitbucket.org \
      merge "${destination:0:12}" --no-edit
  )
  chmod 777 "$build"
  # Root (as on a developer's machine) hands it to another user; a runner's
  # own user already differs from the container's.
  if [[ $(id -u) == 0 ]]; then chown -R 1000:1000 "$root"; fi
  echo "$build"
}

# expect <name> <exit code> <branch> <source commit> [docker run options...]
expect() {
  local name=$1 want=$2 branch=$3 source=$4 build got
  shift 4
  build=$(clone "$branch" "$source")
  echo "::group::$name"
  set +e
  docker run --rm \
    --volume="$build:$build" --workdir="$build" \
    --env=BITBUCKET_CLONE_DIR="$build" \
    --env=BITBUCKET_BRANCH="$branch" \
    --env=BITBUCKET_COMMIT="$source" \
    --env=BITBUCKET_REPO_FULL_NAME=example/repo \
    "$@" "$image"
  got=$?
  set -e
  echo "::endgroup::"
  if [[ $got == "$want" ]]; then
    echo "ok: $name (exit $got)"
  else
    echo "FAILED: $name: exit $got, expected $want"
    failures=$((failures + 1))
  fi
}

pull_request=(
  --env=BITBUCKET_PR_ID=7
  --env=BITBUCKET_PR_DESTINATION_BRANCH=main
  --env=BITBUCKET_PR_DESTINATION_COMMIT="${destination:0:12}"
)

expect "good pull request passes" 0 feature/add-search "$good" "${pull_request[@]}"
expect "bad commit message fails" 1 feature/bad-message "$bad" "${pull_request[@]}"
expect "MESSAGE: 'false' leaves the bad message out" 0 feature/bad-message "$bad" \
  "${pull_request[@]}" --env=MESSAGE=false
expect "a value that is not true or false stops the pipe" 2 feature/add-search "$good" \
  "${pull_request[@]}" --env=AUTHOR_EMAIL=yes
expect "PR_TITLE without a token fails and says why" 1 feature/add-search "$good" \
  "${pull_request[@]}" --env=PR_TITLE=true
expect "AUTHOR_NAME and AUTHOR_EMAIL pass" 0 feature/add-search "$good" \
  "${pull_request[@]}" --env=AUTHOR_NAME=TRUE --env="AUTHOR_EMAIL= True "
# The rebase check writes the destination's ref into the clone first.
expect "the rebase check passes a rebased branch" 0 feature/rebased "$rebased" \
  "${pull_request[@]}" --env=CCHK_REQUIRE_REBASE_TARGET=main
expect "the rebase check fails a branch behind the destination" 1 feature/add-search "$good" \
  "${pull_request[@]}" --env=CCHK_REQUIRE_REBASE_TARGET=main
expect "a branch pipeline checks the last commit" 0 feature/add-search "$good"

if (( failures != 0 )); then
  echo "$failures case(s) failed"
  exit 1
fi
echo "All cases passed."
