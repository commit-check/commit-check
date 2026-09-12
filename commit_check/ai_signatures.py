"""AI tool signature detection logic.

This module provides the public API for detecting AI tool signatures in commit
messages.  The signature data (tool definitions and patterns) lives in
:mod:`commit_check.ai_signatures_data`.

Typical usage::

    from commit_check.ai_signatures import detect_ai_signatures

    result = detect_ai_signatures(
        "feat: init\\n\\nCo-authored-by: Claude <noreply@anthropic.com>"
    )
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from functools import lru_cache

from commit_check.ai_signatures_data import ALL_KNOWN_TOOLS as _ALL_KNOWN_TOOLS
from commit_check.ai_signatures_data import GENERIC_AI, ROLE_DISCLOSURE

# Re-export for convenience — consumers can import everything from
# commit_check.ai_signatures without knowing about the data/logic split.
ALL_KNOWN_TOOLS = _ALL_KNOWN_TOOLS


#: Flat list of all compiled patterns for bulk scanning.
#: Each tuple is ``(regex, tool_name, description, kind, role)``.
ALL_PATTERNS: list[tuple[re.Pattern[str], str, str, str, str]] = [
    (p.regex, tool.name, p.description, p.kind, p.role)
    for tool in ALL_KNOWN_TOOLS
    for p in tool.patterns
]

#: The tools that can be recognised by name in free text.
_NAMED_TOOLS: list[tuple[re.Pattern[str], str]] = [
    (tool.name_pattern, tool.name)
    for tool in ALL_KNOWN_TOOLS
    if tool.name_pattern is not None
]

#: What a match says about the tool: ``(tool, description, kind, role)``.
_Member = tuple[str, str, str, str]


@dataclass(frozen=True)
class _Group:
    """One compiled scan, and what each of its alternatives means.

    Every pattern that reads the same trailer key is compiled into a single
    alternation whose branches are numbered capturing groups, in catalog
    order, so a trailer line is read once however many tools the catalog
    knows and the most specific pattern still wins. A body marker has no
    key, and its group is the pattern by itself.
    """

    keys: frozenset[str]
    regex: re.Pattern[str]
    #: One entry per capturing group, indexed by group number minus one.
    members: tuple[_Member, ...]


def _build_groups() -> list[_Group]:
    """Compile the catalog: one alternation per trailer key set, then the markers.

    Order between groups carries no meaning — each line is read by the one
    group whose key it starts with — so the trailer groups come in the order
    their key sets first appear and the body markers after them.
    """
    keyed: dict[frozenset[str], tuple[list[str], list[_Member]]] = {}
    markers: list[_Group] = []
    for tool in ALL_KNOWN_TOOLS:
        for pattern in tool.patterns:
            member: _Member = (
                tool.name,
                pattern.description,
                pattern.kind,
                pattern.role,
            )
            if not pattern.keys:
                markers.append(_Group(frozenset(), pattern.regex, (member,)))
                continue
            values, members = keyed.setdefault(pattern.keys, ([], []))
            values.append(pattern.value_pattern)
            members.append(member)

    groups = []
    for keys, (values, members) in keyed.items():
        alternation = "|".join(re.escape(key) for key in sorted(keys))
        branches = "|".join(f"(?P<s{i}>{value})" for i, value in enumerate(values))
        regex = re.compile(
            rf"^(?:{alternation}):[ \t]*(?:{branches})[ \t]*$",
            re.IGNORECASE | re.MULTILINE,
        )
        groups.append(_Group(keys, regex, tuple(members)))
    return groups + markers


@lru_cache(maxsize=1)
def groups() -> tuple[_Group, ...]:
    """The catalog, compiled for scanning — on first use, not at import.

    ``ai_attribution`` is off by default, so most runs never scan a message
    at all, and compiling the alternations costs milliseconds in a cold
    interpreter: real money for a hook that runs on every commit.
    """
    return tuple(_build_groups())


@lru_cache(maxsize=1)
def _scans() -> tuple[re.Pattern[str], ...]:
    """The group regexes alone, for a question that needs no detail."""
    return tuple(group.regex for group in groups())


#: The key of a trailer-shaped line, e.g. ``Co-authored-by`` in
#: ``Co-authored-by: Claude``.
_TRAILER_KEY = re.compile(r"([A-Za-z][A-Za-z0-9-]*):")


def _trailer_lines(message: str) -> list[tuple[str, str]]:
    """Every trailer-shaped line in *message*, as ``(key, line)``.

    The key is lower-cased, because a trailer is read case-insensitively;
    the line is kept as written, because it is what gets reported.
    """
    lines: list[tuple[str, str]] = []
    for line in message.splitlines():
        head = _TRAILER_KEY.match(line)
        if head:
            lines.append((head.group(1).lower(), line))
    return lines


def _group_matches(
    group: _Group, trailers: list[tuple[str, str]], message: str
) -> Iterator[tuple[_Member, str]]:
    """What *group* finds, in message order."""
    if not group.keys:
        for found in group.regex.finditer(message):
            yield group.members[0], found.group(0).strip()
        return
    for key, line in trailers:
        if key not in group.keys:
            continue
        branch = group.regex.search(line)
        if branch:
            # Exactly one branch of the alternation took part, and its
            # number says which pattern matched.
            yield group.members[(branch.lastindex or 1) - 1], branch.group(0).strip()


def _scan(message: str) -> Iterator[tuple[_Member, str]]:
    """Every signature in *message*, as ``(member, matched text)``.

    A trailer group is measured only against the lines that carry its key,
    so a message says nothing to the tools it does not name, and nothing at
    all when it carries no trailers. Body markers read the whole message.
    """
    trailers = _trailer_lines(message)
    for group in groups():
        yield from _group_matches(group, trailers, message)


def tool_named_in(text: str) -> str | None:
    """The known tool *text* names, or ``None`` when it names none."""
    for pattern, name in _NAMED_TOOLS:
        if pattern.search(text):
            return name
    return None


def _split_trailer(line: str) -> tuple[str, str]:
    """A trailer line as ``(key, value)``, both stripped."""
    key, _, value = line.partition(":")
    return key.strip(), value.strip()


def detect_ai_signatures(message: str) -> list[dict[str, str]]:
    """Scan *message* for known AI tool signatures.

    :param message: The full commit message (subject + body) to scan.
    :returns: A list of dicts, one per matched signature, each with keys
        ``"tool"``, ``"kind"``, ``"role"``, ``"description"``,
        ``"matched_text"``, and — for a trailer — ``"trailer"`` (the key as
        written) and ``"value"``; both are empty for a body marker.
        Returns an empty list when no signatures are found.

    Example::

        >>> detect_ai_signatures(
        ...     "feat: init\\n\\nCo-authored-by: Claude <noreply@anthropic.com>"
        ... )
        [{'tool': 'Claude Code', 'kind': 'trailer', 'role': 'co_author', ...}]
    """
    results: list[dict[str, str]] = []
    seen: set[str] = set()

    for (tool_name, desc, kind, role), matched in _scan(message):
        if matched in seen:
            continue
        seen.add(matched)
        trailer = value = ""
        if kind == "trailer":
            trailer, value = _split_trailer(matched)
        tool = tool_name
        if role == ROLE_DISCLOSURE and tool_name == GENERIC_AI.name:
            # The disclosure trailers are matched generically, on their
            # key alone; the value is where the tool is named.
            tool = tool_named_in(value) or tool_name
        results.append(
            {
                "tool": tool,
                "kind": kind,
                "role": role,
                "description": desc,
                "matched_text": matched,
                "trailer": trailer,
                "value": value,
            }
        )

    return results


def has_ai_signature(message: str) -> bool:
    """Return ``True`` if *message* contains any known AI signature.

    This one asks a yes/no question and stops at the first answer, so it
    reads the message directly rather than splitting it into lines first:
    the split only pays for itself when there is nothing to find in a long
    message, and every group is anchored to a line start anyway.
    """
    for scan in _scans():
        if scan.search(message):
            return True
    return False


def find_trailers(message: str, keys: list[str]) -> list[tuple[str, str, str]]:
    """Every trailer line in *message* whose key is one of *keys*.

    Keys match case-insensitively, at the start of any line — the reading
    the signature scanner and the sign-off rule take too.

    :returns: ``(key as written, value, line)`` per match, in message order;
        the value is empty for a trailer that names nothing.
    """
    if not keys:
        return []
    alternation = "|".join(re.escape(key) for key in keys)
    pattern = re.compile(
        rf"^({alternation}):[ \t]*([^\n]*?)[ \t]*$", re.IGNORECASE | re.MULTILINE
    )
    return [
        (match.group(1), match.group(2), match.group(0))
        for match in pattern.finditer(message)
    ]
