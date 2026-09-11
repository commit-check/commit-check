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

    for regex, tool_name, desc, kind, role in ALL_PATTERNS:
        for match in regex.finditer(message):
            matched = match.group(0).strip()
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
    for regex, _tool_name, _desc, _kind, _role in ALL_PATTERNS:
        if regex.search(message):
            return True
    return False


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
