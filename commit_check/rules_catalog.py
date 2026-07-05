"""Centralized catalog of all commit-check rules, regexes, and error messages."""

from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class RuleCatalogEntry:
    check: str
    regex: str | None = None
    error: str | None = None
    suggest: str | None = None


# Commit message rules
COMMIT_RULES = [
    RuleCatalogEntry(
        check="message",
        regex=None,  # Built dynamically from config
        error="The commit message should follow Conventional Commits. See https://www.conventionalcommits.org",
        suggest="Use <type>(<scope>): <description> with allowed types",
    ),
    RuleCatalogEntry(
        check="subject_capitalized",
        regex=None,
        error="Subject must start with a capital letter",
        suggest="Capitalize the first word of the subject",
    ),
    RuleCatalogEntry(
        check="subject_imperative",
        regex=None,
        error="Commit message should use imperative mood (e.g., 'fix bug' not 'fixed bug', 'add feature' not 'adding feature')",
        suggest="Change the first verb to imperative form, e.g., 'fix' instead of 'fixed'/'fixes'/'fixing'",
    ),
    RuleCatalogEntry(
        check="subject_max_length",
        regex=None,
        error="Subject must be at most {max_len} characters",
        suggest="Keep the subject concise (<= configured max)",
    ),
    RuleCatalogEntry(
        check="subject_min_length",
        regex=None,
        error="Subject must be at least {min_len} characters",
        suggest="Provide a meaningful subject (>= configured min)",
    ),
    RuleCatalogEntry(
        check="allow_merge_commits",
        regex=None,
        error="Merge commits are not allowed",
        suggest="Rebase or squash your changes instead of merging",
    ),
    RuleCatalogEntry(
        check="allow_revert_commits",
        regex=None,
        error="Revert commits are not allowed",
        suggest="Avoid using 'revert' commits; rewrite history if necessary",
    ),
    RuleCatalogEntry(
        check="allow_empty_commits",
        regex=None,
        error="Empty commit messages are not allowed",
        suggest="Provide a non-empty subject",
    ),
    RuleCatalogEntry(
        check="allow_fixup_commits",
        regex=None,
        error="Fixup commits are not allowed",
        suggest="Use interactive rebase to clean up fixup commits",
    ),
    RuleCatalogEntry(
        check="allow_wip_commits",
        regex=None,
        error="WIP commits are not allowed",
        suggest="Complete the work before committing or remove 'WIP'",
    ),
    RuleCatalogEntry(
        check="require_body",
        regex=None,
        error="Commit body is required",
        suggest="Add a body explaining the change",
    ),
    RuleCatalogEntry(
        check="author_name",
        regex=r"^[A-Za-zÀ-ÖØ-öø-ÿ\u0100-\u017F\u0180-\u024F ,.'\-]+$|.*(\[bot])",
        error="The committer name seems invalid",
        suggest="git config user.name 'Your Name'",
    ),
    RuleCatalogEntry(
        check="author_email",
        regex=r"^.+@.+$",
        error="The committer's email seems invalid",
        suggest="git config user.email yourname@example.com",
    ),
    RuleCatalogEntry(
        check="ignore_authors",
        regex=None,
        error=None,
        suggest=None,
    ),
    RuleCatalogEntry(
        check="require_signed_off_by",
        regex=r"Signed-off-by:.*[A-Za-z0-9]\s+<.+@.+>",
        error="Signed-off-by not found in latest commit",
        suggest="git commit --amend --signoff or use --signoff on commit",
    ),
    RuleCatalogEntry(
        check="ai_attribution",
        regex=None,
        error="AI attribution policy violation",
        suggest="Remove AI attribution trailers from the commit message",
    ),
]

# Push rules
PUSH_RULES = [
    RuleCatalogEntry(
        check="no_force_push",
        regex=None,
        error="Force push is not allowed",
        suggest="Use a normal push instead of --force or --force-with-lease",
    ),
]

# Branch rules
BRANCH_RULES = [
    RuleCatalogEntry(
        check="branch",
        regex=None,  # Built dynamically from config
        error="The branch should follow Conventional Branch. See https://conventionalbranch.org",
        suggest="Use <type>/<description> with allowed types or add branch name to allow_branch_names in config, or use ignore_authors in config branch section to bypass",
    ),
    RuleCatalogEntry(
        check="merge_base",
        regex=None,  # Provided by config
        error="Current branch is not rebased onto target branch",
        suggest="Rebase or merge with the target branch",
    ),
    RuleCatalogEntry(
        check="ignore_authors",
        regex=None,
        error=None,
        suggest=None,
    ),
]
