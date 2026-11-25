#!/bin/sh
# The commit-check pin in README.md, read and written in one place, so the
# release-drafter job that writes it and the publish check that reads it
# cannot disagree about which lines count.
#
# Every `rev:` line under `repo: https://github.com/commit-check/commit-check`
# counts, until the next `repo:` line or the end of the code block, whatever
# its value: a pin this cannot read is reported as found, not skipped, so a
# README that is only partly updated never passes. The value is the whole
# YAML scalar: a quoted one ends at its closing quote, a bare one where a
# comment begins. Quotes and a trailing comment are kept. Anything else after
# the value fails `check`, and `write` refuses before it changes the file. A
# snippet for another hook repository is not this project's pin and is left
# alone.
#
#   readme-pin.sh read            print the pins found, comma-separated
#   readme-pin.sh write vX.Y.Z    set every pin to vX.Y.Z
#   readme-pin.sh check vX.Y.Z    fail unless every pin is vX.Y.Z
set -eu

readme=README.md

# mode=read prints each pin's value; mode=write prints the README with every
# pin set to tag.
scan() {
  awk -v mode="$1" -v tag="${2:-}" '
    /^[[:space:]]*```/ { own = 0 }
    /^[[:space:]]*-?[[:space:]]*repo:/ { own = ($0 ~ /github\.com\/commit-check\/commit-check([[:space:]]|$)/) }
    own && /^[[:space:]]*rev:/ {
      match($0, /^[[:space:]]*rev:[[:space:]]*/)
      head = substr($0, 1, RLENGTH); rest = substr($0, RLENGTH + 1)
      q = substr(rest, 1, 1)
      if (q == "\"" || q == "\047") {
        # A quoted value ends at its closing quote.
        shut = index(substr(rest, 2), q)
        if (shut) { value = substr(rest, 2, shut - 1); tail = substr(rest, shut + 2) }
        else { value = rest; tail = "unclosed" }
      } else {
        # A bare value ends where a comment begins: whitespace, then #.
        q = ""
        if (match(rest, /[[:space:]]+#/)) { value = substr(rest, 1, RSTART - 1); tail = substr(rest, RSTART) }
        else { value = rest; tail = "" }
        sub(/[[:space:]]+$/, "", value)
      }
      # After the value, only a comment may follow.
      if (tail ~ /^([[:space:]]+#.*|[[:space:]]*)$/) {
        if (mode == "read") print (value == "" ? "(empty)" : value)
        else $0 = head q tag q tail
      } else if (mode == "read") {
        print "(unreadable: " rest ")"
      } else {
        bad = bad " " NR
      }
    }
    mode == "write" { print }
    END { if (bad != "") { print "line" bad ": rev: is not a value this can rewrite" > "/dev/stderr"; exit 3 } }' "$readme"
}

pins() {
  scan read | sort -u | paste -sd, -
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
    if ! scan write "$2" > "$readme.tmp"; then
      rm -f "$readme.tmp"
      echo "::error file=$readme::$readme was left as it was" >&2
      exit 1
    fi
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
