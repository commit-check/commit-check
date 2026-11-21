#!/bin/sh
# The commit-check pin in README.md, read and written in one place, so the
# release-drafter job that writes it and the publish check that reads it
# cannot disagree about which lines count.
#
# Only `rev:` lines under `repo: https://github.com/commit-check/commit-check`
# count. A snippet for another hook repository, or a `rev:` in prose, is not
# this project's pin and is left alone.
#
#   readme-pin.sh read            print the pins found, comma-separated
#   readme-pin.sh write vX.Y.Z    set every pin to vX.Y.Z
#   readme-pin.sh check vX.Y.Z    fail unless every pin is vX.Y.Z
set -eu

readme=README.md

pins() {
  awk '
    /^[[:space:]]*-?[[:space:]]*repo:/ { own = ($0 ~ /github\.com\/commit-check\/commit-check([[:space:]]|$)/) }
    own && /^[[:space:]]*rev:[[:space:]]*v[0-9]+\.[0-9]+\.[0-9]+[[:space:]]*$/ {
      sub(/^[[:space:]]*rev:[[:space:]]*/, ""); sub(/[[:space:]]*$/, ""); print
    }' "$readme" | sort -u | paste -sd, -
}

tag_arg() {
  # A draft's tag comes from Release Drafter's template, so check its shape
  # here rather than write whatever arrives into the README.
  if ! printf '%s\n' "${1:-}" | grep -Eq '^v[0-9]+\.[0-9]+\.[0-9]+$'; then
    echo "::error::expected a tag like v1.2.3, got '${1:-}'" >&2
    exit 2
  fi
}

case "${1:-}" in
  read)
    pins
    ;;
  write)
    tag_arg "${2:-}"
    awk -v tag="$2" '
      /^[[:space:]]*-?[[:space:]]*repo:/ { own = ($0 ~ /github\.com\/commit-check\/commit-check([[:space:]]|$)/) }
      own && /^[[:space:]]*rev:[[:space:]]*v[0-9]+\.[0-9]+\.[0-9]+[[:space:]]*$/ {
        match($0, /^[[:space:]]*rev:[[:space:]]*/); $0 = substr($0, 1, RLENGTH) tag
      }
      { print }' "$readme" > "$readme.tmp"
    mv "$readme.tmp" "$readme"
    # Read it back with the same rule the publish check uses.
    found=$(pins)
    if [ "$found" != "$2" ]; then
      echo "::error file=$readme::wrote $2, but $readme now pins ${found:-nothing}" >&2
      exit 1
    fi
    ;;
  check)
    tag_arg "${2:-}"
    found=$(pins)
    if [ "$found" != "$2" ]; then
      echo "::error file=$readme::$readme pins commit-check ${found:-nowhere (no rev: under repo: https://github.com/commit-check/commit-check)}, but this release is $2, so nothing was built or published. To recover, delete this release and its tag, then merge the README pin pull request; Release Drafter drafts the release again from that commit."
      exit 1
    fi
    echo "$readme pins commit-check $2"
    ;;
  *)
    echo "usage: $0 read | write vX.Y.Z | check vX.Y.Z" >&2
    exit 2
    ;;
esac
