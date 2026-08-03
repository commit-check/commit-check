"""Tests for stable rule IDs in the rules catalog."""

import re
from pathlib import Path

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
from commit_check import (
    DEFAULT_BOOLEAN_RULES,
    DEFAULT_BRANCH_TYPES,
    DEFAULT_COMMIT_TYPES,
    DEFAULT_PUSH_RULES,
)

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


class TestRulesDocumentation:
    """Anti-drift guard: every documented rule stays documented."""

    @pytest.mark.benchmark
    def test_every_rule_is_documented(self):
        """Each rule ID must have an anchor in the rules reference page.

        This prevents shipping a new rule without documenting it.
        """
        content = _read_doc("rules.rst")
        for entry in ALL_RULES:
            anchor = f".. _{entry.rule_id.lower()}:"
            assert anchor in content, (
                f"{entry.rule_id} ({entry.check}) is missing from docs/rules.rst"
            )

    @pytest.mark.benchmark
    def test_every_rule_has_a_section_heading(self):
        """Each rule needs a ``name (CCxxx)`` heading, not just an anchor.

        An anchor alone would satisfy the test above while linking readers to
        an empty part of the page.
        """
        content = _read_doc("rules.rst")
        for entry in ALL_RULES:
            heading = f"{entry.name} ({entry.rule_id})"
            assert heading in content, (
                f"docs/rules.rst has no section titled '{heading}'"
            )

    @pytest.mark.benchmark
    def test_every_rule_explains_itself(self):
        """Each rule section must answer what it does and why it matters."""
        content = _read_doc("rules.rst")
        # Split on the anchors so each rule's prose is checked in isolation.
        for entry in ALL_RULES:
            _, _, after = content.partition(f".. _{entry.rule_id.lower()}:")
            section = re.split(r"\n\.\. _cc\d{3}:", after)[0]
            for required in ("**What it does**", "**Why is this bad?**", "**Options**"):
                assert required in section, (
                    f"{entry.rule_id} ({entry.check}) section is missing {required}"
                )


class TestDocumentedDefaults:
    """The documented defaults must match the ones the code actually uses."""

    @pytest.mark.benchmark
    def test_boolean_defaults_match_configuration_docs(self):
        """Every boolean option's documented default matches the source.

        The options table in ``docs/configuration.rst`` is maintained by hand.
        Without this guard it silently drifts away from
        ``DEFAULT_BOOLEAN_RULES`` whenever a default changes.
        """
        documented = _parse_options_table(_read_doc("configuration.rst"))
        expected = {**DEFAULT_BOOLEAN_RULES, **DEFAULT_PUSH_RULES}

        for option, default in expected.items():
            assert option in documented, (
                f"'{option}' has a default in the source but no row in the "
                f"options table of docs/configuration.rst"
            )
            assert documented[option] == default, (
                f"docs/configuration.rst documents {option} as "
                f"{str(documented[option]).lower()}, but the default is "
                f"{str(default).lower()}"
            )

    @pytest.mark.parametrize(
        ("option", "expected"),
        [
            ("allow_commit_types", DEFAULT_COMMIT_TYPES),
            ("allow_branch_types", DEFAULT_BRANCH_TYPES),
        ],
    )
    @pytest.mark.benchmark
    def test_list_defaults_match_configuration_docs(self, option, expected):
        """The documented list defaults contain exactly the real values.

        Compared as sets: these are allow-lists, so the order they are listed
        in carries no meaning and should not fail the build.
        """
        documented = _parse_list_default(_read_doc("configuration.rst"), option)
        assert documented is not None, (
            f"'{option}' has no list[str] row in the options table of "
            f"docs/configuration.rst"
        )
        assert set(documented) == set(expected), (
            f"docs/configuration.rst documents {option} with "
            f"{sorted(set(documented) - set(expected))} that are not defaults, "
            f"and is missing {sorted(set(expected) - set(documented))}"
        )


def _read_doc(name: str) -> str:
    """Read a file from the ``docs`` directory."""
    return (Path(__file__).parent.parent / "docs" / name).read_text(encoding="utf-8")


def _parse_options_table(content: str) -> dict[str, bool]:
    """Extract ``option -> documented default`` for boolean rows.

    Matches the five-cell ``list-table`` rows in the options table, e.g.::

        * - commit
          - allow_wip_commits
          - bool
          - true
          - Allow work-in-progress commits.
    """
    row = re.compile(
        r"\*\s+-\s+(?:commit|branch|push)\s*\n"
        r"\s+-\s+(\w+)\s*\n"
        r"\s+-\s+bool\s*\n"
        r"\s+-\s+(true|false)\s*\n"
    )
    return {name: value == "true" for name, value in row.findall(content)}


def _parse_list_default(content: str, option: str) -> list[str] | None:
    """Extract the documented default for a ``list[str]`` option.

    Returns ``None`` when the option has no ``list[str]`` row, so the caller
    can tell "undocumented" apart from "documented as empty".
    """
    row = re.search(
        rf"\*\s+-\s+(?:commit|branch|push)\s*\n"
        rf"\s+-\s+{re.escape(option)}\s*\n"
        rf"\s+-\s+list\[str\]\s*\n"
        rf"\s+-\s+(\[.*?\])\s*\n",
        content,
        re.S,
    )
    if row is None:
        return None
    return re.findall(r'"([^"]+)"', row.group(1))
