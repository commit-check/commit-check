"""Centralized built-in rules and TOML translation for commit-check."""
from __future__ import annotations
from typing import Any, Dict, List


def build_checks_from_toml(conf: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """Translate high-level TOML options into internal checks list.

    Each documented option in docs/configuration.rst yields a corresponding
    rule here. Regex remains internal; users do not provide regex.
    """
    checks: List[Dict[str, Any]] = []

    commit_cfg = conf.get("commit", {}) or {}
    branch_cfg = conf.get("branch", {}) or {}
    author_cfg = conf.get("author", {}) or {}

    # --- commit section ---
    if commit_cfg.get("conventional_commits", True):
        allowed_types = commit_cfg.get("allow_commit_types") or [
            "feat", "fix", "docs", "style", "refactor", "test", "chore",
        ]
        allowed_re = "|".join(sorted(set(allowed_types)))
        conv_regex = rf"^({allowed_re}){{1}}(\([\w\-\.]+\))?(!)?: ([\w ])+([\s\S]*)|(Merge).*|(fixup!.*)"
        checks.append({
            "check": "message",
            "regex": conv_regex,
            "error": "The commit message should follow Conventional Commits. See https://www.conventionalcommits.org",
            "suggest": "Use <type>(<scope>): <description> with allowed types",
            "allowed_types": allowed_types,
        })

    if commit_cfg.get("subject_capitalized", True):
        checks.append({
            "check": "subject_capitalized",
            "regex": "",
            "error": "Subject must start with a capital letter",
            "suggest": "Capitalize the first word of the subject",
        })

    if commit_cfg.get("subject_imperative", True):
        checks.append({
            "check": "imperative",
            "regex": "",
            "error": "Commit message should use imperative mood (e.g., 'Add feature' not 'Added feature')",
            "suggest": "Use imperative mood in the subject line",
        })

    max_len = commit_cfg.get("subject_max_length")
    if isinstance(max_len, int):
        checks.append({
            "check": "subject_max_length",
            "regex": "",
            "error": f"Subject must be at most {max_len} characters",
            "suggest": "Keep the subject concise (<= configured max)",
            "value": max_len,
        })
    min_len = commit_cfg.get("subject_min_length")
    if isinstance(min_len, int):
        checks.append({
            "check": "subject_min_length",
            "regex": "",
            "error": f"Subject must be at least {min_len} characters",
            "suggest": "Provide a meaningful subject (>= configured min)",
            "value": min_len,
        })

    if commit_cfg.get("allow_merge_commits", True) is False:
        checks.append({
            "check": "allow_merge_commits",
            "regex": "",
            "error": "Merge commits are not allowed",
            "suggest": "Rebase or squash your changes instead of merging",
            "value": False,
        })
    if commit_cfg.get("allow_revert_commits", True) is False:
        checks.append({
            "check": "allow_revert_commits",
            "regex": "",
            "error": "Revert commits are not allowed",
            "suggest": "Avoid using 'revert' commits; rewrite history if necessary",
            "value": False,
        })
    if commit_cfg.get("allow_empty_commits", False) is False:
        checks.append({
            "check": "allow_empty_commits",
            "regex": "",
            "error": "Empty commit messages are not allowed",
            "suggest": "Provide a non-empty subject",
            "value": False,
        })
    if commit_cfg.get("allow_fixup_commits", True) is False:
        checks.append({
            "check": "allow_fixup_commits",
            "regex": "",
            "error": "Fixup commits are not allowed",
            "suggest": "Use interactive rebase to clean up fixup commits",
            "value": False,
        })
    if commit_cfg.get("allow_wip_commits", False) is False:
        checks.append({
            "check": "allow_wip_commits",
            "regex": "",
            "error": "WIP commits are not allowed",
            "suggest": "Complete the work before committing or remove 'WIP'",
            "value": False,
        })
    if commit_cfg.get("require_body", False):
        checks.append({
            "check": "require_body",
            "regex": "",
            "error": "Commit body is required",
            "suggest": "Add a body explaining the change",
            "value": True,
        })

    # --- branch section ---
    if branch_cfg.get("conventional_branch", True):
        branch_allowed = branch_cfg.get("allow_branch_types") or [
            "feature", "bugfix", "hotfix", "release", "chore", "feat", "fix",
        ]
        # Preserve order while de-duplicating
        seen_b = set()
        ordered_branch_allowed: List[str] = []
        for t in branch_allowed:
            if t not in seen_b:
                seen_b.add(t)
                ordered_branch_allowed.append(t)
        allowed_re = "|".join(ordered_branch_allowed)
        regex = rf"^({allowed_re})\/.+|(master)|(main)|(HEAD)|(PR-.+)"
        checks.append({
            "check": "branch",
            "regex": regex,
            "error": "Branches must begin with allowed types (e.g., feature/, bugfix/) or be main/master/PR-*.",
            "suggest": "git checkout -b <type>/<branch_name>",
            "allowed": ordered_branch_allowed,
            "allowed_types": ordered_branch_allowed,
        })

    target = branch_cfg.get("require_rebase_target")
    if isinstance(target, str) and target:
        checks.append({
            "check": "merge_base",
            "regex": target,
            "error": "Current branch is not rebased onto target branch",
            "suggest": "Rebase or merge with the target branch",
        })

    # --- author section ---
    checks.append({
        "check": "author_name",
        "regex": r"^[A-Za-zÀ-ÖØ-öø-ÿ\u0100-\u017F\u0180-\u024F ,.'\-]+$|.*(\[bot])",
        "error": "The committer name seems invalid",
        "suggest": "git config user.name 'Your Name'",
    })
    checks.append({
        "check": "author_email",
        "regex": r"^.+@.+$",
        "error": "The committer's email seems invalid",
        "suggest": "git config user.email yourname@example.com",
    })

    allow_authors = author_cfg.get("allow_authors")
    if isinstance(allow_authors, list) and allow_authors:
        checks.append({
            "check": "allow_authors",
            "regex": "",
            "error": "Author is not allowed",
            "suggest": "Use a configured author or adjust configuration",
            "allowed": allow_authors,
        })
    ignore_authors = author_cfg.get("ignore_authors")
    if isinstance(ignore_authors, list) and ignore_authors:
        checks.append({
            "check": "ignore_authors",
            "regex": "",
            "error": "",
            "suggest": "",
            "ignored": ignore_authors,
        })

    if author_cfg.get("require_signed_off_by", False):
        sign_name = author_cfg.get("required_signoff_name")
        sign_email = author_cfg.get("required_signoff_email")
        rule: Dict[str, Any] = {
            "check": "commit_signoff",
            "regex": r"Signed-off-by:.*[A-Za-z0-9]\s+<.+@.+>",
            "error": "Signed-off-by not found in latest commit",
            "suggest": "git commit --amend --signoff or use --signoff on commit",
        }
        if sign_name:
            rule["required_name"] = sign_name
        if sign_email:
            rule["required_email"] = sign_email
        checks.append(rule)

    return {"checks": checks}
