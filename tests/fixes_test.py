"""Tests for the deterministic corrections in commit_check.fixes."""

import pytest

from commit_check.fixes import (
    fix_branch_type,
    fix_conventional_header,
    fix_subject_case,
    fix_wip,
    signoff_trailer,
    strip_lines_containing,
)

TYPES = ["feat", "fix", "docs", "test", "chore", "refactor"]


class TestFixConventionalHeader:
    @pytest.mark.parametrize(
        "subject, expected",
        [
            ("Fix: add x", "fix: add x"),
            ("FEAT(api): add x", "feat(api): add x"),
            ("feat add x", "feat: add x"),
            ("feat:add x", "feat: add x"),
            ("feat :  add x", "feat: add x"),
            ("feta: add x", "feat: add x"),
            ("refactr(core)!: drop y", "refactor(core)!: drop y"),
            ("  fix: trailing  ", "fix: trailing"),
        ],
    )
    def test_mechanical_slips_are_corrected(self, subject, expected):
        assert fix_conventional_header(subject, TYPES) == expected

    @pytest.mark.parametrize(
        "subject",
        [
            "add x",  # no type at all: choosing one is a judgment
            "update the readme",  # a verb, not a near-miss of a type
            "feat: add x",  # already valid, nothing to change
            "feat:",  # no description to keep
            "xyzzy: add x",  # not close to any type
        ],
    )
    def test_declines_to_guess(self, subject):
        assert fix_conventional_header(subject, TYPES) is None

    def test_no_allowed_types_no_fix(self):
        assert fix_conventional_header("Fix: add x", None) is None
        assert fix_conventional_header("Fix: add x", []) is None

    def test_short_words_only_match_by_case(self):
        # "fx" is one letter off "fix" but too short for similarity matching.
        assert fix_conventional_header("fx: add x", TYPES) is None
        assert fix_conventional_header("FIX: add x", TYPES) == "fix: add x"

    def test_feat_never_becomes_test(self):
        # Both are four letters and share two; the cutoff must keep them apart.
        assert fix_conventional_header("feat: add x", ["test"]) is None
        # A one-letter substitution in a short word is a different word.
        assert fix_conventional_header("text: add x", ["test"]) is None

    def test_swapped_letters_are_corrected(self):
        assert fix_conventional_header("feta: add x", TYPES) == "feat: add x"
        assert fix_conventional_header("fxi: add x", TYPES) == "fix: add x"


class TestFixSubjectCase:
    def test_capitalizes_description_after_prefix(self):
        assert fix_subject_case("feat: add x") == "feat: Add x"
        assert fix_subject_case("fix(api)!: drop y") == "fix(api)!: Drop y"

    def test_capitalizes_plain_subject(self):
        assert fix_subject_case("add x") == "Add x"

    def test_lowercases_when_asked(self):
        assert fix_subject_case("feat: Add x", capitalize=False) == "feat: add x"

    def test_no_change_needed(self):
        assert fix_subject_case("feat: Add x") is None

    def test_non_alphabetic_start_is_not_touched(self):
        assert fix_subject_case("feat: 2fa support") is None
        assert fix_subject_case("feat: ") is None


class TestFixWip:
    @pytest.mark.parametrize(
        "message, expected",
        [
            ("WIP: add x", "add x"),
            ("wip: add x", "add x"),
            ("[WIP] add x", "add x"),
            ("[wip]: add x", "add x"),
            ("WIP add x", "add x"),
            ("WIP - add x", "add x"),
            ("WIP: feat: add x\n\nbody", "feat: add x\n\nbody"),
        ],
    )
    def test_marker_is_dropped(self, message, expected):
        assert fix_wip(message) == expected

    def test_nothing_left_is_no_fix(self):
        assert fix_wip("WIP") is None
        assert fix_wip("WIP:") is None

    def test_no_marker_no_fix(self):
        assert fix_wip("feat: add x") is None
        # "wipe" is a word, not a marker.
        assert fix_wip("wipe the cache") is None


class TestSignoffTrailer:
    def test_full_identity(self):
        assert (
            signoff_trailer("Jane Doe", "jane@example.com")
            == "Signed-off-by: Jane Doe <jane@example.com>"
        )

    def test_missing_half_is_no_trailer(self):
        assert signoff_trailer("", "jane@example.com") is None
        assert signoff_trailer("Jane Doe", "") is None


class TestFixBranchType:
    def test_case_and_spelling(self):
        assert fix_branch_type("Feature/login", TYPES + ["feature"]) == "feature/login"
        assert fix_branch_type("featre/login", ["feature", "bugfix"]) == "feature/login"

    def test_no_slash_no_fix(self):
        assert fix_branch_type("login", ["feature"]) is None
        assert fix_branch_type("feature/", ["feature"]) is None

    def test_unrelated_prefix_no_fix(self):
        assert fix_branch_type("xyzzy/login", ["feature", "bugfix"]) is None

    def test_already_valid_no_fix(self):
        assert fix_branch_type("feature/login", ["feature"]) is None


class TestStripLinesContaining:
    def test_drops_matching_lines_only(self):
        message = "feat: init\n\nSome body\n\nCo-authored-by: Claude <noreply@anthropic.com>"
        assert (
            strip_lines_containing(message, ["Co-authored-by: Claude <noreply@anthropic.com>"])
            == "feat: init\n\nSome body"
        )

    def test_partial_fragment_matches_its_line(self):
        message = "feat: init\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)"
        assert strip_lines_containing(message, ["🤖 Generated with [Claude"]) == "feat: init"

    def test_no_match_no_fix(self):
        assert strip_lines_containing("feat: init", ["Co-authored-by: Claude"]) is None
        assert strip_lines_containing("feat: init", []) is None
        assert strip_lines_containing("feat: init", [""]) is None

    def test_nothing_left_is_no_fix(self):
        assert strip_lines_containing("Co-authored-by: Claude", ["Co-authored-by: Claude"]) is None
