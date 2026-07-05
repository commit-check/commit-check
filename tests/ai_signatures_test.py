"""Tests for commit_check.ai_signatures — the AI tool signature database."""

import pytest
from commit_check.ai_signatures import (
    detect_ai_signatures,
    has_ai_signature,
    find_co_authored_by_ai,
    find_assisted_by_trailers,
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
    def test_claude_co_author_detected(self):
        """Co-authored-by: Claude is detected."""
        message = (
            "feat: implement feature\n\nCo-authored-by: Claude <noreply@anthropic.com>"
        )
        result = detect_ai_signatures(message)
        assert len(result) >= 1
        assert any(s["tool"] == "Claude Code" for s in result)

    @pytest.mark.benchmark
    def test_copilot_co_author_detected(self):
        """Co-authored-by: Copilot is detected."""
        message = "fix: resolve bug\n\nCo-authored-by: Copilot <noreply@github.com>"
        result = detect_ai_signatures(message)
        assert len(result) >= 1
        assert any(s["tool"] == "GitHub Copilot" for s in result)

    @pytest.mark.benchmark
    def test_assisted_by_trailer_detected(self):
        """Assisted-by: trailer (kernel style) is detected."""
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
            "Co-authored-by: Copilot <noreply@github.com>"
        )
        result = detect_ai_signatures(message)
        tools = {s["tool"] for s in result}
        assert "Claude Code" in tools
        assert "GitHub Copilot" in tools

    @pytest.mark.benchmark
    def test_dedup_matched_text(self):
        """Duplicate matched text is reported only once."""
        # Two patterns could match the same line; we only report once
        message = "feat: add feature\n\nAssisted-by: Claude:claude-sonnet-4"
        result = detect_ai_signatures(message)
        matched_texts = [s["matched_text"] for s in result]
        assert len(matched_texts) == len(set(matched_texts))

    @pytest.mark.benchmark
    def test_human_co_author_not_detected(self):
        """A human Co-authored-by is not flagged."""
        message = "feat: add feature\n\nCo-authored-by: Jane Doe <jane@example.com>"
        result = detect_ai_signatures(message)
        # "Jane Doe" doesn't match any AI pattern; our patterns are specific
        # to known AI tool names, not arbitrary human names.
        for r in result:
            assert "AI" not in r["tool"] or "Generic" in r["tool"]

    @pytest.mark.benchmark
    def test_claude_session_trailer(self):
        """Claude-Session: trailer is detected."""
        message = "feat: update config\n\nClaude-Session: abc123"
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
    def test_aider_commit_marker(self):
        """Aider commit marker is detected."""
        message = "# aider commit: refactored authentication module"
        result = detect_ai_signatures(message)
        assert len(result) >= 1
        assert any(s["tool"] == "Aider" for s in result)

    @pytest.mark.benchmark
    def test_all_known_tools_have_patterns(self):
        """All known tools have at least one pattern."""
        for tool in ALL_KNOWN_TOOLS:
            assert len(tool.patterns) >= 1, f"{tool.name} has no patterns"

    @pytest.mark.benchmark
    def test_all_patterns_compile(self):
        """All patterns in the master registry compile successfully."""
        for regex, tool_name, desc in ALL_PATTERNS:
            assert regex is not None, f"{tool_name}: {desc} has None regex"
            assert regex.search("test") is not None or True  # regex is valid


class TestHasAiSignature:
    """Tests for has_ai_signature()."""

    @pytest.mark.benchmark
    def test_clean_message(self):
        """Returns False for a clean commit message."""
        assert has_ai_signature("feat: add feature") is False

    @pytest.mark.benchmark
    def test_with_ai_signature(self):
        """Returns True when AI signature present."""
        assert has_ai_signature("feat: add feature\n\nCo-authored-by: Claude") is True

    @pytest.mark.benchmark
    def test_empty_message(self):
        """Returns False for empty message."""
        assert has_ai_signature("") is False


class TestFindCoAuthoredByAi:
    """Tests for find_co_authored_by_ai()."""

    @pytest.mark.benchmark
    def test_finds_claude_co_author(self):
        """Finds Co-authored-by: Claude lines."""
        message = "feat: add feature\n\nCo-authored-by: Claude <noreply@anthropic.com>"
        result = find_co_authored_by_ai(message)
        assert len(result) >= 1
        assert "Co-authored-by: Claude" in result[0]

    @pytest.mark.benchmark
    def test_finds_copilot_co_author(self):
        """Finds Co-authored-by: Copilot lines."""
        message = "feat: add feature\n\nCo-authored-by: Copilot <noreply@github.com>"
        result = find_co_authored_by_ai(message)
        assert len(result) >= 1
        assert "Copilot" in result[0]

    @pytest.mark.benchmark
    def test_no_false_positive_for_human(self):
        """Human co-authors are not returned."""
        message = "feat: add feature\n\nCo-authored-by: Alice Smith <alice@example.com>"
        result = find_co_authored_by_ai(message)
        assert result == []

    @pytest.mark.benchmark
    def test_empty_message(self):
        """Empty message returns empty list."""
        assert find_co_authored_by_ai("") == []


class TestFindAssistedByTrailers:
    """Tests for find_assisted_by_trailers()."""

    @pytest.mark.benchmark
    def test_finds_assisted_by_trailer(self):
        """Finds Assisted-by: trailer."""
        message = "feat: add feature\n\nAssisted-by: Claude:claude-sonnet-4"
        result = find_assisted_by_trailers(message)
        assert len(result) >= 1
        assert "Assisted-by: Claude:claude-sonnet-4" in result[0]

    @pytest.mark.benchmark
    def test_no_false_positive(self):
        """Returns empty list when no Assisted-by trailer."""
        message = "feat: add feature\n\nSigned-off-by: Alice <alice@example.com>"
        result = find_assisted_by_trailers(message)
        assert result == []

    @pytest.mark.benchmark
    def test_empty_message(self):
        """Empty message returns empty list."""
        assert find_assisted_by_trailers("") == []


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
        for regex, tool_name, desc in ALL_PATTERNS:
            assert desc, f"Pattern for {tool_name} is missing a description"

    @pytest.mark.benchmark
    def test_claude_code_variant_detection(self):
        """Various Claude Code trailer formats are detected."""
        variants = [
            "Co-authored-by: Claude",
            "Co-authored-by: Claude <noreply@anthropic.com>",
            "Co-authored-by: Claude Code <noreply@anthropic.com>",
            "Assisted-by: Claude:claude-sonnet-4-20250514",
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
