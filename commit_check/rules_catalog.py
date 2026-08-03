"""Centralized catalog of all commit-check rules, regexes, and error messages.

Every user-facing rule has a **stable rule ID** (e.g. ``CC003``) that never
changes once released.  Rule IDs give users a durable handle to reference in
documentation, error output, and machine-readable results.

ID ranges
---------
=========  ==================================
``CC0xx``  Commit message rules
``CC1xx``  Author (name / email) rules
``CC2xx``  Branch rules
``CC3xx``  Push rules
=========  ==================================

Internal bookkeeping entries that never produce a diagnostic (such as
``ignore_authors``) intentionally have no rule ID.
"""

from __future__ import annotations
from dataclasses import dataclass

#: Base URL of the rules reference documentation.
RULES_DOCS_URL = "https://commit-check.github.io/commit-check/rules.html"


@dataclass(frozen=True)
class RuleCatalogEntry:
    check: str
    regex: str | None = None
    error: str | None = None
    suggest: str | None = None
    rule_id: str | None = None

    @property
    def name(self) -> str:
        """Human-readable rule name, e.g. ``subject-imperative``."""
        return self.check.replace("_", "-")

    @property
    def docs_url(self) -> str | None:
        """Link to this rule's section in the rules reference, if it has an ID."""
        if not self.rule_id:
            return None
        return f"{RULES_DOCS_URL}#{self.rule_id.lower()}"


# Commit message rules
COMMIT_RULES = [
    RuleCatalogEntry(
        rule_id="CC001",
        check="message",
        regex=None,  # Built dynamically from config
        error="The commit message should follow Conventional Commits. See https://www.conventionalcommits.org",
        suggest="Use <type>(<scope>): <description> with allowed types",
    ),
    RuleCatalogEntry(
        rule_id="CC002",
        check="subject_capitalized",
        regex=None,
        error="Subject must start with a capital letter",
        suggest="Capitalize the first word of the subject",
    ),
    RuleCatalogEntry(
        rule_id="CC003",
        check="subject_imperative",
        regex=None,
        error="Commit message should use imperative mood (e.g., 'fix bug' not 'fixed bug', 'add feature' not 'adding feature')",
        suggest="Change the first verb to imperative form, e.g., 'fix' instead of 'fixed'/'fixes'/'fixing'",
    ),
    RuleCatalogEntry(
        rule_id="CC004",
        check="subject_max_length",
        regex=None,
        error="Subject must be at most {max_len} characters",
        suggest="Keep the subject concise (<= configured max)",
    ),
    RuleCatalogEntry(
        rule_id="CC005",
        check="subject_min_length",
        regex=None,
        error="Subject must be at least {min_len} characters",
        suggest="Provide a meaningful subject (>= configured min)",
    ),
    RuleCatalogEntry(
        rule_id="CC006",
        check="allow_merge_commits",
        regex=None,
        error="Merge commits are not allowed",
        suggest="Rebase or squash your changes instead of merging",
    ),
    RuleCatalogEntry(
        rule_id="CC007",
        check="allow_revert_commits",
        regex=None,
        error="Revert commits are not allowed",
        suggest="Avoid using 'revert' commits; rewrite history if necessary",
    ),
    RuleCatalogEntry(
        rule_id="CC008",
        check="allow_empty_commits",
        regex=None,
        error="Empty commit messages are not allowed",
        suggest="Provide a non-empty subject",
    ),
    RuleCatalogEntry(
        rule_id="CC009",
        check="allow_fixup_commits",
        regex=None,
        error="Fixup commits are not allowed",
        suggest="Use interactive rebase to clean up fixup commits",
    ),
    RuleCatalogEntry(
        rule_id="CC010",
        check="allow_wip_commits",
        regex=None,
        error="WIP commits are not allowed",
        suggest="Complete the work before committing or remove 'WIP'",
    ),
    RuleCatalogEntry(
        rule_id="CC011",
        check="require_body",
        regex=None,
        error="Commit body is required",
        suggest="Add a body explaining the change",
    ),
    RuleCatalogEntry(
        rule_id="CC101",
        check="author_name",
        regex=r"^[A-Za-zÀ-ÖØ-öø-ÿ\u0100-\u017F\u0180-\u024F ,.'\-]+$|.*(\[bot])",
        error="The committer name seems invalid",
        suggest="git config user.name 'Your Name'",
    ),
    RuleCatalogEntry(
        rule_id="CC102",
        check="author_email",
        regex=r"^.+@.+$",
        error="The committer's email seems invalid",
        suggest="git config user.email yourname@example.com",
    ),
    RuleCatalogEntry(
        # Internal bookkeeping entry - never produces a diagnostic.
        check="ignore_authors",
        regex=None,
        error=None,
        suggest=None,
    ),
    RuleCatalogEntry(
        rule_id="CC012",
        check="require_signed_off_by",
        regex=r"Signed-off-by: .+ <.+@.+>",
        error="Signed-off-by not found in latest commit",
        suggest="git commit --amend --signoff or use --signoff on commit",
    ),
    RuleCatalogEntry(
        rule_id="CC013",
        check="ai_attribution",
        regex=None,
        error="AI attribution policy violation",
        suggest="This project forbids AI-assisted commits. Remove AI trailers and re-commit.",
    ),
]

# Push rules
PUSH_RULES = [
    RuleCatalogEntry(
        rule_id="CC301",
        check="no_force_push",
        regex=None,
        error="Force push is not allowed",
        suggest="Use a normal push instead of --force or --force-with-lease",
    ),
]

# Branch rules
BRANCH_RULES = [
    RuleCatalogEntry(
        rule_id="CC201",
        check="branch",
        regex=None,  # Built dynamically from config
        error="The branch should follow Conventional Branch. See https://conventionalbranch.org",
        suggest="Use <type>/<description> with allowed types or add branch name to allow_branch_names in config, or use ignore_authors in config branch section to bypass",
    ),
    RuleCatalogEntry(
        rule_id="CC202",
        check="merge_base",
        regex=None,  # Provided by config
        error="Current branch is not rebased onto target branch",
        suggest="Rebase or merge with the target branch",
    ),
    RuleCatalogEntry(
        # Internal bookkeeping entry - never produces a diagnostic.
        check="ignore_authors",
        regex=None,
        error=None,
        suggest=None,
    ),
]

#: All catalog entries that represent a user-facing, documented rule.
ALL_RULES = [
    entry
    for entry in (*COMMIT_RULES, *BRANCH_RULES, *PUSH_RULES)
    if entry.rule_id is not None
]

#: Lookup from check name to its catalog entry, for rules that have an ID.
#: Rule identity lives only here, so built rules can never carry a stale copy.
RULES_BY_CHECK = {entry.check: entry for entry in ALL_RULES}
