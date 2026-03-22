"""Tests for commit_check.fixer module — targeting 100% line coverage."""

from __future__ import annotations

from unittest.mock import patch

from commit_check.fixer import (
    CommitFixer,
    _to_imperative,
)


# ---------------------------------------------------------------------------
# _to_imperative — unit tests for every branch in the verb algorithm
# ---------------------------------------------------------------------------


class TestToImperative:
    def test_past_to_imperative_table_simplified(self):
        assert _to_imperative("simplified") == "simplify"

    def test_past_to_imperative_table_applied(self):
        assert _to_imperative("applied") == "apply"

    def test_past_to_imperative_table_modified(self):
        assert _to_imperative("modified") == "modify"

    def test_past_to_imperative_table_unified(self):
        assert _to_imperative("unified") == "unify"

    def test_past_to_imperative_table_verified(self):
        assert _to_imperative("verified") == "verify"

    def test_past_to_imperative_table_specified(self):
        assert _to_imperative("specified") == "specify"

    def test_past_to_imperative_table_classified(self):
        assert _to_imperative("classified") == "classify"

    def test_past_to_imperative_table_notified(self):
        assert _to_imperative("notified") == "notify"

    def test_past_to_imperative_case_insensitive(self):
        # Table lookup works on lowercased form
        assert _to_imperative("Simplified") == "simplify"

    # -ed suffix (step 3b)
    def test_ed_suffix_fixed(self):
        assert _to_imperative("fixed") == "fix"

    def test_ed_suffix_added(self):
        assert _to_imperative("added") == "add"

    def test_ed_suffix_removed(self):
        result = _to_imperative("removed")
        # "remov" is not in IMPERATIVES, so should fall through and return None
        assert result is None

    def test_ed_suffix_too_short_no_match(self):
        # word where stem after stripping -ed is < 3 chars ("xed" -> stem="x", len=1 < 3)
        assert _to_imperative("xed") is None

    def test_ed_suffix_stem_not_in_imperatives(self):
        # stem length >=3 but not an imperative verb
        assert _to_imperative("frobled") is None

    # -ing suffix (step 3c) — direct IMPERATIVES hit
    def test_ing_suffix_adding(self):
        assert _to_imperative("adding") == "add"

    def test_ing_suffix_fixing(self):
        assert _to_imperative("fixing") == "fix"

    # -ing suffix (step 3c) — doubled consonant de-gemination
    def test_ing_doubled_consonant_running(self):
        assert _to_imperative("running") == "run"

    def test_ing_doubled_consonant_getting(self):
        # "getting" -> stem "gett" -> undoubled "get"
        assert _to_imperative("getting") == "get"

    def test_ing_too_short_skips(self):
        # Too short for -ing rule: len <= 5
        assert _to_imperative("ring") is None

    def test_ing_doubled_consonant_undoubled_not_in_imperatives(self):
        # doubled consonant but result not an imperative
        assert _to_imperative("fuzzing") is None

    # -es suffix (step 3d)
    def test_es_suffix_fixes(self):
        assert _to_imperative("fixes") == "fix"

    def test_es_suffix_adds(self):
        assert _to_imperative("adds") == "add"

    def test_es_suffix_not_in_imperatives(self):
        assert _to_imperative("frobles") is None

    # -s suffix (step 3d)
    def test_s_suffix_adds(self):
        # Already covered by -es but test plain -s
        assert _to_imperative("updates") is not None  # "update" or via -es

    def test_s_suffix_too_short(self):
        # len <= 3 → skip -s rule
        assert _to_imperative("ads") is None

    def test_no_rule_matches(self):
        assert _to_imperative("xyzqrst") is None

    def test_unknown_word_returns_none(self):
        assert _to_imperative("blorp") is None


# ---------------------------------------------------------------------------
# CommitFixer.fix() — allow_wip_commits transform
# ---------------------------------------------------------------------------


class TestFixWip:
    def setup_method(self):
        self.fixer = CommitFixer()

    def test_wip_stripped_nonempty(self):
        result = self.fixer.fix("WIP: add feature", ["allow_wip_commits"])
        assert result.fixed_message == "add feature"
        assert "allow_wip_commits" in result.fixed
        assert not result.unfixable

    def test_wip_stripped_uppercase(self):
        result = self.fixer.fix("WIP: fix bug", ["allow_wip_commits"])
        assert result.fixed_message == "fix bug"

    def test_wip_stripped_mixed_case(self):
        # "wip:" is matched case-insensitively by .upper()
        result = self.fixer.fix("wip: something", ["allow_wip_commits"])
        assert result.fixed_message == "something"
        assert "allow_wip_commits" in result.fixed

    def test_wip_prefix_yields_empty_body(self):
        result = self.fixer.fix("WIP:   ", ["allow_wip_commits"])
        assert result.fixed_message == "WIP:   "  # unchanged
        assert not result.fixed
        assert any("allow_wip_commits" in c for c, _ in result.unfixable)

    def test_wip_not_present_noop(self):
        result = self.fixer.fix("feat: add thing", ["allow_wip_commits"])
        # No WIP prefix → transform returns (message, None) → fix applied (no-op)
        assert result.fixed_message == "feat: add thing"
        assert "allow_wip_commits" in result.fixed

    def test_wip_multiline_body_preserved(self):
        msg = "WIP: fix bug\n\nThis is the body."
        result = self.fixer.fix(msg, ["allow_wip_commits"])
        assert result.fixed_message == "fix bug\n\nThis is the body."


# ---------------------------------------------------------------------------
# CommitFixer.fix() — subject_imperative transform
# ---------------------------------------------------------------------------


class TestFixImperative:
    def setup_method(self):
        self.fixer = CommitFixer()

    def test_fixed_verb_plain(self):
        result = self.fixer.fix("fixed bug", ["subject_imperative"])
        assert result.fixed_message == "fix bug"
        assert "subject_imperative" in result.fixed

    def test_past_tense_table_plain(self):
        result = self.fixer.fix("simplified logic", ["subject_imperative"])
        assert result.fixed_message == "simplify logic"

    def test_conventional_prefix_preserved(self):
        result = self.fixer.fix("feat: fixed bug", ["subject_imperative"])
        assert result.fixed_message == "feat: fix bug"

    def test_conventional_breaking_change_prefix(self):
        result = self.fixer.fix("feat!: fixed bug", ["subject_imperative"])
        assert result.fixed_message == "feat!: fix bug"

    def test_conventional_scoped_prefix(self):
        result = self.fixer.fix("fix(scope): added thing", ["subject_imperative"])
        assert result.fixed_message == "fix(scope): add thing"

    def test_capitalization_preserved_after_fix(self):
        # "Fixed" → "Fix" (not "fix")
        result = self.fixer.fix("Fixed bug in login", ["subject_imperative"])
        assert result.fixed_message == "Fix bug in login"

    def test_ing_suffix_fix(self):
        result = self.fixer.fix("Adding new feature", ["subject_imperative"])
        assert result.fixed_message == "Add new feature"

    def test_unknown_verb_unfixable(self):
        result = self.fixer.fix("xyzqrst feature", ["subject_imperative"])
        assert not result.fixed
        assert any("subject_imperative" in c for c, _ in result.unfixable)
        assert "unknown verb form" in result.unfixable[0][1]

    def test_no_first_word_match_unfixable(self):
        # Subject starting with a non-word character
        result = self.fixer.fix("!!! broken", ["subject_imperative"])
        assert not result.fixed

    def test_multiline_body_unchanged(self):
        msg = "fixed bug\n\nThis explains why."
        result = self.fixer.fix(msg, ["subject_imperative"])
        assert result.fixed_message == "fix bug\n\nThis explains why."

    def test_adding_doubled_consonant(self):
        result = self.fixer.fix("running tests", ["subject_imperative"])
        assert result.fixed_message == "run tests"


# ---------------------------------------------------------------------------
# CommitFixer.fix() — subject_capitalized transform
# ---------------------------------------------------------------------------


class TestFixCapitalized:
    def setup_method(self):
        self.fixer = CommitFixer()

    def test_conventional_lowercase_description(self):
        result = self.fixer.fix("feat: fix the bug", ["subject_capitalized"])
        assert result.fixed_message == "feat: Fix the bug"
        assert "subject_capitalized" in result.fixed

    def test_plain_lowercase(self):
        result = self.fixer.fix("fix the bug", ["subject_capitalized"])
        assert result.fixed_message == "Fix the bug"

    def test_already_capitalized_conventional(self):
        # No change needed — still counts as "fixed" (transform applied, message same)
        result = self.fixer.fix("feat: Fix the bug", ["subject_capitalized"])
        assert result.fixed_message == "feat: Fix the bug"
        assert "subject_capitalized" in result.fixed

    def test_empty_description_after_prefix(self):
        # "feat: " with empty description → guard fires → no-op
        result = self.fixer.fix("feat:", ["subject_capitalized"])
        assert "subject_capitalized" in result.fixed  # still counted as fixed (no-op)

    def test_empty_plain_subject(self):
        result = self.fixer.fix("", ["subject_capitalized"])
        assert "subject_capitalized" in result.fixed

    def test_scoped_conventional(self):
        result = self.fixer.fix("fix(auth): resolve issue", ["subject_capitalized"])
        assert result.fixed_message == "fix(auth): Resolve issue"

    def test_multiline_body_unchanged(self):
        msg = "feat: fix bug\n\nBody here."
        result = self.fixer.fix(msg, ["subject_capitalized"])
        assert result.fixed_message == "feat: Fix bug\n\nBody here."


# ---------------------------------------------------------------------------
# CommitFixer.fix() — require_signed_off_by transform
# ---------------------------------------------------------------------------


class TestFixSignoff:
    def setup_method(self):
        self.fixer = CommitFixer()

    def test_signoff_appended_single_line(self):
        with patch("commit_check.fixer.cmd_output") as mock_cmd:
            mock_cmd.side_effect = ["Jane Doe", "jane@example.com"]
            result = self.fixer.fix("fix bug", ["require_signed_off_by"])
        assert "Signed-off-by: Jane Doe <jane@example.com>" in result.fixed_message
        assert "require_signed_off_by" in result.fixed

    def test_signoff_double_blank_separator(self):
        with patch("commit_check.fixer.cmd_output") as mock_cmd:
            mock_cmd.side_effect = ["Jane Doe", "jane@example.com"]
            result = self.fixer.fix("fix bug\n\nBody text.", ["require_signed_off_by"])
        assert result.fixed_message.endswith(
            "Body text.\n\nSigned-off-by: Jane Doe <jane@example.com>"
        )

    def test_signoff_unfixable_no_name(self):
        with patch("commit_check.fixer.cmd_output") as mock_cmd:
            mock_cmd.side_effect = ["", "jane@example.com"]
            result = self.fixer.fix("fix bug", ["require_signed_off_by"])
        assert not result.fixed
        assert any("require_signed_off_by" in c for c, _ in result.unfixable)
        assert "git user identity not configured" in result.unfixable[0][1]

    def test_signoff_unfixable_no_email(self):
        with patch("commit_check.fixer.cmd_output") as mock_cmd:
            mock_cmd.side_effect = ["Jane Doe", ""]
            result = self.fixer.fix("fix bug", ["require_signed_off_by"])
        assert not result.fixed
        assert any("require_signed_off_by" in c for c, _ in result.unfixable)


# ---------------------------------------------------------------------------
# CommitFixer.fix() — multi-transform ordering
# ---------------------------------------------------------------------------


class TestMultiTransform:
    def setup_method(self):
        self.fixer = CommitFixer()

    def test_wip_strip_then_imperative(self):
        # "WIP: fixed bug" → strip WIP → "fixed bug" → fix tense → "fix bug"
        result = self.fixer.fix(
            "WIP: fixed bug", ["allow_wip_commits", "subject_imperative"]
        )
        assert result.fixed_message == "fix bug"
        assert "allow_wip_commits" in result.fixed
        assert "subject_imperative" in result.fixed

    def test_imperative_then_capitalized(self):
        # "feat: fixed bug" → fix tense → "feat: fix bug" → capitalize → "feat: Fix bug"
        result = self.fixer.fix(
            "feat: fixed bug",
            ["subject_imperative", "subject_capitalized"],
        )
        assert result.fixed_message == "feat: Fix bug"

    def test_multiline_body_preserved_across_transforms(self):
        msg = "feat: fixed bug\n\nThis is the explanation."
        result = self.fixer.fix(msg, ["subject_imperative", "subject_capitalized"])
        assert result.fixed_message == "feat: Fix bug\n\nThis is the explanation."

    def test_all_four_transforms(self):
        with patch("commit_check.fixer.cmd_output") as mock_cmd:
            mock_cmd.side_effect = ["Jane Doe", "jane@example.com"]
            msg = "WIP: fixed bug"
            result = self.fixer.fix(
                msg,
                [
                    "allow_wip_commits",
                    "subject_imperative",
                    "subject_capitalized",
                    "require_signed_off_by",
                ],
            )
        assert result.fixed_message.startswith("Fix bug")
        assert "Signed-off-by: Jane Doe <jane@example.com>" in result.fixed_message
        assert len(result.fixed) == 4


# ---------------------------------------------------------------------------
# CommitFixer.fix() — unfixable paths
# ---------------------------------------------------------------------------


class TestUnfixablePaths:
    def setup_method(self):
        self.fixer = CommitFixer()

    def test_subject_max_length_unfixable(self):
        result = self.fixer.fix("a" * 80, ["subject_max_length"])
        assert not result.fixed
        assert any("subject_max_length" in c for c, _ in result.unfixable)
        assert "shorten manually" in result.unfixable[0][1]

    def test_subject_min_length_unfixable(self):
        result = self.fixer.fix("x", ["subject_min_length"])
        assert not result.fixed
        assert "expand manually" in result.unfixable[0][1]

    def test_require_body_unfixable(self):
        result = self.fixer.fix("fix bug", ["require_body"])
        assert not result.fixed
        assert "body required" in result.unfixable[0][1]

    def test_allow_merge_commits_unfixable(self):
        result = self.fixer.fix("Merge branch 'main'", ["allow_merge_commits"])
        assert not result.fixed
        assert "cannot undo commit type" in result.unfixable[0][1]

    def test_allow_fixup_commits_unfixable(self):
        result = self.fixer.fix("fixup! fix bug", ["allow_fixup_commits"])
        assert not result.fixed
        assert "fixup" in result.unfixable[0][1]

    def test_message_unfixable(self):
        result = self.fixer.fix("whatever", ["message"])
        assert not result.fixed
        assert "deferred" in result.unfixable[0][1]

    def test_unknown_check_silently_skipped(self):
        # Unknown check name not in _TRANSFORM_ORDER falls through to unfixable-or-skip
        result = self.fixer.fix("fix bug", ["totally_unknown_check"])
        # Not in _TRANSFORM_ORDER → reported as unfixable with generic reason
        assert not result.fixed
        assert any("totally_unknown_check" in c for c, _ in result.unfixable)

    def test_allow_revert_commits_unfixable(self):
        result = self.fixer.fix("Revert 'fix bug'", ["allow_revert_commits"])
        assert not result.fixed

    def test_allow_empty_commits_unfixable(self):
        result = self.fixer.fix("fix bug", ["allow_empty_commits"])
        # allow_empty_commits is not in _TRANSFORM_ORDER → unfixable
        assert not result.fixed


# ---------------------------------------------------------------------------
# FixResult fields
# ---------------------------------------------------------------------------


class TestFixResult:
    def setup_method(self):
        self.fixer = CommitFixer()

    def test_fixed_message_equals_original_when_nothing_fixable(self):
        result = self.fixer.fix("fix bug", ["subject_max_length"])
        assert result.fixed_message == result.original_message

    def test_fixed_message_differs_when_transform_applied(self):
        result = self.fixer.fix("fixed bug", ["subject_imperative"])
        assert result.fixed_message != result.original_message

    def test_fixed_list_contains_check_names(self):
        result = self.fixer.fix("fixed bug", ["subject_imperative"])
        assert result.fixed == ["subject_imperative"]

    def test_unfixable_list_contains_tuples(self):
        result = self.fixer.fix("fix bug", ["subject_max_length"])
        assert isinstance(result.unfixable, list)
        assert len(result.unfixable) == 1
        check, reason = result.unfixable[0]
        assert check == "subject_max_length"
        assert isinstance(reason, str)

    def test_original_message_preserved(self):
        original = "WIP: fixed bug"
        result = self.fixer.fix(original, ["allow_wip_commits", "subject_imperative"])
        assert result.original_message == original


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def setup_method(self):
        self.fixer = CommitFixer()

    def test_windows_line_endings_normalized(self):
        # strip() on read normalizes CRLF; fixer receives the stripped message
        msg = "fixed bug\r\n\r\nBody."
        result = self.fixer.fix(msg, ["subject_imperative"])
        assert result.fixed_message.startswith("fix bug")

    def test_very_long_subject_unfixable(self):
        long_subject = "x" * 200
        result = self.fixer.fix(long_subject, ["subject_max_length"])
        assert not result.fixed

    def test_body_preserved_after_all_fixable_transforms(self):
        msg = "fixed bug\n\nDetailed explanation here."
        result = self.fixer.fix(
            msg,
            ["subject_imperative", "subject_capitalized"],
        )
        assert "Detailed explanation here." in result.fixed_message

    def test_wip_only_spaces_yields_empty_unfixable(self):
        # "WIP:   " → strip → "" → unfixable
        result = self.fixer.fix("WIP:   ", ["allow_wip_commits"])
        assert not result.fixed
        assert any("allow_wip_commits" in c for c, _ in result.unfixable)
