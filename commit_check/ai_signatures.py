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

# Re-export for convenience — consumers can import everything from
# commit_check.ai_signatures without knowing about the data/logic split.
ALL_KNOWN_TOOLS = _ALL_KNOWN_TOOLS


#: Flat list of all compiled patterns for bulk scanning.
#: Each tuple is ``(regex, tool_name, description, kind)``.
ALL_PATTERNS: list[tuple[re.Pattern[str], str, str, str]] = [
    (p.regex, tool.name, p.description, p.kind)
    for tool in ALL_KNOWN_TOOLS
    for p in tool.patterns
]


def detect_ai_signatures(message: str) -> list[dict[str, str]]:
    """Scan *message* for known AI tool signatures.

    :param message: The full commit message (subject + body) to scan.
    :returns: A list of dicts, one per matched signature, each with keys
        ``"tool"``, ``"kind"``, ``"description"``, and ``"matched_text"``.
        Returns an empty list when no signatures are found.

    Example::

        >>> detect_ai_signatures(
        ...     "feat: init\\n\\nCo-authored-by: Claude <noreply@anthropic.com>"
        ... )
        [{'tool': 'Claude Code', 'kind': 'trailer', ...}]
    """
    results: list[dict[str, str]] = []
    seen: set[str] = set()

    for regex, tool_name, desc, kind in ALL_PATTERNS:
        for match in regex.finditer(message):
            matched = match.group(0).strip()
            if matched not in seen:
                seen.add(matched)
                results.append(
                    {
                        "tool": tool_name,
                        "kind": kind,
                        "description": desc,
                        "matched_text": matched,
                    }
                )

    return results


def has_ai_signature(message: str) -> bool:
    """Return ``True`` if *message* contains any known AI signature."""
    for regex, _tool_name, _desc, _kind in ALL_PATTERNS:
        if regex.search(message):
            return True
    return False


def find_co_authored_by_ai(message: str) -> list[str]:
    """Find ``Co-authored-by`` trailer lines that reference known AI tools.

    Human co-authors like ``Co-authored-by: Jane Doe <jane@example.com>``
    are NOT returned because no known AI tool pattern matches common
    human names.

    :returns: List of matched trailer lines (deduplicated).
    """
    results: list[str] = []
    seen: set[str] = set()
    co_pat = re.compile(r"^Co-authored-by:\s*", re.IGNORECASE | re.MULTILINE)
    if not co_pat.search(message):
        return results

    for regex, _tool_name, _desc, _kind in ALL_PATTERNS:
        for match in regex.finditer(message):
            matched = match.group(0).strip()
            if matched.lower().startswith("co-authored-by:") and matched not in seen:
                seen.add(matched)
                results.append(matched)
    return results


def find_assisted_by_trailers(message: str) -> list[str]:
    """Find ``Assisted-by`` trailer lines in *message*.

    :returns: List of matched ``Assisted-by`` lines.
    """
    pat = re.compile(r"^Assisted-by:\s*\S+.*$", re.MULTILINE | re.IGNORECASE)
    return [m.group(0).strip() for m in pat.finditer(message)]
