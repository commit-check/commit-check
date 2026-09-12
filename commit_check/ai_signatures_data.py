"""Known AI tool signatures — pure data, no detection logic.

This module defines the data structures and the curated registry of known AI
coding tool signatures.  To add a new tool, define a ``KnownAiTool`` entry
with its patterns and add it to ``ALL_KNOWN_TOOLS``.

Every pattern carries a *role*: how the line places the tool in the commit.
The role is what a policy rules on. ``forbid`` objects to all of them;
``disclose`` accepts a disclosure and objects to the tool taking a person's
place — as a co-author, or as the one certifying the DCO.

The detection logic lives in :mod:`commit_check.ai_signatures`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

#: A trailer whose purpose is to disclose AI assistance: ``Assisted-by``
#: (Linux kernel, Fedora, FluxCD), ``Generated-by`` (Apache Software
#: Foundation).
ROLE_DISCLOSURE = "disclosure"
#: The tool credited as a person who wrote part of the change:
#: ``Co-authored-by``, ``Co-developed-by``.
ROLE_CO_AUTHOR = "co_author"
#: The tool certifying the Developer Certificate of Origin: ``Signed-off-by``.
ROLE_SIGNOFF = "signoff"
#: A vendor's own mark: a "Generated with" line, a session-ID trailer.
ROLE_STAMP = "stamp"

ROLES = frozenset({ROLE_DISCLOSURE, ROLE_CO_AUTHOR, ROLE_SIGNOFF, ROLE_STAMP})


@dataclass(frozen=True)
class AiSignaturePattern:
    """A single pattern that identifies AI tool usage in a commit message.

    :param regex: A compiled regex that, if matched anywhere in the commit
        message body, indicates the corresponding tool was involved.
    :param kind: ``"trailer"`` for structured ``Key: value`` footer lines
        (matched case-insensitively), ``"body_marker"`` for any other text
        marker.
    :param role: How the match places the tool in the commit — one of
        :data:`ROLES`.
    :param description: Human-readable description of what is matched.
    :param keys: For a trailer, the keys it can match, lower-cased; empty for
        a body marker. The scanner indexes on these so a message is only
        measured against the trailers it actually carries.
    :param value_pattern: For a trailer, what may follow the key. The scanner
        compiles the value patterns that share a key into one alternation,
        so a trailer line is read once however many tools the catalog knows.
    """

    regex: re.Pattern[str]
    kind: str  # "trailer" | "body_marker"
    role: str
    description: str = ""
    keys: frozenset[str] = frozenset()
    value_pattern: str = ""


@dataclass(frozen=True)
class KnownAiTool:
    """A known AI coding tool and its commit-message signatures.

    :param name: Short display name (e.g. ``"Claude Code"``, ``"GitHub Copilot"``).
    :param patterns: One or more signature patterns that indicate this tool.
    :param name_pattern: A regex that recognises the tool when it is named in
        free text — the value of a disclosure trailer, say — so a generic
        ``Assisted-by:`` match can still be attributed to the tool it names.
    """

    name: str
    patterns: list[AiSignaturePattern] = field(default_factory=list)
    name_pattern: re.Pattern[str] | None = None


# ---------------------------------------------------------------------------
#  Pattern helpers
# ---------------------------------------------------------------------------

#: Trailers whose value credits a person who wrote part of the change.
PERSON_TRAILERS = ("Co-authored-by", "Co-developed-by")


def _trailer(
    keys: tuple[str, ...], value_pattern: str, role: str, description: str
) -> AiSignaturePattern:
    """Build a trailer pattern for a structured ``Key: value`` line.

    The match is case-insensitive and anchors the key at the start of a line.
    Horizontal whitespace only around the value: ``\\s`` would let a match run
    on to the next trailer line and report two lines as one.
    """
    alternation = "|".join(re.escape(key) for key in keys)
    raw = rf"^(?:{alternation}):[ \t]*{value_pattern}[ \t]*$"
    return AiSignaturePattern(
        regex=re.compile(raw, re.IGNORECASE | re.MULTILINE),
        kind="trailer",
        role=role,
        description=description,
        keys=frozenset(key.lower() for key in keys),
        value_pattern=value_pattern,
    )


def _identity(value_pattern: str, label: str) -> list[AiSignaturePattern]:
    """The co-author and sign-off patterns for one way a tool names itself.

    A tool that can appear after ``Co-authored-by:`` can appear after
    ``Signed-off-by:`` just the same, and the policies that object to the
    one object to the other; one identity pattern serves both so the two
    cannot drift apart.
    """
    return [
        _trailer(
            PERSON_TRAILERS,
            value_pattern,
            ROLE_CO_AUTHOR,
            f"``Co-authored-by: {label}`` trailer",
        ),
        _trailer(
            ("Signed-off-by",),
            value_pattern,
            ROLE_SIGNOFF,
            f"``Signed-off-by: {label}`` trailer",
        ),
    ]


def _disclosure(key: str, description: str) -> AiSignaturePattern:
    """A trailer that exists to disclose AI assistance, whatever its value."""
    return _trailer((key,), r"\S[^\n]*", ROLE_DISCLOSURE, description)


def _stamp_trailer(key: str, description: str) -> AiSignaturePattern:
    """A trailer a vendor adds for its own purposes, such as a session ID."""
    return _trailer((key,), r"\S+", ROLE_STAMP, description)


def _body_marker(pattern: str, description: str = "") -> AiSignaturePattern:
    """Build a free-text body marker pattern."""
    return AiSignaturePattern(
        regex=re.compile(pattern, re.MULTILINE),
        kind="body_marker",
        role=ROLE_STAMP,
        description=description,
    )


def _names(pattern: str) -> re.Pattern[str]:
    """Compile a ``name_pattern``: the tool's names, as whole words.

    Bounded at both ends, or a tool's name would be found inside a longer
    one: without this, ``Generated-by: Raider`` was disclosed as Aider.
    ``\\b`` cannot serve here because a name may begin or end with a
    non-word character.
    """
    return re.compile(rf"(?<!\w)(?:{pattern})(?!\w)", re.IGNORECASE)


# ---------------------------------------------------------------------------
#  Known tool signatures
# ---------------------------------------------------------------------------

# --- Anthropic Claude Code / Claude CLI ---
CLAUDE_CODE = KnownAiTool(
    name="Claude Code",
    name_pattern=_names(r"\bclaude\b|anthropic"),
    patterns=[
        # Standard Co-authored-by trailer added by Claude Code.
        # When an email is present, anchor to known AI noreply addresses
        # to avoid false positives with human co-authors named Claude.
        *_identity(
            r"Claude(?: Code)?"
            r"(?:[ \t]*<(?:noreply@anthropic\.com"
            r"|\d+\+Claude@users\.noreply\.github\.com)>)?",
            "Claude",
        ),
        # Any name with the Anthropic noreply email — catches model-name
        # variants such as "Claude Opus 4.5 (1M context)" that the pattern
        # above misses.
        *_identity(r"[^<\n]*<noreply@anthropic\.com>", "... <noreply@anthropic.com>"),
        # Body marker: generated-with notice
        _body_marker(
            r"🤖\s*Generated\s+(?:with|by)\s+\[?Claude",
            "``🤖 Generated with Claude`` body marker",
        ),
        # Session ID trailer (Claude Code sometimes adds this)
        _stamp_trailer("Claude-Session", "``Claude-Session:`` trailer"),
        # Workflow ID trailer
        _stamp_trailer("Claude-Workflow", "``Claude-Workflow:`` trailer"),
    ],
)

# --- GitHub Copilot ---
COPILOT = KnownAiTool(
    name="GitHub Copilot",
    name_pattern=_names(r"copilot"),
    patterns=[
        *_identity(
            r"Copilot(?:[ \t]*<\d+\+Copilot@users\.noreply\.github\.com>)?",
            "Copilot",
        ),
    ],
)

# --- OpenAI Codex ---
CODEX = KnownAiTool(
    name="OpenAI Codex",
    name_pattern=_names(r"codex"),
    patterns=[
        *_identity(r"Codex[ \t]*(?:<[^>\n]*>)?", "Codex"),
    ],
)

# --- Gemini (Google) ---
GEMINI = KnownAiTool(
    name="Gemini",
    name_pattern=_names(r"gemini"),
    patterns=[
        *_identity(r"Gemini[ \t]*(?:<[^>\n]*>)?", "Gemini"),
    ],
)

# --- Cursor ---
CURSOR = KnownAiTool(
    name="Cursor",
    name_pattern=_names(r"cursor"),
    patterns=[
        *_identity(r"Cursor[ \t]*(?:<[^>\n]*>)?", "Cursor"),
    ],
)

# --- Devin ---
DEVIN = KnownAiTool(
    name="Devin",
    name_pattern=_names(r"devin"),
    patterns=[
        *_identity(r"Devin[ \t]*(?:<[^>\n]*>)?", "Devin"),
    ],
)

# --- Aider ---
AIDER = KnownAiTool(
    name="Aider",
    name_pattern=_names(r"aider"),
    patterns=[
        *_identity(r"Aider[ \t]*(?:<[^>\n]*>)?", "Aider"),
        # aider appends "(aider)" to the author name
        *_identity(r"[^<\n]+\(aider\)[ \t]*(?:<[^>\n]*>)?", "... (aider)"),
    ],
)

# --- Windsurf (Codeium) ---
WINDSURF = KnownAiTool(
    name="Windsurf",
    name_pattern=_names(r"windsurf|codeium"),
    patterns=[
        *_identity(r"Windsurf[ \t]*(?:<[^>\n]*>)?", "Windsurf"),
    ],
)

# --- Tabby ---
TABBY = KnownAiTool(
    name="Tabby",
    name_pattern=_names(r"tabby"),
    patterns=[
        *_identity(r"Tabby[ \t]*(?:<[^>\n]*>)?", "Tabby"),
    ],
)

# --- Generic / catch-all AI patterns ---
GENERIC_AI = KnownAiTool(
    name="Generic AI",
    patterns=[
        # Catch AI agent model identifiers credited as a person
        # (e.g. claude-sonnet-4, gpt-4-turbo, gemini-1.5-pro).
        # A hyphenated model suffix is required so bare human first names
        # ("Claude", "Gemini") are NOT flagged, regardless of the email.
        *_identity(
            r"(?:claude|gpt|gemini)[\w.]*-[\w.-]+(?:[ \t]*<[^>\n]*>)?",
            "<model-name>",
        ),
        # Catch space-separated AI model identifiers credited as a person
        # (e.g. "Claude Opus 4.5", "Gemini 2.5 Pro", "GPT 4 Turbo").
        # A purely numeric version token is required so human names with
        # ordinals ("Claude Dubois 3rd") are NOT flagged.
        *_identity(
            r"(?:claude|gpt|gemini)(?:[ \t]+[a-z]+)*[ \t]+\d+(?:\.\d+)*(?!\w)"
            r"(?:[ \t]+[a-z]+)*(?:[ \t]*\([^)\n]*\))?(?:[ \t]*<[^>\n]*>)?",
            "<Model N.N>",
        ),
        # The disclosure trailers. Any value counts: the Linux kernel writes
        # "Assisted-by: LLM coccinelle sparse", Fedora "Assisted-by: ChatGPTv5",
        # FluxCD "Assisted-by: claude-code/claude-opus-4"; the key alone says
        # a tool was involved.
        _disclosure(
            "Assisted-by",
            "``Assisted-by:`` trailer (Linux kernel, Fedora, FluxCD)",
        ),
        _disclosure(
            "Generated-by",
            "``Generated-by:`` trailer (Apache Software Foundation)",
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
