"""The commit message is quoted once above the rules it failed."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from commit_check.engine import ValidationContext, ValidationEngine
from commit_check.rule_builder import RuleBuilder
from commit_check.rules_catalog import MESSAGE_CHECKS
from commit_check.util import print_quoted_message

AI_MESSAGE = "Added the login page\n\nCo-Authored-By: Claude <noreply@anthropic.com>\n"


def run(config: dict, message: str, **context) -> None:
    # The message rules only: the branch, tag and author rules read git.
    rules = [
        rule
        for rule in RuleBuilder(config).build_all_rules()
        if rule.check in MESSAGE_CHECKS or rule.check.startswith("ai_")
    ]
    engine = ValidationEngine(rules)
    with patch(
        "commit_check.engine.SignoffValidator._resolve_author_identity",
        return_value=("Dev", "dev@example.com"),
    ):
        engine.validate_all(ValidationContext(stdin_text=message, **context))


@pytest.fixture
def no_colour(monkeypatch):
    for module in ("commit_check.util", "commit_check.engine"):
        for name in ("RED", "GREEN", "DIM", "BOLD", "YELLOW", "RESET_COLOR"):
            monkeypatch.setattr(f"{module}.{name}", "", raising=False)


class TestQuotedMessage:
    def test_the_message_is_printed_once(self, capsys, no_colour):
        run({"commit": {"subject_imperative": True}}, "added x\n")
        out, _ = capsys.readouterr()
        assert out.count("added x") == 1
        assert "  │ added x\n" in out
        assert "✖ CC001 message failed\n" in out
        assert "✖ CC003 subject-imperative failed\n" in out

    def test_a_single_failure_keeps_its_value_on_its_line(self, capsys, no_colour):
        run({"commit": {}}, "added x\n")
        out, _ = capsys.readouterr()
        assert "│" not in out
        assert "✖ CC001 message failed: added x" in out

    def test_compact_output_is_unchanged(self, capsys, no_colour):
        run({"commit": {"subject_imperative": True}}, "added x\n", compact=True)
        out, _ = capsys.readouterr()
        assert "│" not in out
        assert "[FAIL] CC001 message: added x" in out

    def test_an_ai_rule_keeps_its_own_value_and_marks_the_trailer(
        self, capsys, monkeypatch
    ):
        monkeypatch.setattr("commit_check.util.RED", "<r>")
        monkeypatch.setattr("commit_check.util.RESET_COLOR", "</>")
        run(
            {"commit": {"subject_imperative": True, "ai_attribution": "forbid"}},
            AI_MESSAGE,
        )
        out, _ = capsys.readouterr()
        assert out.count("Added the login page") == 1
        assert "<r>Added the login page</>" in out
        assert "<r>Co-Authored-By: Claude <noreply@anthropic.com></>" in out
        assert "failed: <r>Claude Code</>" in out

    def test_a_missing_sign_off_is_shown_where_it_goes(self, capsys, no_colour):
        run(
            {"commit": {"subject_imperative": True, "require_signed_off_by": True}},
            "added x\n",
        )
        out, _ = capsys.readouterr()
        assert "  │ Signed-off-by: Dev <dev@example.com>  ← missing\n" in out
        assert "✖ CC012 require-signed-off-by failed\n" in out

    def test_a_good_subject_is_not_marked(self, capsys, monkeypatch):
        monkeypatch.setattr("commit_check.util.RED", "<r>")
        monkeypatch.setattr("commit_check.util.RESET_COLOR", "</>")
        run(
            {"commit": {"require_signed_off_by": True, "require_body": True}},
            "feat: add x\n",
        )
        out, _ = capsys.readouterr()
        assert " feat: add x\n" in out
        assert "<r>feat: add x" not in out


class TestPrintQuotedMessage:
    def test_a_long_body_is_folded_but_marked_lines_stay(self, capsys, no_colour):
        lines = [f"line {n}" for n in range(30)]
        print_quoted_message("\n".join(lines), marked={25})
        out, _ = capsys.readouterr()
        assert "│ line 11\n" in out
        assert "│ line 12\n" not in out
        assert "│ … 13 more\n" in out
        assert "│ line 25\n" in out
        assert "│ … 4 more\n" in out

    def test_trailing_blank_lines_are_dropped(self, capsys, no_colour):
        print_quoted_message("feat: x\n\n\n")
        out, _ = capsys.readouterr()
        assert out == "  │ feat: x\n\n"
