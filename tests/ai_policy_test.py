"""The ``disclose`` policy: what a message says about AI, and how to fix it."""

import pytest

from commit_check.ai_policy import analyze, propose_fix

ACCEPTED = ["Assisted-by", "Generated-by"]

CLAUDE_STAMP = "🤖 Generated with [Claude Code](https://claude.com/claude-code)"
CLAUDE_CO_AUTHOR = "Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
COPILOT_CO_AUTHOR = (
    "Co-authored-by: Copilot <175728472+Copilot@users.noreply.github.com>"
)
HUMAN_SIGNOFF = "Signed-off-by: Jane Dev <jane@example.com>"


def fix_for(message, accepted=ACCEPTED, pattern=""):
    return propose_fix(message, analyze(message, accepted, pattern), accepted, pattern)


class TestAnalyze:
    def test_a_clean_message_is_compliant(self):
        report = analyze("feat: add x\n\nBody.\n\n" + HUMAN_SIGNOFF, ACCEPTED)
        assert report.compliant
        assert not report.disclosed
        assert report.evidence == []

    @pytest.mark.parametrize(
        "trailer",
        [
            "Assisted-by: LLM coccinelle sparse",
            "Assisted-by: ChatGPTv5",
            "Assisted-by: claude-code/claude-opus-4",
            "Generated-by: GitHub Copilot",
            "assisted-by: lower-case key",
        ],
    )
    def test_an_accepted_disclosure_is_compliant(self, trailer):
        report = analyze(f"fix: x\n\n{trailer}\n{HUMAN_SIGNOFF}", ACCEPTED)
        assert report.disclosed
        assert report.compliant
        assert [d.line for d in report.disclosures] == [trailer]

    def test_a_vendor_co_author_line_is_undisclosed_and_a_co_author(self):
        report = analyze(f"fix: x\n\n{CLAUDE_STAMP}\n\n{CLAUDE_CO_AUTHOR}", ACCEPTED)
        assert report.undisclosed
        assert [s["matched_text"] for s in report.co_author_lines] == [CLAUDE_CO_AUTHOR]
        assert [s["tool"] for s in report.stamps] == ["Claude Code"]
        assert not report.compliant

    def test_a_disclosed_tool_credited_as_co_author_is_only_a_co_author(self):
        report = analyze(
            "fix: x\n\nAssisted-by: Claude Code\nCo-authored-by: Claude <noreply@anthropic.com>",
            ACCEPTED,
        )
        assert report.disclosed
        assert not report.undisclosed
        assert len(report.co_author_lines) == 1

    def test_an_ai_sign_off_is_a_sign_off(self):
        report = analyze(
            "fix: x\n\nAssisted-by: LLM\nSigned-off-by: Claude <noreply@anthropic.com>",
            ACCEPTED,
        )
        assert report.disclosed
        assert [s["tool"] for s in report.signoff_lines] == ["Claude Code"]
        assert not report.compliant

    def test_a_disclosure_under_another_trailer_is_undisclosed(self):
        report = analyze("fix: x\n\nGenerated-by: GitHub Copilot", ["Assisted-by"])
        assert report.undisclosed
        assert [s["trailer"] for s in report.other_disclosures] == ["Generated-by"]

    def test_a_stamp_alone_is_undisclosed(self):
        report = analyze(f"fix: x\n\n{CLAUDE_STAMP}", ACCEPTED)
        assert report.undisclosed
        assert report.co_author_lines == report.signoff_lines == []

    def test_an_empty_disclosure_is_malformed(self):
        report = analyze("fix: x\n\nAssisted-by:", ACCEPTED)
        assert not report.disclosed
        assert [(d.key, d.problem) for d in report.malformed] == [
            ("Assisted-by", "empty")
        ]
        assert not report.compliant

    def test_the_pattern_is_matched_from_the_start_of_the_value(self):
        agent_model = r"^\S+/\S+$"
        good = analyze(
            "fix: x\n\nAssisted-by: claude-code/claude-opus-4", ACCEPTED, agent_model
        )
        assert good.compliant
        bad = analyze(
            "fix: x\n\nAssisted-by: LLM coccinelle sparse", ACCEPTED, agent_model
        )
        assert [(d.value, d.problem) for d in bad.malformed] == [
            ("LLM coccinelle sparse", "pattern")
        ]
        assert not bad.compliant

    def test_one_good_disclosure_is_enough(self):
        """A malformed second trailer still fails, but the message is disclosed."""
        report = analyze("fix: x\n\nAssisted-by: LLM\nGenerated-by:", ACCEPTED)
        assert report.disclosed
        assert len(report.malformed) == 1


class TestCoAuthorAsDisclosure:
    """A project that lists Co-authored-by accepts the tool as a co-author."""

    ACCEPTED = ["Assisted-by", "Co-authored-by"]

    def test_an_ai_co_author_line_is_the_disclosure(self):
        report = analyze(f"fix: x\n\n{COPILOT_CO_AUTHOR}", self.ACCEPTED)
        assert report.disclosed
        assert report.co_author_lines == []
        assert report.compliant

    def test_a_human_co_author_is_not_a_disclosure(self):
        report = analyze(
            "fix: x\n\nCo-authored-by: Jane Doe <jane@example.com>", self.ACCEPTED
        )
        assert not report.disclosed
        assert report.compliant  # no AI shows, nothing to disclose

    def test_a_stamp_next_to_a_human_co_author_is_still_undisclosed(self):
        report = analyze(
            f"fix: x\n\n{CLAUDE_STAMP}\n\nCo-authored-by: Jane Doe <jane@example.com>",
            self.ACCEPTED,
        )
        assert report.undisclosed

    def test_co_developed_by_is_not_covered_by_co_authored_by(self):
        report = analyze(
            "fix: x\n\nCo-developed-by: Claude <noreply@anthropic.com>", self.ACCEPTED
        )
        assert not report.disclosed
        assert len(report.co_author_lines) == 1


class TestProposeFix:
    def test_the_co_author_line_becomes_the_disclosure(self):
        message = f"fix: x\n\n{CLAUDE_STAMP}\n\n{CLAUDE_CO_AUTHOR}"
        assert fix_for(message) == (
            f"fix: x\n\n{CLAUDE_STAMP}\n\nAssisted-by: Claude Opus 4.5"
        )

    def test_the_fix_is_written_with_the_first_accepted_trailer(self):
        message = f"fix: x\n\n{COPILOT_CO_AUTHOR}"
        assert fix_for(message, ["Generated-by", "Assisted-by"]) == (
            "fix: x\n\nGenerated-by: Copilot"
        )

    def test_a_disclosed_tool_credited_as_co_author_just_loses_the_credit(self):
        message = (
            "fix: x\n\nAssisted-by: Claude Code\n"
            "Co-authored-by: Claude <noreply@anthropic.com>\n"
            f"{HUMAN_SIGNOFF}"
        )
        assert (
            fix_for(message) == f"fix: x\n\nAssisted-by: Claude Code\n{HUMAN_SIGNOFF}"
        )

    def test_an_ai_sign_off_becomes_the_disclosure(self):
        message = "fix: x\n\nSigned-off-by: Claude <noreply@anthropic.com>"
        assert fix_for(message) == "fix: x\n\nAssisted-by: Claude"

    def test_another_trailer_keeps_its_value_under_the_accepted_key(self):
        message = "fix: x\n\nGenerated-by: GitHub Copilot"
        assert (
            fix_for(message, ["Assisted-by"]) == "fix: x\n\nAssisted-by: GitHub Copilot"
        )

    def test_a_stamp_alone_gets_the_disclosure_appended(self):
        assert fix_for(f"fix: x\n\n{CLAUDE_STAMP}") == (
            f"fix: x\n\n{CLAUDE_STAMP}\n\nAssisted-by: Claude Code"
        )

    def test_the_appended_disclosure_joins_an_existing_trailer_block(self):
        message = f"fix: x\n\n{CLAUDE_STAMP}\n\n{HUMAN_SIGNOFF}"
        assert fix_for(message) == (
            f"fix: x\n\n{CLAUDE_STAMP}\n\n{HUMAN_SIGNOFF}\nAssisted-by: Claude Code"
        )

    def test_two_tools_give_two_disclosures(self):
        message = f"fix: x\n\n{CLAUDE_CO_AUTHOR}\n{COPILOT_CO_AUTHOR}"
        assert fix_for(message) == (
            "fix: x\n\nAssisted-by: Claude Opus 4.5\nAssisted-by: Copilot"
        )

    def test_one_tool_credited_twice_is_disclosed_once(self):
        message = (
            "fix: x\n\nCo-authored-by: Claude <noreply@anthropic.com>\n"
            "Signed-off-by: Claude <noreply@anthropic.com>"
        )
        assert fix_for(message) == "fix: x\n\nAssisted-by: Claude"

    def test_a_compliant_message_has_no_fix(self):
        assert fix_for("fix: x\n\nAssisted-by: LLM") is None
        assert fix_for("fix: x") is None

    def test_a_malformed_disclosure_is_not_rewritten(self):
        assert fix_for("fix: x\n\nAssisted-by:") is None
        assert fix_for("fix: x\n\nAssisted-by: LLM", pattern=r"^\S+/\S+$") is None

    def test_a_fix_that_would_fail_the_pattern_is_withheld(self):
        message = f"fix: x\n\n{CLAUDE_CO_AUTHOR}"
        assert fix_for(message, pattern=r"^\S+/\S+$") is None

    def test_a_generic_stamp_names_no_tool_to_disclose(self):
        assert fix_for("fix: x\n\nGenerated by AI") is None

    def test_every_fix_complies(self):
        messages = [
            f"fix: x\n\n{CLAUDE_STAMP}\n\n{CLAUDE_CO_AUTHOR}",
            f"fix: x\n\n{COPILOT_CO_AUTHOR}",
            "fix: x\n\nSigned-off-by: Claude <noreply@anthropic.com>",
            f"fix: x\n\n{CLAUDE_STAMP}\n\n{HUMAN_SIGNOFF}",
            "fix: x\n\nGenerated-by: GitHub Copilot",
        ]
        for message in messages:
            fixed = fix_for(message, ["Assisted-by"])
            assert fixed, message
            assert analyze(fixed, ["Assisted-by"]).compliant, fixed
