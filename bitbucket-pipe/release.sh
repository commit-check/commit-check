#!/bin/bash
# Publishes the pipe to its Bitbucket repository: copies this directory's
# files there with the version filled in, commits, and tags the commit with
# the version, which is what `pipe: commit-check/commit-check:<version>`
# resolves. The release workflow runs it after pushing the image.
#
# Usage: bitbucket-pipe/release.sh <version> <requirements.txt>
# Environment: BITBUCKET_PIPE_TOKEN, a repository access token with the
# Repositories: Write scope. PIPE_REMOTE overrides the repository URL (tests).
set -euo pipefail

version=${1:?usage: $0 <version> <requirements.txt>}
requirements=${2:?usage: $0 <version> <requirements.txt>}
# Read before the script changes into the clone, so a relative path works.
requirements=$(realpath "$requirements")
here=$(cd "$(dirname "$0")" && pwd)
remote=${PIPE_REMOTE:-https://bitbucket.org/commit-check/commit-check.git}

if [[ ! $version =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "::error::version '$version' is not MAJOR.MINOR.PATCH"
  exit 1
fi

auth=()
if [[ -n ${BITBUCKET_PIPE_TOKEN:-} ]]; then
  basic=$(printf 'x-token-auth:%s' "$BITBUCKET_PIPE_TOKEN" | base64 -w0)
  echo "::add-mask::$basic"
  auth=(-c "http.extraHeader=Authorization: Basic $basic")
fi

clone=$(mktemp -d)
trap 'rm -rf "$clone"' EXIT
git "${auth[@]}" clone --quiet "$remote" "$clone"
cd "$clone"

# The clone has every tag. A release that is run again stops here.
if git rev-parse --quiet --verify "refs/tags/$version" >/dev/null; then
  echo "::notice::The pipe's repository already has tag $version; nothing to publish."
  exit 0
fi

# A new, empty repository has no branch yet.
git rev-parse --quiet --verify HEAD >/dev/null || git symbolic-ref HEAD refs/heads/main
git rm -r --quiet --ignore-unmatch .

cp "$here/Dockerfile" "$here/pipe.sh" "$here/pipe.yml" "$here/README.md" .
cp "$here/../LICENSE" .
cp "$requirements" requirements.txt
# Every `commit-check-pipe:X.Y.Z` (the image) and `commit-check/commit-check:X.Y.Z`
# (the pipe) names this release.
sed -E -i "s#(commit-check-pipe|commit-check/commit-check):[0-9]+\.[0-9]+\.[0-9]+#\1:$version#g" pipe.yml README.md
grep -q "commit-check-pipe:$version" pipe.yml
grep -q "commit-check/commit-check:$version" README.md

git add --all
git commit --quiet -m "Release $version" \
  -m "Published from https://github.com/commit-check/commit-check/releases/tag/v$version"
git tag "$version"
git "${auth[@]}" push --quiet origin HEAD "refs/tags/$version"
echo "Published pipe $version to $remote"
