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
    Blanks may precede the colon, because git reads ``Key : value`` as the
    trailer ``Key: value``. Horizontal whitespace only around the value:
    ``\\s`` would let a match run on to the next trailer line and report two
    lines as one. The value starts and ends on a non-blank character, so a
    long run of spaces around it can be read only one way; see
    ``ai_signatures._build_groups``.
    """
    alternation = "|".join(re.escape(key) for key in keys)
    raw = rf"^(?:{alternation})[ \t]*:[ \t]*(?=\S)(?:{value_pattern})(?<![ \t])[ \t]*$"
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

    One identity serves both trailers, so the two cannot drift apart.
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


def _app_bot(login: str) -> list[AiSignaturePattern]:
    """The identity of a tool's GitHub App: ``<login>[bot]``, with any address.

    A GitHub App commits under its own ``[bot]`` account, and no person can
    hold that name, so the address needs no anchoring.
    """
    return _identity(rf"{re.escape(login)}\[bot\][ \t]*(?:<[^>\n]*>)?", f"{login}[bot]")


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

    Bounded at both ends, or ``Generated-by: Raider`` is disclosed as Aider.
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
        # The Claude GitHub App, which commits as itself.
        *_app_bot("claude"),
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
# The coding agent links each of its commits to the session logs with an
# ``Agent-Logs-Url`` trailer, and a squash merge of its pull request credits
# it as ``copilot-swe-agent[bot] <198982749+Copilot@users.noreply.github.com>``:
# https://github.blog/changelog/2026-03-20-trace-any-copilot-coding-agent-commit-to-its-session-logs
COPILOT = KnownAiTool(
    name="GitHub Copilot",
    name_pattern=_names(r"copilot"),
    patterns=[
        *_identity(
            r"Copilot(?:[ \t]*<\d+\+Copilot@users\.noreply\.github\.com>)?",
            "Copilot",
        ),
        # Only the Copilot account has this address, so it catches the agent
        # under any display name.
        *_identity(
            r"[^<\n]*<\d+\+Copilot@users\.noreply\.github\.com>",
            "... <N+Copilot@users.noreply.github.com>",
        ),
        _stamp_trailer("Agent-Logs-Url", "``Agent-Logs-Url:`` trailer"),
    ],
)

# --- OpenAI Codex ---
CODEX = KnownAiTool(
    name="OpenAI Codex",
    name_pattern=_names(r"codex"),
    patterns=[
        *_identity(r"Codex[ \t]*(?:<[^>\n]*>)?", "Codex"),
        # Codex in the cloud commits through its GitHub App.
        *_app_bot("chatgpt-codex-connector"),
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
        *_identity(r"Cursor(?: Agent)?[ \t]*(?:<[^>\n]*>)?", "Cursor"),
        # Cursor's agent signs as ``Cursor Agent <cursoragent@cursor.com>``;
        # the address catches it under any display name.
        *_identity(r"[^<\n]*<cursoragent@cursor\.com>", "... <cursoragent@cursor.com>"),
        # Cursor's background agent commits through its GitHub App.
        *_app_bot("cursor"),
        # Cursor's own mark on commits it writes:
        # https://forum.cursor.com/t/allow-disabling-made-with-cursor-commit-trailer/154494
        _trailer(
            ("Made-with",), r"Cursor", ROLE_STAMP, "``Made-with: Cursor`` trailer"
        ),
    ],
)

# --- Devin ---
# Devin credits itself as ``Devin AI`` with its GitHub App's address,
# ``158243242+devin-ai-integration[bot]@users.noreply.github.com``.
# "Devin" alone is a person's name, so with an address it counts only when
# the address is the app's.
DEVIN = KnownAiTool(
    name="Devin",
    name_pattern=_names(r"devin"),
    patterns=[
        *_identity(r"Devin AI[ \t]*(?:<[^>\n]*>)?", "Devin AI"),
        *_identity(
            r"Devin(?:[ \t]*<(?:\d+\+)?devin-ai-integration\[bot\]"
            r"@users\.noreply\.github\.com>)?",
            "Devin",
        ),
        # The app's address catches it under any display name.
        *_identity(
            r"[^<\n]*<(?:\d+\+)?devin-ai-integration\[bot\]"
            r"@users\.noreply\.github\.com>",
            "... <N+devin-ai-integration[bot]@users.noreply.github.com>",
        ),
    ],
)

# --- Aider ---
AIDER = KnownAiTool(
    name="Aider",
    name_pattern=_names(r"aider"),
    patterns=[
        *_identity(r"Aider[ \t]*(?:<[^>\n]*>)?", "Aider"),
        # aider's own trailer names the model, on by default since v0.85:
        # "Co-authored-by: aider (<model>) <aider@aider.chat>", see
        # https://github.com/Aider-AI/aider/blob/main/aider/repo.py
        *_identity(r"[^<\n]*<aider@aider\.chat>", "... <aider@aider.chat>"),
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

# --- Amp (Sourcegraph) ---
# Both trailers are on by default and switched off in Amp's settings:
# https://ampcode.com/docs/cli/settings
AMP = KnownAiTool(
    name="Amp",
    name_pattern=_names(r"amp|ampcode"),
    patterns=[
        # "Amp" is a short word, so when an address is present it must be
        # Amp's own.
        *_identity(r"Amp(?:[ \t]*<amp@ampcode\.com>)?", "Amp <amp@ampcode.com>"),
        _stamp_trailer("Amp-Thread-ID", "``Amp-Thread-ID:`` trailer"),
    ],
)

# --- OpenHands (All Hands AI) ---
# Commits as openhands <openhands@all-hands.dev> by default, and stays on as
# a co-author when the user sets their own identity:
# https://docs.openhands.dev/openhands/usage/settings/application-settings
OPENHANDS = KnownAiTool(
    name="OpenHands",
    name_pattern=_names(r"openhands|all-hands"),
    patterns=[
        # By name only: the people who work at All Hands share the agent's
        # all-hands.dev domain.
        *_identity(r"OpenHands[ \t]*(?:<[^>\n]*>)?", "OpenHands"),
    ],
)

# --- Factory Droid ---
# Adds itself as a co-author by default (includeCoAuthoredByDroid):
# https://docs.factory.com/droid-cli/settings.md
FACTORY_DROID = KnownAiTool(
    name="Factory Droid",
    name_pattern=_names(r"factory-droid|droid"),
    patterns=[
        *_identity(r"factory-droid\[bot\][ \t]*(?:<[^>\n]*>)?", "factory-droid[bot]"),
    ],
)

# --- Jules (Google) ---
# Commits as the google-labs-jules[bot] app, or co-authors with the user
# when Commit Authoring says so: https://jules.google/docs/changelog/2026-02-19
# "Jules" alone is a person's name, so only the app's name counts.
JULES = KnownAiTool(
    name="Jules",
    name_pattern=_names(r"google-labs-jules|jules"),
    patterns=[
        *_identity(
            r"google-labs-jules\[bot\][ \t]*(?:<[^>\n]*>)?", "google-labs-jules[bot]"
        ),
    ],
)

# --- Continue (continue.dev) ---
# The Continue CLI injects a commit signature by default, unless
# CONTINUE_CLI_DISABLE_COMMIT_SIGNATURE is set: a "Generated with [Continue]"
# body marker and a Co-authored-by trailer with the continue.dev address.
# https://github.com/continuedev/continue/blob/main/extensions/cli/src/systemMessage.ts
# "Continue" is a common English word (and a possible surname), so the
# co-author / sign-off patterns are anchored to the continue.dev address and
# the body marker to its URL; the tool gets no broad name_pattern, so a bare
# "continue" in prose or a human co-author is never flagged.
CONTINUE = KnownAiTool(
    name="Continue",
    patterns=[
        *_identity(
            r"[^<\n]*<noreply@continue\.dev>", "Continue <noreply@continue.dev>"
        ),
        _body_marker(
            r"Generated with \[Continue\]\(https://continue\.dev\)",
            "``Generated with [Continue](https://continue.dev)`` body marker",
        ),
    ],
)

# --- Mistral Vibe ---
# Vibe's system prompt tells the model to end every commit with a signature,
# on unless include_commit_signature = false in config.toml:
# "Generated by Mistral Vibe." and a Co-Authored-By trailer with vibe@mistral.ai.
# https://github.com/mistralai/mistral-vibe/blob/main/vibe/core/system_prompt.py
# The model writes the signature itself, so the name and the address are each
# matched on their own. "Vibe" alone is a common word, so only "Mistral Vibe"
# names the tool.
MISTRAL_VIBE = KnownAiTool(
    name="Mistral Vibe",
    name_pattern=_names(r"mistral[ \t-]?vibe"),
    patterns=[
        *_identity(r"Mistral[ \t]+Vibe[ \t]*(?:<[^>\n]*>)?", "Mistral Vibe"),
        *_identity(r"[^<\n]*<vibe@mistral\.ai>", "... <vibe@mistral.ai>"),
        _body_marker(
            r"^Generated by Mistral Vibe\b", "``Generated by Mistral Vibe`` body marker"
        ),
    ],
)

# --- Qwen Code (Alibaba) ---
# Qwen Code appends "Co-authored-by: Qwen-Coder <qwen-coder@alibabacloud.com>"
# to the commits it makes, on unless the gitCoAuthor.commit setting is off:
# https://github.com/QwenLM/qwen-code/blob/main/packages/core/src/config/config.ts
QWEN_CODE = KnownAiTool(
    name="Qwen Code",
    name_pattern=_names(r"qwen[ \t-]?code|qwen-coder"),
    patterns=[
        *_identity(r"Qwen-Coder[ \t]*(?:<[^>\n]*>)?", "Qwen-Coder"),
        *_identity(
            r"[^<\n]*<qwen-coder@alibabacloud\.com>",
            "... <qwen-coder@alibabacloud.com>",
        ),
    ],
)

# --- Amazon Q Developer ---
# The Amazon Q Developer agent commits through its GitHub App.
AMAZON_Q = KnownAiTool(
    name="Amazon Q Developer",
    name_pattern=_names(r"amazon[ \t]+q(?:[ \t]+developer)?|amazon-q-developer"),
    patterns=[*_app_bot("amazon-q-developer")],
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
    AMP,
    OPENHANDS,
    FACTORY_DROID,
    JULES,
    CONTINUE,
    MISTRAL_VIBE,
    QWEN_CODE,
    AMAZON_Q,
    GENERIC_AI,
]
