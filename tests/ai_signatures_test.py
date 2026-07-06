"""Tests for commit_check.ai_signatures — the AI tool signature database."""

import pytest
from commit_check.ai_signatures import (
    detect_ai_signatures,
    has_ai_signature,
    ALL_KNOWN_TOOLS,
    ALL_PATTERNS,
)


class TestDetectAiSignatures:
    """Tests for detect_ai_signatures()."""

    @pytest.mark.benchmark
    def test_no_signatures_in_clean_commit(self):
        """A clean commit message with no AI references returns empty list."""
        message = (
            "feat: add streaming endpoint\n\nSigned-off-by: Alice <alice@example.com>"
        )
        result = detect_ai_signatures(message)
        assert result == []

    @pytest.mark.benchmark
    def test_claude_co_author_with_noreply_email(self):
        """Co-authored-by: Claude with anthropic noreply is detected."""
        message = (
            "feat: implement feature\n\nCo-authored-by: Claude <noreply@anthropic.com>"
        )
        result = detect_ai_signatures(message)
        assert len(result) >= 1
        assert any(s["tool"] == "Claude Code" for s in result)

    @pytest.mark.benchmark
    def test_claude_code_with_github_noreply(self):
        """Co-authored-by: Claude with GitHub noreply is detected."""
        message = "feat: implement feature\n\nCo-authored-by: Claude <12345+Claude@users.noreply.github.com>"
        result = detect_ai_signatures(message)
        assert len(result) >= 1
        assert any(s["tool"] == "Claude Code" for s in result)

    @pytest.mark.benchmark
    def test_human_claude_with_personal_email_ignored(self):
        """A human named Claude with a personal email is NOT detected."""
        message = "feat: add feature\n\nCo-authored-by: Claude Dubois <claude.dubois@gmail.com>"
        result = detect_ai_signatures(message)
        claude_hits = [s for s in result if s["tool"] == "Claude Code"]
        assert len(claude_hits) == 0

    @pytest.mark.benchmark
    def test_copilot_with_noreply_email(self):
        """Co-authored-by: Copilot with GitHub noreply is detected."""
        message = (
            "fix: resolve bug\n\n"
            "Co-authored-by: Copilot <175728472+Copilot@users.noreply.github.com>"
        )
        result = detect_ai_signatures(message)
        assert len(result) >= 1
        assert any(s["tool"] == "GitHub Copilot" for s in result)

    @pytest.mark.benchmark
    def test_copilot_bare_name(self):
        """Co-authored-by: Copilot (bare, no email) is detected."""
        message = "fix: resolve bug\n\nCo-authored-by: Copilot"
        result = detect_ai_signatures(message)
        assert len(result) >= 1
        assert any(s["tool"] == "GitHub Copilot" for s in result)

    @pytest.mark.benchmark
    def test_kernel_format_with_tool_list(self):
        """Assisted-by with kernel-style tool list is detected."""
        message = (
            "refactor: clean up API\n\n"
            "Assisted-by: Claude:claude-3-opus coccinelle sparse"
        )
        result = detect_ai_signatures(message)
        assert len(result) >= 1
        assert any("Assisted-by" in s["matched_text"] for s in result)

    @pytest.mark.benchmark
    def test_kernel_format_simple(self):
        """Assisted-by with just tool:model is detected."""
        message = "refactor: clean up API\n\nAssisted-by: Claude:claude-sonnet-4"
        result = detect_ai_signatures(message)
        assert len(result) >= 1
        assert any("Assisted-by" in s["matched_text"] for s in result)

    @pytest.mark.benchmark
    def test_multiple_ai_tools_detected(self):
        """Multiple AI tool signatures are all detected."""
        message = (
            "feat: implement feature\n\n"
            "Co-authored-by: Claude <noreply@anthropic.com>\n"
            "Co-authored-by: Copilot <175728472+Copilot@users.noreply.github.com>"
        )
        result = detect_ai_signatures(message)
        tools = {s["tool"] for s in result}
        assert "Claude Code" in tools
        assert "GitHub Copilot" in tools

    @pytest.mark.benchmark
    def test_dedup_matched_text(self):
        """Duplicate matched text is reported only once."""
        message = "feat: add feature\n\nAssisted-by: Claude:claude-sonnet-4"
        result = detect_ai_signatures(message)
        matched_texts = [s["matched_text"] for s in result]
        assert len(matched_texts) == len(set(matched_texts))

    @pytest.mark.benchmark
    def test_human_co_author_not_detected(self):
        """A human Co-authored-by is not flagged."""
        message = "feat: add feature\n\nCo-authored-by: Jane Doe <jane@example.com>"
        result = detect_ai_signatures(message)
        # None of the known AI patterns should match a common human name
        assert len(result) == 0

    @pytest.mark.benchmark
    def test_claude_session_trailer(self):
        """Claude-Session: trailer is detected."""
        message = "feat: update config\n\nClaude-Session: sess_abc123"
        result = detect_ai_signatures(message)
        assert len(result) >= 1
        assert any("Claude-Session" in s["matched_text"] for s in result)

    @pytest.mark.benchmark
    def test_emoji_marker_detected(self):
        """🤖 Generated with Claude marker is detected."""
        message = "feat: add feature\n\n🤖 Generated with Claude Code"
        result = detect_ai_signatures(message)
        assert len(result) >= 1
        assert any("Claude Code" == s["tool"] for s in result)

    @pytest.mark.benchmark
    def test_aider_suffix_pattern(self):
        """Co-authored-by with (aider) suffix is detected."""
        message = (
            "feat: add feature\n\nCo-authored-by: Some Dev (aider) <dev@example.com>"
        )
        result = detect_ai_signatures(message)
        assert len(result) >= 1
        assert any(s["tool"] == "Aider" for s in result)

    @pytest.mark.benchmark
    def test_generic_model_name_detected(self):
        """Model names like claude-sonnet-4 in Co-authored-by are detected."""
        message = (
            "feat: add feature\n\nCo-authored-by: claude-sonnet-4 <bot@example.com>"
        )
        result = detect_ai_signatures(message)
        assert len(result) >= 1
        assert any(s["tool"] == "Generic AI" for s in result)

    @pytest.mark.benchmark
    def test_generic_gpt_model_detected(self):
        """gpt-4-turbo in Co-authored-by is detected."""
        message = "feat: add feature\n\nCo-authored-by: gpt-4-turbo <bot@example.com>"
        result = detect_ai_signatures(message)
        assert len(result) >= 1
        assert any(s["tool"] == "Generic AI" for s in result)

    @pytest.mark.benchmark
    def test_all_known_tools_have_patterns(self):
        """All known tools have at least one pattern."""
        for tool in ALL_KNOWN_TOOLS:
            assert len(tool.patterns) >= 1, f"{tool.name} has no patterns"

    @pytest.mark.benchmark
    def test_all_patterns_compile(self):
        """All patterns in the master registry compile successfully."""
        for regex, tool_name, desc, kind in ALL_PATTERNS:
            assert regex is not None, f"{tool_name}: {desc} has None regex"
            assert kind in ("trailer", "body_marker"), (
                f"{tool_name}: invalid kind {kind}"
            )

    @pytest.mark.benchmark
    def test_kind_field_correct_for_body_marker(self):
        """Body markers have kind='body_marker', not 'trailer'."""
        message = "feat: add feature\n\nGenerated by AI"
        result = detect_ai_signatures(message)
        for r in result:
            if r["description"].startswith("``Generated by AI"):
                assert r["kind"] == "body_marker", (
                    f"Expected body_marker, got {r['kind']}"
                )

    @pytest.mark.benchmark
    def test_kind_field_correct_for_trailer(self):
        """Trailers have kind='trailer'."""
        message = "feat: add feature\n\nCo-authored-by: Claude <noreply@anthropic.com>"
        result = detect_ai_signatures(message)
        for r in result:
            assert r["kind"] == "trailer", f"Expected trailer, got {r['kind']}"


class TestHasAiSignature:
    """Tests for has_ai_signature()."""

    @pytest.mark.benchmark
    def test_clean_message(self):
        """Returns False for a clean commit message."""
        assert has_ai_signature("feat: add feature") is False

    @pytest.mark.benchmark
    def test_with_ai_signature(self):
        """Returns True when AI signature present."""
        assert (
            has_ai_signature(
                "feat: add feature\n\nCo-authored-by: Claude <noreply@anthropic.com>"
            )
            is True
        )

    @pytest.mark.benchmark
    def test_empty_message(self):
        """Returns False for empty message."""
        assert has_ai_signature("") is False


class TestHumanNameFalsePositives:
    """Human co-authors whose names overlap with AI tool/model tokens.

    The generic model-name pattern requires a hyphenated model suffix
    (e.g. ``claude-sonnet-4``), so a bare human first name — even with a
    personal email — must never be flagged.
    """

    @pytest.mark.benchmark
    @pytest.mark.parametrize(
        "trailer",
        [
            "Co-authored-by: Claude <claude.dubois@gmail.com>",
            "Co-authored-by: Gemini Rossi <gemini@rossi.it>",
            "Co-authored-by: gpt <someone@example.com>",
            "Co-authored-by: Claude Monet <claude@monet.fr>",
        ],
    )
    def test_bare_human_name_not_detected(self, trailer):
        """A human co-author is not treated as an AI signature."""
        message = f"feat: add feature\n\n{trailer}"
        assert detect_ai_signatures(message) == []
        assert has_ai_signature(message) is False

    @pytest.mark.benchmark
    @pytest.mark.parametrize(
        "trailer",
        [
            "Co-authored-by: claude-sonnet-4 <bot@example.com>",
            "Co-authored-by: gpt-4-turbo <bot@example.com>",
            "Co-authored-by: gemini-1.5-pro",
        ],
    )
    def test_model_identifier_still_detected(self, trailer):
        """A hyphenated AI model identifier is still caught by Generic AI."""
        message = f"feat: add feature\n\n{trailer}"
        assert has_ai_signature(message) is True


class TestSignatureDatabase:
    """Tests for the structure and completeness of the signature database."""

    @pytest.mark.benchmark
    def test_all_tools_have_unique_names(self):
        """All known tools have unique display names."""
        names = [t.name for t in ALL_KNOWN_TOOLS]
        assert len(names) == len(set(names))

    @pytest.mark.benchmark
    def test_all_patterns_have_description(self):
        """All patterns have a non-empty description."""
        for regex, tool_name, desc, kind in ALL_PATTERNS:
            assert desc, f"Pattern for {tool_name} is missing a description"

    @pytest.mark.benchmark
    def test_claude_code_variant_detection(self):
        """Various Claude Code trailer formats are detected."""
        variants = [
            "Co-authored-by: Claude",
            "Co-authored-by: Claude <noreply@anthropic.com>",
            "Co-authored-by: Claude Code <noreply@anthropic.com>",
            "Assisted-by: Claude:claude-sonnet-4-20250514",
            "Assisted-by: Claude:claude-3-opus coccinelle sparse",
            "Claude-Session: sess_abc123",
            "Claude-Workflow: workflow_xyz",
        ]
        for variant in variants:
            message = f"feat: add feature\n\n{variant}"
            result = detect_ai_signatures(message)
            assert len(result) >= 1, f"Failed to detect: {variant}"

    @pytest.mark.benchmark
    def test_generic_ai_catch_all(self):
        """Assisted-by with any AI agent is caught by Generic AI."""
        message = "feat: update code\n\nAssisted-by: gpt-4:openai"
        result = detect_ai_signatures(message)
        assert len(result) >= 1

    @pytest.mark.benchmark
    def test_human_name_not_detected(self):
        """Common human names that could overlap with AI tool names."""
        # Devin is both a human name and an AI tool name
        message = (
            "feat: add feature\n\nCo-authored-by: Devin Booker <devin.booker@gmail.com>"
        )
        result = detect_ai_signatures(message)
        devin_hits = [s for s in result if s["tool"] == "Devin"]
        # With a personal email, Devin should NOT be detected
        assert len(devin_hits) == 0
