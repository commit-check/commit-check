"""Known AI tool signatures — pure data, no detection logic.

This module defines the data structures and the curated registry of known AI
coding tool signatures.  To add a new tool, define a ``KnownAiTool`` entry
with its patterns and add it to ``ALL_KNOWN_TOOLS``.

The detection logic lives in :mod:`commit_check.ai_signatures`.
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
            r"(?:\s*<(?:noreply@anthropic\.com"
            r"|\d+\+Claude@users\.noreply\.github\.com)>)?",
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
        # A hyphenated model suffix is required so bare human first names
        # ("Claude", "Gemini") are NOT flagged, regardless of the email.
        _trailer(
            "Co-authored-by",
            r"(?:claude|gpt|gemini)[\w.]*-[\w.-]+(?:\s*<[^>]*>)?",
            "``Co-authored-by`` with AI model name",
        ),
        # Catch Assisted-by trailer (Linux kernel style) regardless of agent,
        # with optional trailing tool list.
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
