"""Known AI tool signatures found in commit messages and trailers.

This module maintains a curated directory of patterns that known AI coding
tools leave behind in commit messages.  It is the technical core of the
``ai_attribution`` validator — keeping this database up to date is what
gives users a reason to use commit-check instead of rolling their own regex.

Each entry describes:
* A human-readable tool name (for error messages).
* One or more regex patterns that match trailers, footers, or body markers
  left by that tool.
* Whether the pattern is a ``trailer`` (structured key: value line, typically
  in the commit body footer) or a ``body_marker`` (free-text marker anywhere
  in the message body).

Adding a new tool
-----------------
#. Find the commit-message artefacts the tool produces (e.g.
   ``Co-Authored-By: Copilot <noreply@github.com>``).
#. Add a ``KnownAiTool`` entry with a unique name and one or more patterns.
#. Submit a PR — the project maintainers will review and release.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class AiSignaturePattern:
    """A single pattern that identifies AI tool usage in a commit message.

    :param regex: A compiled regex that, if matched anywhere in the commit
        message body, indicates the corresponding tool was involved.
    :param kind: ``"trailer"`` for structured ``Key: value`` footer lines
        (matched case-insensitively), ``"body_marker"`` for any other text
        marker.
    :param description: Human-readable description of what is matched.
    """

    regex: re.Pattern[str]
    kind: str  # "trailer" | "body_marker"
    description: str = ""


@dataclass(frozen=True)
class KnownAiTool:
    """A known AI coding tool and its commit-message signatures.

    :param name: Short display name (e.g. ``"Claude Code"``, ``"GitHub Copilot"``).
    :param patterns: One or more signature patterns that indicate this tool.
    """

    name: str
    patterns: list[AiSignaturePattern] = field(default_factory=list)


# ---------------------------------------------------------------------------
#  Pattern helpers
# ---------------------------------------------------------------------------


def _trailer(
    key: str, value_pattern: str = r".*", description: str = ""
) -> AiSignaturePattern:
    """Build a trailer pattern for a structured ``Key: value`` line.

    The match is case-insensitive and anchors the key at the start of a line.
    """
    raw = rf"^{re.escape(key)}:\s*{value_pattern}\s*$"
    return AiSignaturePattern(
        regex=re.compile(raw, re.IGNORECASE | re.MULTILINE),
        kind="trailer",
        description=description or f"``{key}:`` trailer",
    )


def _body_marker(pattern: str, description: str = "") -> AiSignaturePattern:
    """Build a free-text body marker pattern."""
    return AiSignaturePattern(
        regex=re.compile(pattern, re.MULTILINE),
        kind="body_marker",
        description=description,
    )


# ---------------------------------------------------------------------------
#  Known tool signatures
# ---------------------------------------------------------------------------

# --- Anthropic Claude Code / Claude CLI ---
CLAUDE_CODE = KnownAiTool(
    name="Claude Code",
    patterns=[
        # Standard Co-authored-by trailer added by Claude Code.
        # When an email is present, anchor to known AI noreply addresses
        # to avoid false positives with human co-authors named Claude.
        _trailer(
            "Co-authored-by",
            r"Claude(?: Code)?"
            r"(?:\s*<(?:"
            r"noreply@anthropic\.com"
            r"|\d+\+Claude@users\.noreply\.github\.com"
            r")>)?",
            "``Co-authored-by: Claude`` trailer",
        ),
        # Assisted-by trailer (Linux kernel style, with optional tool list)
        _trailer(
            "Assisted-by",
            r"Claude:\S+(?:\s+\S+)*",
            "``Assisted-by: Claude:<model> [tools]`` trailer",
        ),
        # Body marker: generated-with notice
        _body_marker(
            r"🤖\s*Generated\s+(?:with|by)\s+\[?Claude",
            "``🤖 Generated with Claude`` body marker",
        ),
        # Session ID trailer (Claude Code sometimes adds this)
        _trailer("Claude-Session", r"\S+", "``Claude-Session:`` trailer"),
        # Workflow ID trailer
        _trailer("Claude-Workflow", r"\S+", "``Claude-Workflow:`` trailer"),
    ],
)

# --- GitHub Copilot ---
COPILOT = KnownAiTool(
    name="GitHub Copilot",
    patterns=[
        _trailer(
            "Co-authored-by",
            r"Copilot"
            r"(?:\s*<\d+\+Copilot@users\.noreply\.github\.com>)?",
            "``Co-authored-by: Copilot`` trailer",
        ),
    ],
)

# --- OpenAI Codex ---
CODEX = KnownAiTool(
    name="OpenAI Codex",
    patterns=[
        _trailer(
            "Co-authored-by",
            r"Codex\s*(?:<[^>]*>)?",
            "``Co-authored-by: Codex`` trailer",
        ),
    ],
)

# --- Gemini (Google) ---
GEMINI = KnownAiTool(
    name="Gemini",
    patterns=[
        _trailer(
            "Co-authored-by",
            r"Gemini\s*(?:<[^>]*>)?",
            "``Co-authored-by: Gemini`` trailer",
        ),
    ],
)

# --- Cursor ---
CURSOR = KnownAiTool(
    name="Cursor",
    patterns=[
        _trailer(
            "Co-authored-by",
            r"Cursor\s*(?:<[^>]*>)?",
            "``Co-authored-by: Cursor`` trailer",
        ),
    ],
)

# --- Devin ---
DEVIN = KnownAiTool(
    name="Devin",
    patterns=[
        _trailer(
            "Co-authored-by",
            r"Devin\s*(?:<[^>]*>)?",
            "``Co-authored-by: Devin`` trailer",
        ),
    ],
)

# --- Aider ---
AIDER = KnownAiTool(
    name="Aider",
    patterns=[
        _trailer(
            "Co-authored-by",
            r"Aider\s*(?:<[^>]*>)?",
            "``Co-authored-by: Aider`` trailer",
        ),
        # aider appends "(aider)" to the author name
        _trailer(
            "Co-authored-by",
            r"[^<]+\(aider\)\s*(?:<[^>]*>)?",
            "``Co-authored-by: ... (aider)`` trailer",
        ),
    ],
)

# --- Windsurf (Codeium) ---
WINDSURF = KnownAiTool(
    name="Windsurf",
    patterns=[
        _trailer(
            "Co-authored-by",
            r"Windsurf\s*(?:<[^>]*>)?",
            "``Co-authored-by: Windsurf`` trailer",
        ),
    ],
)

# --- Tabby ---
TABBY = KnownAiTool(
    name="Tabby",
    patterns=[
        _trailer(
            "Co-authored-by",
            r"Tabby\s*(?:<[^>]*>)?",
            "``Co-authored-by: Tabby`` trailer",
        ),
    ],
)

# --- Generic / catch-all AI patterns ---
GENERIC_AI = KnownAiTool(
    name="Generic AI",
    patterns=[
        # Catch AI agent model identifiers in Co-authored-by
        # (e.g. claude-sonnet-4, gpt-4-turbo, gemini-1.5-pro).
        # Only matches values that look like model names (containing
        # word chars, dots, or hyphens — not plain human names).
        _trailer(
            "Co-authored-by",
            r"(?:claude|gpt|gemini)[\w.-]*(?:\s*<[^>]*>)?",
            "``Co-authored-by`` with AI model name",
        ),
        # Catch Assisted-by trailer (Linux kernel style) regardless of agent,
        # with optional trailing tool list, e.g.:
        # "Assisted-by: Claude:claude-3-opus coccinelle sparse"
        _trailer(
            "Assisted-by",
            r"\S+:\S+(?:\s+\S+)*",
            "``Assisted-by: <tool>:<model> [tools]`` trailer (kernel style)",
        ),
        # Catch common body markers
        _body_marker(
            r"^Generated\s+(?:by|with)\s+(?:AI|artificial intelligence)",
            "``Generated by AI`` body marker",
        ),
    ],
)

# ---------------------------------------------------------------------------
#  Master registry — ordered by specificity (most specific first)
# ---------------------------------------------------------------------------

#: All known AI tools, ordered so that more specific patterns are checked first.
ALL_KNOWN_TOOLS: list[KnownAiTool] = [
    CLAUDE_CODE,
    COPILOT,
    CODEX,
    GEMINI,
    CURSOR,
    DEVIN,
    AIDER,
    WINDSURF,
    TABBY,
    GENERIC_AI,
]

#: Flat list of all compiled patterns for bulk scanning.
#: Each tuple is ``(regex, tool_name, description, kind)``.
ALL_PATTERNS: list[tuple[re.Pattern[str], str, str, str]] = [
    (p.regex, tool.name, p.description, p.kind)
    for tool in ALL_KNOWN_TOOLS
    for p in tool.patterns
]


# ---------------------------------------------------------------------------
#  Public API
# ---------------------------------------------------------------------------


def detect_ai_signatures(message: str) -> list[dict[str, str]]:
    """Scan *message* for known AI tool signatures.

    :param message: The full commit message (subject + body) to scan.
    :returns: A list of dicts, one per matched signature, each with keys
        ``"tool"``, ``"kind"``, ``"description"``, and ``"matched_text"``.
        Returns an empty list when no signatures are found.

    Example::

        >>> detect_ai_signatures("feat: init\\n\\nCo-authored-by: Claude <noreply@anthropic.com>")
        [{'tool': 'Claude Code', 'kind': 'trailer', 'description': '``Co-authored-by: Claude`` trailer', 'matched_text': 'Co-authored-by: Claude <noreply@anthropic.com>'}]
    """
    results: list[dict[str, str]] = []
    seen: set[str] = set()  # deduplicate by matched text

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

    Scans all known AI patterns and collects those that start with
    ``Co-authored-by:`` (case-insensitive).  Human co-authors like
    ``Co-authored-by: Jane Doe <jane@example.com>`` are NOT returned
    because no known AI tool pattern matches common human names.

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
