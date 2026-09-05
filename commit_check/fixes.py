"""Deterministic corrections for failed checks.

A suggestion is only worth more than the rule's generic text when the fix is
unambiguous: a type written ``Fix`` where ``fix`` is allowed, a type misspelt
by a letter, a missing space after the colon, a ``WIP:`` marker to drop, a
sign-off trailer to add. Anything that needs a judgment — which type a bare
subject deserves, how to shorten a long one, how to phrase it imperatively —
is left to the human, and these functions return ``None`` so the caller keeps
the generic suggestion. Every function here is pure and free of git.
"""

from __future__ import annotations

import difflib
import re

# type, optional scope, optional bang, optional colon, the rest. Lenient on
# purpose: this is the shape of a subject that *tried* to be conventional.
_HEADER = re.compile(r"^\s*([A-Za-z]+)(\([^)]*\))?(!)?(\s*:\s*|\s+)(\S.*?)\s*$")
_CONVENTIONAL_PREFIX = re.compile(r"^(\w+(?:\([^)]*\))?!?:\s*)(.*)$")
_WIP = re.compile(r"^\s*(?:\[wip\]|wip:|wip\b)\s*[-:]?\s*", re.IGNORECASE)


def _transposed(a: str, b: str) -> bool:
    """Whether *a* is *b* with one pair of adjacent letters swapped (``feta``/``feat``)."""
    if len(a) != len(b) or a == b:
        return False
    diff = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
    return len(diff) == 2 and diff[1] == diff[0] + 1 and a[diff[0]] == b[diff[1]] and a[diff[1]] == b[diff[0]]


def _closest(word: str, allowed: list[str]) -> str | None:
    """The allowed word *word* is a near-miss of, or None.

    Case is forgiven outright; a swapped pair of letters or a one-letter slip
    is matched, tightly enough that ``feat`` never turns into ``test`` and
    ``text`` never turns into ``test`` either.
    """
    lowered = word.lower()
    if lowered in allowed:
        return lowered
    if len(lowered) < 3:
        return None
    for candidate in allowed:
        if _transposed(lowered, candidate):
            return candidate
    close = difflib.get_close_matches(lowered, allowed, n=1, cutoff=0.8)
    return close[0] if close else None


def fix_conventional_header(subject: str, allowed_types: list[str] | None) -> str | None:
    """A corrected Conventional Commits header, or None when it takes a guess.

    Fixes the type's case and small misspellings, a missing colon after a
    recognised type, and the spacing around the colon. Does not invent a
    type: a subject with no recognisable type is the author's to fix.
    """
    if not allowed_types:
        return None
    match = _HEADER.match(subject)
    if not match:
        return None
    raw_type, scope, bang, _sep, description = match.groups()
    fixed_type = _closest(raw_type, allowed_types)
    if fixed_type is None or not description:
        return None
    fixed = f"{fixed_type}{scope or ''}{bang or ''}: {description}"
    return fixed if fixed != subject else None


def fix_subject_case(subject: str, capitalize: bool = True) -> str | None:
    """The subject with its description's first letter in the required case."""
    match = _CONVENTIONAL_PREFIX.match(subject)
    prefix, description = (match.group(1), match.group(2)) if match else ("", subject)
    if not description or not description[0].isalpha():
        return None
    first = description[0].upper() if capitalize else description[0].lower()
    fixed = f"{prefix}{first}{description[1:]}"
    return fixed if fixed != subject else None


def fix_wip(message: str) -> str | None:
    """The message without its work-in-progress marker, or None if that is all there was."""
    stripped = _WIP.sub("", message, count=1)
    if stripped == message or not stripped.strip():
        return None
    return stripped


def signoff_trailer(name: str, email: str) -> str | None:
    """The ``Signed-off-by`` line for this author, or None without both parts."""
    if not name or not email:
        return None
    return f"Signed-off-by: {name} <{email}>"


def fix_branch_type(branch: str, allowed_types: list[str] | None) -> str | None:
    """The branch with its type prefix corrected, or None when there is no near-miss."""
    if not allowed_types or "/" not in branch:
        return None
    raw_type, rest = branch.split("/", 1)
    if not rest:
        return None
    fixed_type = _closest(raw_type, allowed_types)
    if fixed_type is None:
        return None
    fixed = f"{fixed_type}/{rest}"
    return fixed if fixed != branch else None


def strip_lines_containing(message: str, fragments: list[str]) -> str | None:
    """The message without any line that contains one of *fragments*.

    Used to drop AI-attribution trailers: the signature scanner reports the
    text it matched, and the line carrying it is what has to go. Returns
    None when nothing would change or nothing would be left.
    """
    if not fragments:
        return None
    kept = [
        line
        for line in message.splitlines()
        if not any(fragment and fragment in line for fragment in fragments)
    ]
    if len(kept) == len(message.splitlines()):
        return None
    result = "\n".join(kept).strip()
    return result or None
