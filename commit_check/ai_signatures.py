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
    alternation whose branches are numbered capturing groups, so a trailer
    line is read once however many tools the catalog knows about. Branches
    are tried in catalog order — the order the separate patterns used to be
    tried in, and the reason the most specific one still wins.

    A body marker has no key, and its group is the pattern by itself.
    """

    keys: frozenset[str]
    regex: re.Pattern[str]
    #: One entry per capturing group, indexed by group number minus one.
    members: tuple[_Member, ...]


def _build_groups() -> list[_Group]:
    """Compile the catalog into one scan per trailer key set, in catalog order."""
    keys_to_slot: dict[frozenset[str], int] = {}
    slots: list[tuple[frozenset[str], list[str], list[_Member]]] = []
    markers: list[tuple[int, _Group]] = []

    for tool in ALL_KNOWN_TOOLS:
        for pattern in tool.patterns:
            member: _Member = (
                tool.name,
                pattern.description,
                pattern.kind,
                pattern.role,
            )
            if not pattern.keys:
                markers.append(
                    (len(slots), _Group(frozenset(), pattern.regex, (member,)))
                )
                continue
            slot = keys_to_slot.get(pattern.keys)
            if slot is None:
                slot = keys_to_slot[pattern.keys] = len(slots)
                slots.append((pattern.keys, [], []))
            slots[slot][1].append(pattern.value_pattern)
            slots[slot][2].append(member)

    groups: list[_Group] = []
    for position, (keys, values, members) in enumerate(slots):
        for marker_at, marker in markers:
            if marker_at == position:
                groups.append(marker)
        alternation = "|".join(re.escape(key) for key in sorted(keys))
        branches = "|".join(
            f"(?P<s{index}>{value})" for index, value in enumerate(values)
        )
        groups.append(
            _Group(
                keys,
                re.compile(
                    rf"^(?:{alternation}):[ \t]*(?:{branches})[ \t]*$",
                    re.IGNORECASE | re.MULTILINE,
                ),
                tuple(members),
            )
        )
    groups.extend(marker for marker_at, marker in markers if marker_at == len(slots))
    return groups


#: The catalog, compiled for scanning.
_GROUPS: list[_Group] = _build_groups()

#: The key of a trailer-shaped line, e.g. ``Co-authored-by`` in
#: ``Co-authored-by: Claude``.
_TRAILER_KEY = re.compile(r"([A-Za-z][A-Za-z0-9-]*):")


def _scan(message: str) -> Iterator[tuple[_Member, str]]:
    """Every signature in *message*, as ``(member, matched text)``.

    A trailer group is measured only against the lines that carry its key,
    so a message says nothing to the tools it does not name, and nothing at
    all when it carries no trailers. Body markers read the whole message;
    there are two.

    Groups come in catalog order and their lines in message order.
    """
    trailers: list[tuple[str, str]] = []
    for line in message.splitlines():
        head = _TRAILER_KEY.match(line)
        if head:
            trailers.append((head.group(1).lower(), line))

    for group in _GROUPS:
        if not group.keys:
            for found in group.regex.finditer(message):
                yield group.members[0], found.group(0).strip()
            continue
        for key, line in trailers:
            if key not in group.keys:
                continue
            branch = group.regex.search(line)
            if branch:
                # Exactly one branch of the alternation took part, and its
                # number says which pattern matched.
                yield (
                    group.members[(branch.lastindex or 1) - 1],
                    branch.group(0).strip(),
                )


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
    """Return ``True`` if *message* contains any known AI signature."""
    return any(True for _member, _matched in _scan(message))


def find_trailers(message: str, keys: list[str]) -> list[tuple[str, str, str]]:
    """Every trailer line in *message* whose key is one of *keys*.

    Keys match case-insensitively (``Co-Authored-By`` is ``Co-authored-by``),
    anywhere in the message at the start of a line — the same reading the
    signature scanner and the sign-off rule take, and the one GitHub takes
    when it looks for co-authors.

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
