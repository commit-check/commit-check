"""Check git commit message formatting"""
import re
from pathlib import PurePath
from commit_check import YELLOW, RESET_COLOR, PASS, FAIL
from commit_check.util import cmd_output, get_commit_info, print_error_header, print_error_message, print_suggestion, has_commits
from commit_check.imperatives import IMPERATIVES


def _load_imperatives() -> set:
    """Load imperative verbs from imperatives module."""
    return IMPERATIVES


def get_default_commit_msg_file() -> str:
    """Get the default commit message file."""
    git_dir = cmd_output(['git', 'rev-parse', '--git-dir']).strip()
    return str(PurePath(git_dir, "COMMIT_EDITMSG"))


def read_commit_msg(commit_msg_file) -> str:
    """Read the commit message from the specified file."""
    try:
        with open(commit_msg_file, 'r') as f:
            return f.read()
    except FileNotFoundError:
        # Commit message is composed by subject and body
        return str(get_commit_info("s") + "\n\n" + get_commit_info("b"))


def check_commit_msg(checks: list, commit_msg_file: str = "") -> int:
    """Check commit message against the provided checks."""
    if has_commits() is False:
        return PASS # pragma: no cover

    if commit_msg_file is None or commit_msg_file == "":
        commit_msg_file = get_default_commit_msg_file()

    commit_msg = read_commit_msg(commit_msg_file)

    for check in checks:
        if check['check'] == 'message':
            if check['regex'] == "":
                print(
                    f"{YELLOW}Not found regex for commit message. skip checking.{RESET_COLOR}",
                )
                return PASS

            result = re.match(check['regex'], commit_msg)
            if result is None:
                if not print_error_header.has_been_called:
                    print_error_header() # pragma: no cover
                print_error_message(
                    check['check'], check['regex'],
                    check['error'], commit_msg,
                )
                if check['suggest']:
                    print_suggestion(check['suggest'])
                return FAIL

    return PASS


def check_commit_signoff(checks: list, commit_msg_file: str = "") -> int:
    if has_commits() is False:
        return PASS # pragma: no cover

    if commit_msg_file is None or commit_msg_file == "":
        commit_msg_file = get_default_commit_msg_file()

    for check in checks:
        if check['check'] == 'commit_signoff':
            if check['regex'] == "":
                print(
                    f"{YELLOW}Not found regex for commit signoff. skip checking.{RESET_COLOR}",
                )
                return PASS

            commit_msg = read_commit_msg(commit_msg_file)
            commit_hash = get_commit_info("H")
            result = re.search(check['regex'], commit_msg)
            if result is None:
                if not print_error_header.has_been_called:
                    print_error_header() # pragma: no cover
                print_error_message(
                    check['check'], check['regex'],
                    check['error'], commit_hash,
                )
                if check['suggest']:
                    print_suggestion(check['suggest'])
                return FAIL

    return PASS


def check_commit_gpg_signature(checks: list) -> int:
    """Check if commit has a valid GPG signature."""
    if has_commits() is False:
        return PASS # pragma: no cover

    for check in checks:
        if check['check'] == 'gpg_signature':
            # Get GPG signature status using git log --pretty=format:"%G?"
            try:
                gpg_status = cmd_output(['git', 'log', '--pretty=format:%G?', '-1']).strip()
                commit_hash = get_commit_info("H")

                # GPG status codes:
                # G = good (valid) signature
                # B = bad signature
                # U = good signature with unknown validity
                # X = good signature that has expired
                # Y = good signature made by an expired key
                # R = good signature made by a revoked key
                # E = signature cannot be checked (e.g., missing public key)
                # N = no signature

                if gpg_status not in ['G', 'U']:  # Only accept good signatures
                    if not print_error_header.has_been_called:
                        print_error_header() # pragma: no cover

                    error_msg = check['error']
                    if gpg_status == 'N':
                        error_msg = 'Commit is not signed with GPG'
                    elif gpg_status == 'B':
                        error_msg = 'Commit has a bad GPG signature'
                    elif gpg_status == 'E':
                        error_msg = 'GPG signature cannot be verified (missing public key?)'
                    elif gpg_status == 'X':
                        error_msg = 'GPG signature has expired'
                    elif gpg_status == 'Y':
                        error_msg = 'GPG signature made by an expired key'
                    elif gpg_status == 'R':
                        error_msg = 'GPG signature made by a revoked key'

                    print_error_message(
                        check['check'], f'GPG Status: {gpg_status}',
                        error_msg, commit_hash,
                    )
                    if check['suggest']:
                        print_suggestion(check['suggest'])
                    return FAIL

            except Exception:
                # If we can't check GPG status, treat as failure
                if not print_error_header.has_been_called:
                    print_error_header() # pragma: no cover
                print_error_message(
                    check['check'], 'Unknown',
                    'Unable to check GPG signature status', get_commit_info("H"),
                )
                if check['suggest']:
                    print_suggestion(check['suggest'])
                return FAIL

    return PASS


def check_imperative(checks: list, commit_msg_file: str = "") -> int:
    """Check if commit message uses imperative mood."""
    if has_commits() is False:
        return PASS # pragma: no cover

    if commit_msg_file is None or commit_msg_file == "":
        commit_msg_file = get_default_commit_msg_file()

    for check in checks:
        if check['check'] == 'imperative':
            commit_msg = read_commit_msg(commit_msg_file)

            # Extract the subject line (first line of commit message)
            subject = commit_msg.split('\n')[0].strip()

            # Skip if empty or merge commit
            if not subject or subject.startswith('Merge'):
                return PASS

            # For conventional commits, extract description after the colon
            if ':' in subject:
                description = subject.split(':', 1)[1].strip()
            else:
                description = subject

            # Check if the description uses imperative mood
            if not _is_imperative(description):
                if not print_error_header.has_been_called:
                    print_error_header() # pragma: no cover
                print_error_message(
                    check['check'], 'imperative mood pattern',
                    check['error'], subject,
                )
                if check['suggest']:
                    print_suggestion(check['suggest'])
                return FAIL

    return PASS


def _is_imperative(description: str) -> bool:
    """Check if a description uses imperative mood."""
    if not description:
        return True

    # Get the first word of the description
    first_word = description.split()[0].lower()

    # Load imperative verbs from file
    imperatives = _load_imperatives()

    # Check for common past tense pattern (-ed ending) but be more specific
    if (first_word.endswith('ed') and len(first_word) > 3 and
        first_word not in {'red', 'bed', 'fed', 'led', 'wed', 'shed', 'fled'}):
        return False

    # Check for present continuous pattern (-ing ending) but be more specific
    if (first_word.endswith('ing') and len(first_word) > 4 and
        first_word not in {'ring', 'sing', 'king', 'wing', 'thing', 'string', 'bring'}):
        return False

    # Check for third person singular (-s ending) but be more specific
    # Only flag if it's clearly a verb in third person singular form
    if first_word.endswith('s') and len(first_word) > 3:
        # Common nouns ending in 's' that should be allowed
        common_nouns_ending_s = {'process', 'access', 'address', 'progress', 'express', 'stress', 'success', 'class', 'pass', 'mass', 'loss', 'cross', 'gross', 'boss', 'toss', 'less', 'mess', 'dress', 'press', 'bless', 'guess', 'chess', 'glass', 'grass', 'brass'}

        # Words ending in 'ss' or 'us' are usually not third person singular verbs
        if first_word.endswith('ss') or first_word.endswith('us'):
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
