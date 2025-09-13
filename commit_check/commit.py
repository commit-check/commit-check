"""Check git commit message formatting"""

from typing import Optional
import re
from pathlib import PurePath
from commit_check import YELLOW, RESET_COLOR, PASS, FAIL
from commit_check.util import (
    _find_check,
    _print_failure,
    cmd_output,
    get_commit_info,
    has_commits,
)
from commit_check.imperatives import IMPERATIVES


def _load_imperatives() -> set:
    """Load imperative verbs from imperatives module."""
    return IMPERATIVES


def _ensure_msg_file(commit_msg_file: str | None) -> str:
    """Return a commit message file path, falling back to the default when empty."""
    if not commit_msg_file:
        return get_default_commit_msg_file()
    return commit_msg_file


def get_default_commit_msg_file() -> str:
    """Get the default commit message file."""
    git_dir = cmd_output(["git", "rev-parse", "--git-dir"]).strip()
    return str(PurePath(git_dir, "COMMIT_EDITMSG"))


def read_commit_msg(commit_msg_file) -> str:
    """Read the commit message from the specified file."""
    try:
        with open(commit_msg_file, "r") as f:
            return f.read()
    except FileNotFoundError:
        # Commit message is composed by subject and body
        return str(get_commit_info("s") + "\n\n" + get_commit_info("b"))


def check_commit_msg(
    checks: list, commit_msg_file: str = "", stdin_text: Optional[str] = None
) -> int:
    """Check commit message against the provided checks.

    If stdin_text is provided, use it directly (stdin override) and do not
    require a git repository state. Otherwise, fall back to reading from file/Git.
    """
    if stdin_text is None and has_commits() is False:
        return PASS  # pragma: no cover

    check = _find_check(checks, "message")
    if not check:
        return PASS  # pragma: no cover

    regex = check.get("regex", "")
    if regex == "":
        print(
            f"{YELLOW}Not found regex for commit message. skip checking.{RESET_COLOR}"
        )
        return PASS

    if stdin_text is not None:
        commit_msg = stdin_text
    else:
        path = _ensure_msg_file(commit_msg_file)
        commit_msg = read_commit_msg(path)

    if re.match(regex, commit_msg):
        return PASS

    _print_failure(check, regex, commit_msg)
    return FAIL


def check_commit_signoff(
    checks: list, commit_msg_file: str = "", stdin_text: Optional[str] = None
) -> int:
    if stdin_text is None and has_commits() is False:
        return PASS  # pragma: no cover

    check = _find_check(checks, "commit_signoff")
    if not check:
        return PASS  # pragma: no cover

    regex = check.get("regex", "")
    if regex == "":
        print(
            f"{YELLOW}Not found regex for commit signoff. skip checking.{RESET_COLOR}"
        )
        return PASS

    if stdin_text is not None:
        commit_msg = stdin_text
    else:
        path = _ensure_msg_file(commit_msg_file)
        commit_msg = read_commit_msg(path)

    # Extract the subject line (first line of commit message)
    subject = commit_msg.split("\n")[0].strip()

    # Skip if merge commit
    if subject.startswith("Merge"):
        return PASS

    commit_hash = get_commit_info("H")
    if re.search(regex, commit_msg):
        return PASS

    _print_failure(check, regex, commit_hash)
    return FAIL


def check_imperative(
    checks: list, commit_msg_file: str = "", stdin_text: Optional[str] = None
) -> int:
    """Check if commit message uses imperative mood."""
    if stdin_text is None and has_commits() is False:
        return PASS  # pragma: no cover

    check = _find_check(checks, "imperative")
    if not check:
        return PASS

    if stdin_text is not None:
        commit_msg = stdin_text
    else:
        path = _ensure_msg_file(commit_msg_file)
        commit_msg = read_commit_msg(path)

    # Extract the subject line (first line of commit message)
    subject = commit_msg.split("\n")[0].strip()

    # Skip if empty or merge commit
    if not subject or subject.startswith("Merge"):
        return PASS

    # For conventional commits, extract description after the colon
    description = subject.split(":", 1)[1].strip() if ":" in subject else subject

    # Check if the description uses imperative mood
    if _is_imperative(description):
        return PASS

    _print_failure(check, "imperative mood pattern", subject)
    return FAIL


# --- Additional per-option checks (not yet wired into CLI) ---


def _get_subject_and_body(
    stdin_text: Optional[str], commit_msg_file: str
) -> tuple[str, str]:
    if stdin_text is not None:
        commit_msg = stdin_text
    else:
        path = _ensure_msg_file(commit_msg_file)
        commit_msg = read_commit_msg(path)
    subject = commit_msg.split("\n")[0].strip()
    body = "\n".join(commit_msg.split("\n")[1:]).strip()
    return subject, body


def check_subject_capitalized(
    checks: list, commit_msg_file: str = "", stdin_text: Optional[str] = None
) -> int:
    if stdin_text is None and has_commits() is False:
        return PASS  # pragma: no cover
    check = _find_check(checks, "subject_capitalized")
    if not check:
        return PASS
    subject, _ = _get_subject_and_body(stdin_text, commit_msg_file)
    if not subject or subject[0].isupper():
        return PASS
    _print_failure(check, "capitalized first letter", subject)
    return FAIL


def check_subject_max_length(
    checks: list, commit_msg_file: str = "", stdin_text: Optional[str] = None
) -> int:
    if stdin_text is None and has_commits() is False:
        return PASS  # pragma: no cover
    check = _find_check(checks, "subject_max_length")
    if not check:
        return PASS
    max_len = int(check.get("value", 0) or 0)
    subject, _ = _get_subject_and_body(stdin_text, commit_msg_file)
    # Skip if merge commit
    if subject.startswith("Merge"):
        return PASS
    if not max_len or len(subject) <= max_len:
        return PASS
    _print_failure(check, f"max_length={max_len}", subject)
    return FAIL


def check_subject_min_length(
    checks: list, commit_msg_file: str = "", stdin_text: Optional[str] = None
) -> int:
    if stdin_text is None and has_commits() is False:
        return PASS  # pragma: no cover
    check = _find_check(checks, "subject_min_length")
    if not check:
        return PASS
    min_len = int(check.get("value", 0) or 0)
    subject, _ = _get_subject_and_body(stdin_text, commit_msg_file)
    if len(subject) >= min_len:
        return PASS
    _print_failure(check, f"min_length={min_len}", subject)
    return FAIL


def check_allow_commit_types(
    checks: list, commit_msg_file: str = "", stdin_text: Optional[str] = None
) -> int:
    if stdin_text is None and has_commits() is False:
        return PASS  # pragma: no cover
    check = _find_check(checks, "allow_commit_types")
    if not check:
        return PASS
    allowed = set(check.get("allowed") or [])
    subject, _ = _get_subject_and_body(stdin_text, commit_msg_file)
    ctype = (
        subject.split(":", 1)[0].split("(")[0].strip()
        if ":" in subject
        else subject.split("(")[0].strip()
    )
    if ctype in allowed:
        return PASS
    _print_failure(check, f"allowed={sorted(allowed)}", subject)
    return FAIL


def check_allow_merge_commits(
    checks: list, commit_msg_file: str = "", stdin_text: Optional[str] = None
) -> int:
    if stdin_text is None and has_commits() is False:
        return PASS  # pragma: no cover
    check = _find_check(checks, "allow_merge_commits")
    if not check:
        return PASS
    subject, _ = _get_subject_and_body(stdin_text, commit_msg_file)
    if subject.startswith("Merge"):
        _print_failure(check, "no merge commits", subject)
        return FAIL
    return PASS


def check_allow_revert_commits(
    checks: list, commit_msg_file: str = "", stdin_text: Optional[str] = None
) -> int:
    if stdin_text is None and has_commits() is False:
        return PASS  # pragma: no cover
    check = _find_check(checks, "allow_revert_commits")
    if not check:
        return PASS
    subject, _ = _get_subject_and_body(stdin_text, commit_msg_file)
    if subject.lower().startswith("revert"):
        _print_failure(check, "no revert commits", subject)
        return FAIL
    return PASS


def check_allow_empty_commits(
    checks: list, commit_msg_file: str = "", stdin_text: Optional[str] = None
) -> int:
    if stdin_text is None and has_commits() is False:
        return PASS  # pragma: no cover
    check = _find_check(checks, "allow_empty_commits")
    if not check:
        return PASS
    subject, _ = _get_subject_and_body(stdin_text, commit_msg_file)
    if subject:
        return PASS
    _print_failure(check, "non-empty subject required", subject)
    return FAIL


def check_allow_fixup_commits(
    checks: list, commit_msg_file: str = "", stdin_text: Optional[str] = None
) -> int:
    if stdin_text is None and has_commits() is False:
        return PASS  # pragma: no cover
    check = _find_check(checks, "allow_fixup_commits")
    if not check:
        return PASS
    subject, _ = _get_subject_and_body(stdin_text, commit_msg_file)
    if subject.startswith("fixup!"):
        _print_failure(check, "no fixup commits", subject)
        return FAIL
    return PASS


def check_allow_wip_commits(
    checks: list, commit_msg_file: str = "", stdin_text: Optional[str] = None
) -> int:
    if stdin_text is None and has_commits() is False:
        return PASS  # pragma: no cover
    check = _find_check(checks, "allow_wip_commits")
    if not check:
        return PASS
    subject, _ = _get_subject_and_body(stdin_text, commit_msg_file)
    if subject.startswith("WIP") or subject.upper().startswith("WIP:"):
        _print_failure(check, "no WIP commits", subject)
        return FAIL
    return PASS


def check_require_body(
    checks: list, commit_msg_file: str = "", stdin_text: Optional[str] = None
) -> int:
    if stdin_text is None and has_commits() is False:
        return PASS  # pragma: no cover
    check = _find_check(checks, "require_body")
    if not check:
        return PASS
    _, body = _get_subject_and_body(stdin_text, commit_msg_file)
    if body:
        return PASS
    _print_failure(check, "body required", "")
    return FAIL


def _is_imperative(description: str) -> bool:
    """Check if a description uses imperative mood."""
    if not description:
        return True

    # Get the first word of the description
    first_word = description.split()[0].lower()

    # Load imperative verbs from file
    imperatives = _load_imperatives()

    # Check for common past tense pattern (-ed ending) but be more specific
    if (
        first_word.endswith("ed")
        and len(first_word) > 3
        and first_word not in {"red", "bed", "fed", "led", "wed", "shed", "fled"}
    ):
        return False

    # Check for present continuous pattern (-ing ending) but be more specific
    if (
        first_word.endswith("ing")
        and len(first_word) > 4
        and first_word
        not in {"ring", "sing", "king", "wing", "thing", "string", "bring"}
    ):
        return False

    # Check for third person singular (-s ending) but be more specific
    # Only flag if it's clearly a verb in third person singular form
    if first_word.endswith("s") and len(first_word) > 3:
        # Common nouns ending in 's' that should be allowed
        common_nouns_ending_s = {
            "process",
            "access",
            "address",
            "progress",
            "express",
            "stress",
            "success",
            "class",
            "pass",
            "mass",
            "loss",
            "cross",
            "gross",
            "boss",
            "toss",
            "less",
            "mess",
            "dress",
            "press",
            "bless",
            "guess",
            "chess",
            "glass",
            "grass",
            "brass",
        }

        # Words ending in 'ss' or 'us' are usually not third person singular verbs
        if first_word.endswith("ss") or first_word.endswith("us"):
            return True  # Allow these

        # If it's a common noun, allow it
        if first_word in common_nouns_ending_s:
            return True

        # Otherwise, it's likely a third person singular verb
        return False

    # If we have imperatives loaded, check if the first word is imperative
    if imperatives:
        # Check if the first word is in our imperative list
        if first_word in imperatives:
            return True

    # If word is not in imperatives list, apply some heuristics
    # If it passes all the negative checks above, it's likely imperative
    return True
