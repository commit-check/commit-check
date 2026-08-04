"""Tests for stable rule IDs in the rules catalog.

The checks that compared these rules against the documentation now live in
the commit-check.com repository, next to the pages they read.
"""

import re

import pytest

from commit_check.rules_catalog import (
    ALL_RULES,
    RULES_BY_CHECK,
    BRANCH_RULES,
    COMMIT_RULES,
    PUSH_RULES,
    RULES_DOCS_URL,
    RuleCatalogEntry,
)
from commit_check.rule_builder import RuleBuilder

ALL_ENTRIES = [*COMMIT_RULES, *BRANCH_RULES, *PUSH_RULES]


class TestRuleIds:
    """The rule ID contract: stable, unique, well-formed."""

    @pytest.mark.benchmark
    def test_rule_ids_are_unique(self):
        """No two rules may share an ID."""
        ids = [e.rule_id for e in ALL_ENTRIES if e.rule_id]
        assert len(ids) == len(set(ids)), "duplicate rule IDs found"

    @pytest.mark.benchmark
    def test_identified_checks_are_unique(self):
        """Check names of identified rules must be unique.

        Rule identity is looked up by check name, so a duplicate would
        silently shadow one of the rules.
        """
        checks = [e.check for e in ALL_RULES]
        assert len(checks) == len(set(checks))
        assert len(RULES_BY_CHECK) == len(ALL_RULES)

    @pytest.mark.benchmark
    def test_rule_ids_are_well_formed(self):
        """Rule IDs look like CC001."""
        for entry in ALL_ENTRIES:
            if entry.rule_id:
                assert re.fullmatch(r"CC\d{3}", entry.rule_id), entry.rule_id

    @pytest.mark.benchmark
    def test_diagnostic_rules_all_have_ids(self):
        """Any rule that can report a failure must have an ID.

        Entries without an error message are internal bookkeeping (e.g.
        ``ignore_authors``) and intentionally carry no ID.
        """
        for entry in ALL_ENTRIES:
            if entry.error:
                assert entry.rule_id, f"{entry.check} can fail but has no rule ID"

    @pytest.mark.benchmark
    def test_docs_url_derives_from_id(self):
        """The docs URL is derived from the rule ID, not stored separately."""
        entry = RuleCatalogEntry(check="subject_imperative", rule_id="CC003")
        assert entry.docs_url == f"{RULES_DOCS_URL}#cc003"

    @pytest.mark.benchmark
    def test_docs_url_points_at_the_published_site(self):
        """The base URL is pinned, not just derived.

        Every failure the tool reports carries this URL, and released versions
        keep printing whatever they shipped with, so a wrong value cannot be
        corrected after the fact. The other tests build their expectations from
        ``RULES_DOCS_URL`` and would follow it anywhere, including back to a
        host that no longer serves the documentation.
        """
        assert RULES_DOCS_URL == "https://commit-check.com/rules/"

    @pytest.mark.benchmark
    def test_no_docs_url_without_id(self):
        """An entry without a rule ID has no docs URL to link to."""
        assert RuleCatalogEntry(check="ignore_authors").docs_url is None

    @pytest.mark.benchmark
    def test_name_is_kebab_case(self):
        """The display name is the kebab-case form of the config key."""
        assert RuleCatalogEntry(check="subject_imperative").name == "subject-imperative"


class TestRuleIdPropagation:
    """Built rules carry their catalog identity through to output."""

    @pytest.mark.benchmark
    def test_built_rule_has_id_and_docs_url(self):
        """A rule built from the catalog carries its ID and docs URL."""
        rules = RuleBuilder({"commit": {"subject_imperative": True}}).build_all_rules()
        rule = next(r for r in rules if r.check == "subject_imperative")
        assert rule.rule_id == "CC003"
        assert rule.docs_url == f"{RULES_DOCS_URL}#cc003"

    @pytest.mark.benchmark
    def test_to_dict_includes_id_and_docs_url(self):
        """Serialised rules expose the ID and docs URL to consumers."""
        rules = RuleBuilder({"commit": {"subject_imperative": True}}).build_all_rules()
        rule = next(r for r in rules if r.check == "subject_imperative")
        as_dict = rule.to_dict()
        assert as_dict["rule_id"] == "CC003"
        assert as_dict["docs_url"].endswith("#cc003")

    @pytest.mark.benchmark
    def test_internal_entries_have_no_id(self):
        """ignore_authors is bookkeeping - it must not leak a rule ID."""
        entry = next(e for e in ALL_ENTRIES if e.check == "ignore_authors")
        assert entry.rule_id is None

        rules = RuleBuilder({"commit": {"ignore_authors": ["bot"]}}).build_all_rules()
        rule = next(r for r in rules if r.check == "ignore_authors")
        assert rule.rule_id is None
        assert rule.docs_url is None
