"""Clean validation engine following SOLID principles."""

from __future__ import annotations
import shlex
from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from enum import IntEnum
from dataclasses import field

from commit_check.rule_builder import ValidationRule
from commit_check.ai_signatures import (
    detect_ai_signatures,
)
from commit_check.util import (
    fetch_remote_ref,
    fetch_upstream_ref,
    get_commit_author_identity,
    get_commit_info,
    get_git_user_identity,
    get_git_config_value,
    get_branch_name,
    get_commit_files,
    get_push_commits,
    get_git_remotes,
    get_tags_at,
    format_size,
    get_upstream_branch,
    get_upstream_remote_sha,
    has_commits,
    git_merge_base,
    git_rev_parse_verify,
)
from commit_check.imperatives import IMPERATIVES, NON_IMPERATIVE_LOOKALIKES
from commit_check.fixes import (
    fix_branch_type,
    fix_conventional_header,
    fix_subject_case,
    fix_wip,
    signoff_trailer,
    strip_lines_containing,
)


class ValidationResult(IntEnum):
    """Validation result codes.

    ``SKIP`` means the validator declined to run — the author is on an
    ignore list, or there was nothing to check — as opposed to ``PASS``,
    which means the rule ran and found nothing to object to. Reporting a
    skip as a pass makes a bypassed policy indistinguishable from an
    enforced one, so the two are kept apart.

    Only ``FAIL`` is an error. ``validate_all`` returns ``PASS``/``FAIL``
    explicitly rather than propagating this value, so the new member never
    reaches an exit code.
    """

    PASS = 0
    FAIL = 1
    SKIP = 2


@dataclass(frozen=True)
class ValidationContext:
    """Context for validation operations."""

    stdin_text: str | None = None
    commit_file: str | None = None
    config: dict = field(default_factory=dict)
    no_banner: bool = False
    compact: bool = False
    push_upstream_fallback: bool = False
    # A git revision naming the commit under test. When set, message and
    # author checks read that commit -- the author is the commit's author,
    # never the local git config, because an existing commit's identity is
    # a fact about the commit rather than about whoever is running the
    # check. The CLI verifies the revision resolves before it gets here.
    # Last on purpose: positional construction predates it.
    rev: str | None = None
    # Per-run memo of get_commit_files() keyed by revision. The three file
    # rules each get their own validator, so without this they would re-run
    # the same git plumbing over the same commits three times.
    files_cache: dict[str, list[tuple[str, int]]] = field(
        default_factory=dict, repr=False, compare=False
    )


@dataclass
class CheckOutcome:
    """Structured result of a single validation check.

    Returned by :meth:`ValidationEngine.validate_all_detailed` so that
    callers (e.g. ``--format json`` output, the Python API) can inspect
    individual check results without parsing human-readable terminal output.
    """

    check: str
    # "pass" (the rule ran and was satisfied), "fail" (the rule ran and was
    # not), "warn" (the rule was not satisfied but is listed under ``warn``
    # in the config, so it is reported and does not fail the run), or "skip"
    # (the rule never ran — ignored author, or nothing to check). A skip is
    # not a pass: it means the policy was bypassed, and collapsing the two
    # lets a run that validated nothing report success.
    status: str
    # The concrete value that was checked (subject, branch, author, ...),
    # populated on both pass and fail so consumers can report what was
    # validated even when the check succeeded.
    value: str = ""
    error: str = ""
    suggest: str = ""
    # The corrected value when the fix is unambiguous (a type's case, a WIP
    # marker, a missing trailer); empty when fixing it takes a judgment the
    # tool should not make. Consumers can offer it as a one-step correction.
    fix: str = ""
    rule_id: str = ""
    docs_url: str = ""

    def to_dict(self) -> dict[str, str]:
        """Serialise to a plain dict (suitable for JSON encoding)."""
        return {
            "rule_id": self.rule_id,
            "check": self.check,
            "status": self.status,
            "value": self.value,
            "error": self.error,
            "suggest": self.suggest,
            "fix": self.fix,
            "docs_url": self.docs_url,
        }


def overall_status(statuses: Iterable[str]) -> str:
    """Reduce per-check statuses to one of ``"pass"``/``"fail"``/``"skip"``.

    Takes plain status strings rather than a specific type so that every
    caller can share it: the CLI's ``--format json`` and the API's
    :class:`CheckOutcome` objects, and the API's combined paths
    (``validate_author`` with both inputs, ``validate_all``) which merge
    already-serialised check dicts.

    That breadth is the point. This rule had been copied into four places,
    and each copy defaulted to ``"pass"`` for anything that was not a
    failure — which is how a fully skipped run kept reporting success even
    after the skip status existed.

    ``"skip"`` requires that *every* check skipped: a single real verdict
    means something was actually validated. Only ``"fail"`` is an error: a
    ``"warn"`` is a verdict the config asked to report without enforcing,
    so a run whose only findings are warnings passes.
    """
    seen = list(statuses)
    if any(s == "fail" for s in seen):
        return "fail"
    if seen and all(s == "skip" for s in seen):
        return "skip"
    return "pass"


def count_warnings(statuses: Iterable[str]) -> int:
    """How many checks were reported as warnings rather than failures."""
    return sum(1 for s in statuses if s == "warn")


class BaseValidator(ABC):
    """Abstract base validator."""

    def __init__(self, rule: ValidationRule):
        self.rule = rule
        # Set to True by the engine to suppress human-readable terminal
        # output while still collecting failure details: validate_all_detailed
        # never prints, validate_all prints the collected blocks itself once
        # every rule has run.
        self._suppress_output: bool = False
        # Used by _print_failure() when this validator prints for itself.
        self._no_banner: bool = False
        self._compact: bool = False
        # Populated by _print_failure() on every failure, regardless of mode.
        self._last_failure: dict[str, str] | None = None
        # The failure blocks as the printer takes them, (rule dict, value),
        # kept so the engine can print them after the banner.
        self._failure_blocks: list[tuple[dict, str]] = []
        # Populated by subclasses on every validation (pass or fail) with the
        # concrete value that was checked (subject, branch, author, ...), so
        # structured consumers (--format json, validate_all_detailed) can
        # report what was checked even when the check passed.
        self._checked_value: str = ""
        # Set by ValidationEngine.validate_all_detailed() to opt into value
        # collection. Text-mode validation skips the extra lookups (e.g. a
        # git subprocess for the branch name) and keeps values empty.
        self._collect_value: bool = False

    @abstractmethod
    def validate(self, context: ValidationContext) -> ValidationResult:
        """Perform validation and return result."""
        pass

    @staticmethod
    def _resolve_current_author(context: ValidationContext) -> str:
        """Resolve the relevant author identity based on validation mode.

        Two distinct modes:

        *Prospective message* (``stdin_text`` or ``commit_file`` is set):
        the user is about to create a new commit.  The last commit's author
        is unrelated — the relevant identity is the local git config
        (``user.name``), i.e. the person who will author the pending commit.

        *Existing commit* (no ``stdin_text``, no ``commit_file``):
        the last commit is the one being validated.  Use its own author
        (``get_commit_info("an")``), not the local git config which may
        belong to a different person.
        """
        if context.rev is not None:
            # An explicit revision names an existing commit; its author is a
            # fact about that commit, so the config never enters into it.
            return get_commit_info("an", context.rev)
        if context.stdin_text is not None or context.commit_file is not None:
            return get_git_config_value("user.name") or get_commit_info("an")
        return get_commit_info("an") or get_git_config_value("user.name")

    @staticmethod
    def _message_was_supplied(context: ValidationContext) -> bool:
        """Whether the caller named a message source rather than leaving it to git.

        Distinguishes "you asked me about this empty message" from "git had
        nothing to give me", which decide opposite answers: the first is a
        message that fails, the second is nothing to check.

        A commit_file that cannot be read counts as named even though the text
        then comes from git. That stays correct where it matters: the only way
        to reach an empty message from there is a HEAD commit whose message is
        genuinely empty, and rejecting that under allow_empty_commits = false
        is the verdict the rule exists to give.
        """
        return (
            context.stdin_text is not None
            or context.commit_file is not None
            or context.rev is not None
        )

    @staticmethod
    def _get_commit_message(context: ValidationContext) -> str:
        """Get commit message from context or git."""
        if context.stdin_text is not None:
            return context.stdin_text.strip()

        if context.commit_file:
            try:
                with open(context.commit_file, "r", encoding="utf-8") as f:
                    return f.read().strip()
            except FileNotFoundError:
                pass

        # Fallback to git log
        if context.rev is not None:
            subject = get_commit_info("s", context.rev)
            body = get_commit_info("b", context.rev)
        else:
            subject = get_commit_info("s")
            body = get_commit_info("b")
        return f"{subject}\n\n{body}".strip()

    def _author_in_ignore_list(self, context: ValidationContext) -> bool:
        """Check if the current author or any co-author is in the ignore list."""
        import re

        ignore_authors = context.config.get("commit", {}).get("ignore_authors", [])
        if not ignore_authors:
            return False

        current_author = self._resolve_current_author(context)
        if current_author and current_author in ignore_authors:
            return True

        # Check co-authors from the commit message body
        message = self._get_commit_body(context)
        if not message:
            return False

        co_authors = re.findall(
            r"^Co-authored-by:\s*([^<\n]+)\s*(?:<|$)",
            message,
            re.MULTILINE,
        )
        return any(co_author.strip() in ignore_authors for co_author in co_authors)

    @staticmethod
    def _get_commit_body(context: ValidationContext) -> str:
        """Retrieve the commit message body from context or git."""
        # An empty string is a message the caller supplied, not an absent one.
        # Reading it as absent sends the check off to the repository's HEAD
        # commit instead, so a caller asking about "" is answered about
        # whatever was committed last. The skip logic above already draws the
        # line at None; this follows it.
        if context.stdin_text is not None:
            return context.stdin_text
        if context.commit_file:
            try:
                with open(context.commit_file, "r", encoding="utf-8") as f:
                    return f.read()
            except (OSError, IOError):
                pass
        if context.rev is not None:
            return get_commit_info("b", context.rev)
        return get_commit_info("b")

    def _should_skip_commit_validation(self, context: ValidationContext) -> bool:
        """
        Determine if commit validation should be skipped.

        Skip if the current author or any co-author is in the ignore_authors list
        for commits, or if no stdin_text, no commit_file, and no commits exist.
        """
        if self._author_in_ignore_list(context):
            return True

        return (
            context.stdin_text is None
            and context.commit_file is None
            and context.rev is None
            and not has_commits()
        )

    def _should_skip_branch_validation(self, context: ValidationContext) -> bool:
        """
        Determine if branch validation should be skipped.

        Skip if the current author is in the ignore_authors list for branches,
        or if no stdin_text and no commits exist.
        """
        ignore_authors = context.config.get("branch", {}).get("ignore_authors", [])
        if ignore_authors:
            current_author = self._resolve_current_author(context)
            if current_author and current_author in ignore_authors:
                return True
        return context.stdin_text is None and not has_commits()

    def _print_failure(
        self,
        actual_value: str,
        *,
        error: str | None = None,
        fix: str | None = None,
        suggest: str | None = None,
    ) -> None:
        """Record and (unless suppressed) print a standardised failure message.

        ``error`` replaces the rule's static explanation when the validator
        knows more than the rule does at build time: the measured length, the
        tools it detected, whether the message under test is a commit yet.

        ``fix`` is the corrected value when the validator can name it without
        guessing; it replaces the rule's generic suggestion with a concrete
        one (``suggest`` overrides the wording) and travels to structured
        consumers as its own field.
        """
        rule_dict = self.rule.to_dict()
        if error is not None:
            rule_dict["error"] = error
        if fix or suggest:
            rule_dict["suggest"] = suggest or f'Use "{fix}"'

        # Always store structured failure details for programmatic consumers.
        self._last_failure = {
            "check": self.rule.check,
            "value": actual_value,
            "error": rule_dict["error"],
            "suggest": rule_dict.get("suggest") or self.rule.suggest or "",
            "fix": fix or "",
        }
        self._failure_blocks.append((rule_dict, actual_value))

        if not self._suppress_output:
            from commit_check.util import _print_failure

            _print_failure(
                rule_dict,
                actual_value,
                no_banner=self._no_banner,
                compact=self._compact,
            )


class CommitMessageValidator(BaseValidator):
    """Validates commit messages against conventional commit standards."""

    def validate(self, context: ValidationContext) -> ValidationResult:
        if self._should_skip_commit_validation(context):
            return ValidationResult.SKIP

        message = self._get_commit_message(context)
        if not message:
            return ValidationResult.PASS

        self._checked_value = message

        import re

        if self.rule.regex and re.match(self.rule.regex, message):
            return ValidationResult.PASS

        # Name the correction only when it is mechanical: a type's case or a
        # one-letter slip, a colon that went missing. The corrected header
        # has to satisfy the rule itself, or it is no fix at all.
        subject, newline, rest = message.partition("\n")
        fixed_subject = fix_conventional_header(subject, self.rule.allowed)
        fix = suggest = None
        if (
            fixed_subject
            and self.rule.regex
            and re.match(self.rule.regex, fixed_subject)
        ):
            fix = fixed_subject + newline + rest
            suggest = f'Use "{fixed_subject}"'
        self._print_failure(message, fix=fix, suggest=suggest)
        return ValidationResult.FAIL


class SubjectValidator(BaseValidator):
    """Validates commit subject lines."""

    def validate(self, context: ValidationContext) -> ValidationResult:
        if self._should_skip_commit_validation(context):
            return ValidationResult.SKIP

        subject = self._get_subject(context)
        if not subject:
            return ValidationResult.PASS

        self._checked_value = subject

        return self._validate_subject(subject)

    def _get_subject(self, context: ValidationContext) -> str:
        """Extract subject from commit message."""
        if context.stdin_text is not None:
            return context.stdin_text.strip().split("\n")[0]

        if context.commit_file:
            try:
                with open(context.commit_file, "r", encoding="utf-8") as f:
                    message = f.read().strip()
                    return message.split("\n")[0]
            except FileNotFoundError:
                pass

        if context.rev is not None:
            return get_commit_info("s", context.rev)
        return get_commit_info("s")

    def _validate_subject(self, _subject: str) -> ValidationResult:
        """Override in subclasses for specific validation logic."""
        return ValidationResult.PASS


class SubjectCapitalizationValidator(SubjectValidator):
    """Validates that subject starts with capital letter."""

    def _validate_subject(self, subject: str) -> ValidationResult:
        # A merge subject is machine-written; the rule declines to judge it.
        # Git writes "Merge " exactly, so anything else is author prose.
        if subject.startswith("Merge "):
            return ValidationResult.SKIP

        if self._is_capitalized(subject):
            return ValidationResult.PASS

        # The corrected subject has to pass this same check, or it is no fix.
        fix = fix_subject_case(subject, capitalize=True)
        if fix and not self._is_capitalized(fix):
            fix = None
        self._print_failure(subject, fix=fix)
        return ValidationResult.FAIL

    @staticmethod
    def _is_capitalized(subject: str) -> bool:
        """Whether the description starts upper-case, after any Conventional Commits prefix.

        Only a prefix that ends in a colon is a type. Without one, the first
        word is the description itself, so "Add feature" is judged on its
        "A" and not on the "f" that follows, and "Update" alone is judged at
        all.
        """
        import re

        match = re.match(r"^\w+(?:\([^)]*\))?!?:\s*(.*)", subject)
        description = match.group(1).strip() if match else subject
        return bool(description) and description[0].isupper()


class SubjectImperativeValidator(SubjectValidator):
    """Validates that subject uses imperative mood.

    Decides on the first word's form rather than its membership in a
    vocabulary: a past tense ("fixed"), a gerund ("adding") or a third person
    ("fixes") is not imperative, and nothing else disqualifies. A list can
    only reject correct subjects wherever it falls short, and it always does:
    on 59k strictly imperative subjects from git.git it rejected 45%, against
    1% here. See #526.

    The loosening is deliberate: a noun-led subject ("parser improvements")
    now passes, where the list rejected it by accident of vocabulary.
    """

    _INFLECTED = ("ed", "ing")

    def _validate_subject(self, subject: str) -> ValidationResult:
        # Merge and fixup subjects are machine-written; decline to judge them.
        # Git writes "Merge " and "fixup! " exactly, so anything else is
        # author prose.
        if subject.startswith(("Merge ", "fixup! ")):
            return ValidationResult.SKIP

        # Extract first word (ignore conventional commit prefixes)
        import re

        # support breaking changes (feat!:)
        match = re.match(r"^(?:\w+(?:\([^)]*\))?!?:\s*)?(\w+)", subject)
        if not match:
            return ValidationResult.PASS

        first_word = match.group(1).lower()

        if self._is_inflected(first_word):
            self._print_failure(subject)
            return ValidationResult.FAIL

        return ValidationResult.PASS

    @classmethod
    def _is_inflected(cls, word: str) -> bool:
        """Whether *word* carries past-tense, gerund or third-person marking."""
        if word in NON_IMPERATIVE_LOOKALIKES:
            return False
        if word.endswith(cls._INFLECTED):
            return True
        return cls._is_third_person(word)

    @classmethod
    def _is_third_person(cls, word: str) -> bool:
        """Whether *word* is a verb wearing the third-person singular -s.

        Unlike -ed and -ing, a trailing -s is weak evidence on its own --
        plural nouns wear one too ("status report") -- so it asks for
        corroboration: the stem has to be a verb we already know. "tests" is
        genuinely both, and this reads it as the verb.
        """
        # "address" and "process" end in -ss without being third person.
        if not word.endswith("s") or word.endswith("ss"):
            return False
        stems = {word[:-1]}
        if word.endswith("es"):
            stems.add(word[:-2])
        if word.endswith("ies"):
            stems.add(word[:-3] + "y")
        return any(stem in IMPERATIVES for stem in stems)


def _characters(count: int) -> str:
    """``count`` with its unit, singular or plural as the number demands."""
    return f"{count} character{'' if count == 1 else 's'}"


class SubjectLengthValidator(SubjectValidator):
    """Validates subject line length constraints."""

    def _validate_subject(self, subject: str) -> ValidationResult:
        # A merge subject's length is git's doing, not the author's.
        if subject.startswith("Merge "):
            return ValidationResult.SKIP

        length = len(subject)
        limit = self.rule.value

        if (
            (self.rule.check == "subject_max_length" and length <= limit)
            or (self.rule.check == "subject_min_length" and length >= limit)
            or self.rule.check not in ["subject_max_length", "subject_min_length"]
        ):
            return ValidationResult.PASS

        # "At most 20" states the rule; the measured length says how far off
        # the subject is, and the difference is what decides between trimming
        # a word and rewriting the line.
        if self.rule.check == "subject_max_length":
            error = f"Subject is {_characters(length)}; it must be at most {_characters(limit)}"
            suggest = f"Shorten the subject by {_characters(length - limit)}, to {limit} or fewer"
        else:
            error = f"Subject is {_characters(length)}; it must be at least {_characters(limit)}"
            suggest = f"Write a subject of at least {_characters(limit)} ({limit - length} more)"
        self._print_failure(subject, error=error, suggest=suggest)
        return ValidationResult.FAIL


class AuthorValidator(BaseValidator):
    """Validates author information."""

    def validate(self, context: ValidationContext) -> ValidationResult:
        # Use commit skip logic for ignore_authors
        if self._should_skip_commit_validation(context):
            return ValidationResult.SKIP

        author_value = self._get_author_value(context)
        if not author_value:
            return ValidationResult.PASS

        self._checked_value = author_value

        return self._validate_author(author_value)

    def _get_author_value(self, context: ValidationContext) -> str:
        """Get author value based on rule type.

        Checks git config first (for pre-commit validation of the configured identity),
        then falls back to the last commit's author info.
        """
        if context.stdin_text is not None:
            return context.stdin_text.strip()

        git_config_map = {
            "author_name": "user.name",
            "author_email": "user.email",
        }
        git_log_map = {
            "author_name": "an",
            "author_email": "ae",
        }

        # An explicit revision names an existing commit, whose identity is a
        # fact about the commit: read it from the commit and never from the
        # config, which describes whoever happens to be running the check.
        if context.rev is not None:
            format_str = git_log_map.get(self.rule.check, "")
            return get_commit_info(format_str, context.rev) if format_str else ""

        # Try git config first (validates configured identity for new commits)
        config_key = git_config_map.get(self.rule.check, "")
        if config_key:
            config_value = get_git_config_value(config_key)
            if config_value:
                return config_value

        # Fall back to last commit's author info
        format_str = git_log_map.get(self.rule.check, "")
        return get_commit_info(format_str) if format_str else ""

    def _validate_author(self, author_value: str) -> ValidationResult:
        """Validate author against rule constraints."""
        if self.rule.regex:
            import re

            if re.match(self.rule.regex, author_value):
                return ValidationResult.PASS
            self._print_failure(author_value)
            return ValidationResult.FAIL

        if self.rule.allowed and author_value not in self.rule.allowed:
            self._print_failure(author_value)
            return ValidationResult.FAIL

        if self.rule.ignored and author_value in self.rule.ignored:
            # An ignored author is a deliberate bypass, not a verdict.
            return ValidationResult.SKIP

        return ValidationResult.PASS


class BranchValidator(BaseValidator):
    """Validates branch names."""

    def validate(self, context: ValidationContext) -> ValidationResult:
        if self._should_skip_branch_validation(context):
            return ValidationResult.SKIP
        branch_name = (
            context.stdin_text.strip()
            if context.stdin_text is not None
            else get_branch_name()
        )
        self._checked_value = branch_name

        if not self.rule.regex:
            return ValidationResult.PASS

        import re

        if re.match(self.rule.regex, branch_name):
            return ValidationResult.PASS

        fixed = fix_branch_type(branch_name, self.rule.allowed)
        fix = suggest = None
        if fixed and re.match(self.rule.regex, fixed):
            fix = fixed
            suggest = (
                f'Rename the branch to "{fixed}" (git branch -m {shlex.quote(fixed)})'
            )
        self._print_failure(branch_name, fix=fix, suggest=suggest)
        return ValidationResult.FAIL


class TagValidator(BaseValidator):
    """Validates tag names.

    Checks every tag pointing at the revision under test (``--rev``, or
    ``HEAD``). A commit with no tag is a skip, not a failure: the rule
    validates how tags are named, and the absence of one is not a naming
    violation. Piped input (or an API-supplied value) names the tags to check
    directly, one per line, without consulting git.
    """

    @staticmethod
    def _tags_from_stdin(text: str) -> list[str]:
        """Extract tag names from piped input.

        Two shapes arrive here: bare tag names (API callers, ``echo v1 |``),
        and the four-field ``<local ref> <sha> <remote ref> <sha>`` lines a
        pre-push hook receives. For push lines the tags under push are the
        ``refs/tags/*`` refs — a push carrying no tag ref yields nothing to
        validate, and a deletion (all-zero local sha) removes a tag rather
        than naming a new one, so neither can fail the check.
        """
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        push_lines = [ln for ln in lines if len(ln.split()) == 4 and "refs/" in ln]
        if push_lines and len(push_lines) == len(lines):
            tags = []
            for ln in push_lines:
                local_ref, local_sha, remote_ref, _ = ln.split()
                if set(local_sha) == {"0"}:
                    continue
                for ref in (local_ref, remote_ref):
                    if ref.startswith("refs/tags/"):
                        tags.append(ref.removeprefix("refs/tags/"))
                        break
            return list(dict.fromkeys(tags))
        return lines

    def validate(self, context: ValidationContext) -> ValidationResult:
        if context.stdin_text is not None:
            tags = self._tags_from_stdin(context.stdin_text)
        else:
            tags = get_tags_at(context.rev or "HEAD")

        if not tags:
            return ValidationResult.SKIP

        self._checked_value = ", ".join(tags)

        if not self.rule.regex:
            return ValidationResult.PASS

        import re

        for tag in tags:
            if not re.match(self.rule.regex, tag):
                self._checked_value = tag
                self._print_failure(tag)
                return ValidationResult.FAIL

        return ValidationResult.PASS


class FilesValidator(BaseValidator):
    """Validates metadata about the files a commit touches.

    One class serves the three file rules — size limit, prohibited path
    patterns, path length — branching on the rule's check name. Only the
    paths and sizes recorded in the commit are read, never file contents:
    content scanning is a different tool's job. A commit touching no files
    (or an unresolvable revision) is a skip.
    """

    @staticmethod
    def _push_revs_from_stdin(text: str) -> list[str] | None:
        """Extract the commits a pre-push hook is being asked to approve.

        A native pre-push hook receives ``<local ref> <sha> <remote ref>
        <sha>`` lines naming what is being pushed; validating HEAD there
        would check the wrong commit whenever another ref is pushed. Both
        ends of each line matter: a push usually carries several commits,
        and checking only the tip would wave through a file added by any
        earlier commit in the same push.

        Deletions are skipped: an all-zero local sha removes content rather
        than adding it.

        Tags go through the same range as branches rather than being
        skipped. What matters is not whether a ref is a tag but whether it
        carries commits the remote lacks: a tag on already-pushed history
        resolves to an empty range, so ``git push --follow-tags`` is not
        rejected over a file committed long before, while a tag that is the
        only thing carrying a commit to the remote still gets that commit
        checked. Tag *names* remain CC401's business.

        Input of any other shape is not push metadata and returns ``None``,
        so the validator falls back to the revision under test.
        """
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        push_lines = [ln for ln in lines if len(ln.split()) == 4 and "refs/" in ln]
        if not push_lines or len(push_lines) != len(lines):
            return None
        revs: list[str] = []
        for ln in push_lines:
            _local_ref, local_sha, _remote_ref, remote_sha = ln.split()
            if set(local_sha) == {"0"}:
                continue
            revs.extend(get_push_commits(local_sha, remote_sha))
        return list(dict.fromkeys(revs))

    def _files_for_rev(
        self, context: ValidationContext, rev: str
    ) -> list[tuple[str, int]]:
        """Files touched by *rev*, computed once per run and shared."""
        if rev not in context.files_cache:
            context.files_cache[rev] = get_commit_files(rev)
        return context.files_cache[rev]

    def _revs_to_check(self, context: ValidationContext) -> list[str] | None:
        """Revisions this run should police.

        ``None`` means the push carried nothing to police — only deletions,
        or commits the remote already has — which the caller reports as a
        skip rather than a pass.
        """
        if context.stdin_text is not None:
            revs = self._push_revs_from_stdin(context.stdin_text)
            if revs is not None:
                return revs or None
        return [context.rev or "HEAD"]

    def _collect_files(
        self, context: ValidationContext, revs: list[str]
    ) -> list[tuple[str, int]]:
        """Files across *revs*, each one counted once.

        A file touched by several commits of the same push is one offender,
        not one per commit.
        """
        files: list[tuple[str, int]] = []
        seen: set[tuple[str, int]] = set()
        for rev in revs:
            for item in self._files_for_rev(context, rev):
                if item not in seen:
                    seen.add(item)
                    files.append(item)
        return files

    def validate(self, context: ValidationContext) -> ValidationResult:
        revs = self._revs_to_check(context)
        if revs is None:
            return ValidationResult.SKIP

        files = self._collect_files(context, revs)
        if not files:
            return ValidationResult.SKIP

        self._checked_value = f"{len(files)} file(s)"

        if self.rule.check == "file_size":
            return self._validate_sizes(files)
        if self.rule.check == "file_pattern":
            return self._validate_patterns(files)
        if self.rule.check == "path_length":
            return self._validate_path_lengths(files)
        return ValidationResult.PASS

    def _fail(self, offenders: list[str]) -> ValidationResult:
        """Report the first offender, with a count when there are more."""
        value = offenders[0]
        if len(offenders) > 1:
            value += f" (+{len(offenders) - 1} more)"
        self._checked_value = value
        self._print_failure(value)
        return ValidationResult.FAIL

    def _validate_sizes(self, files: list[tuple[str, int]]) -> ValidationResult:
        limit = self.rule.value
        offenders = [
            f"{path} ({format_size(size)})" for path, size in files if size > limit
        ]
        if offenders:
            return self._fail(offenders)
        return ValidationResult.PASS

    def _validate_patterns(self, files: list[tuple[str, int]]) -> ValidationResult:
        # fnmatch() folds case through os.path.normcase, which would make
        # "*.pem" catch KEY.PEM on Windows and miss it everywhere else --
        # one config, two policies. fnmatchcase() is the same on every
        # platform, and case-sensitive is what git pathspecs already are.
        from fnmatch import fnmatchcase

        patterns = self.rule.value or []
        offenders = []
        for path, _ in files:
            basename = path.rsplit("/", 1)[-1]
            hit = next(
                (
                    pattern
                    for pattern in patterns
                    # A bare pattern like *.pem should catch the file at any
                    # depth, so the basename is matched alongside the full
                    # path.
                    if fnmatchcase(path, pattern) or fnmatchcase(basename, pattern)
                ),
                None,
            )
            if hit:
                offenders.append(f"{path} (pattern {hit})")
        if offenders:
            return self._fail(offenders)
        return ValidationResult.PASS

    def _validate_path_lengths(self, files: list[tuple[str, int]]) -> ValidationResult:
        limit = self.rule.value
        offenders = [
            f"{path} ({len(path)} characters)" for path, _ in files if len(path) > limit
        ]
        if offenders:
            return self._fail(offenders)
        return ValidationResult.PASS


class MergeBaseValidator(BaseValidator):
    """Validates merge base ancestry."""

    def validate(self, context: ValidationContext) -> ValidationResult:
        if self._should_skip_branch_validation(context):
            return ValidationResult.SKIP

        current_branch = get_branch_name()
        target_pattern = self.rule.regex
        self._checked_value = current_branch

        if not target_pattern:
            return ValidationResult.PASS

        # Find target branch matching the pattern
        target_branch = self._find_target_branch(target_pattern)
        if not target_branch:
            return ValidationResult.PASS

        result = git_merge_base(target_branch, current_branch)
        if result == 128:
            # 128 is git failing to resolve a name, not an answer about
            # ancestry. A CI checkout of a pull request leaves a detached HEAD
            # with no local branch created, while get_branch_name() still
            # reports a name from GITHUB_HEAD_REF — so the name here refers to
            # nothing on disk. The remote-tracking ref is the real branch.
            result = git_merge_base(target_branch, f"origin/{current_branch}")
        if result == 128:
            # Last resort, when the branch is unresolvable under either name.
            # On a pull_request event HEAD is GitHub's synthetic merge commit,
            # whose first parent IS the target tip, so asking about HEAD would
            # pass every branch, rebased or not. Its *second* parent is the
            # pull request head — the commit actually under review — so ask
            # about that instead whenever HEAD is a merge. Where HEAD has a
            # single parent it is the branch commit itself (a push event, or a
            # branch that was never pushed) and answers for itself.
            source = "HEAD^2" if git_rev_parse_verify("HEAD^2") else "HEAD"
            result = git_merge_base(target_branch, source)
        if result == 0:
            return ValidationResult.PASS

        self._print_failure(current_branch)
        return ValidationResult.FAIL

    def _find_target_branch(self, pattern: str) -> str | None:
        """Find target branch by verifying refs directly.

        Uses ``git rev-parse --verify`` for exact ref resolution instead of
        scanning ``git branch -a`` output with a regex. Strips common regex
        anchors (``^``, ``$``) from the pattern to obtain a branch name,
        then attempts to verify it as a local ref first, falling back to
        the remote tracking ref under ``origin/``.

        :param pattern: The raw regex pattern from the rule config (e.g.
            ``"^main$"`` or ``"main"``).
        :returns: The resolved branch name if verified, ``None`` otherwise.
        """
        import subprocess

        # Strip common regex anchors to obtain a clean branch name
        branch_name = pattern.lstrip("^").rstrip("$").strip()
        if not branch_name:
            return None

        # Try local branch first (refs/heads/ avoids ambiguity with tags)
        try:
            subprocess.run(
                ["git", "rev-parse", "--verify", f"refs/heads/{branch_name}"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
            return branch_name
        except subprocess.CalledProcessError:
            pass

        # Try remote tracking branch under origin/
        try:
            subprocess.run(
                ["git", "rev-parse", "--verify", f"refs/remotes/origin/{branch_name}"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
            # Qualified with the remote, because that is the ref that was just
            # verified. Returning the bare name here made the caller run
            # ``git merge-base --is-ancestor main HEAD`` in a checkout that has
            # only ``origin/main``; git exits 128 on the unresolvable name and
            # the branch was reported as "not rebased onto target branch" when
            # it was correctly based all along. A CI checkout of a pull request
            # is exactly that shape.
            return f"origin/{branch_name}"
        except subprocess.CalledProcessError:
            pass

        return None


class SignoffValidator(BaseValidator):
    """Validates that commit messages contain required signoff trailer."""

    def validate(self, context: ValidationContext) -> ValidationResult:
        if self._should_skip_commit_validation(context):
            return ValidationResult.SKIP

        message = self._get_commit_message(context)
        if not message:
            return ValidationResult.PASS

        self._checked_value = message

        import re

        if self.rule.regex and re.search(self.rule.regex, message):
            return ValidationResult.PASS

        # In a commit-msg hook "the latest commit" is the previous one, which
        # does carry a sign-off, so name what was actually read: the message
        # under test, or the commit it came from.
        error = (
            "Signed-off-by trailer not found in the commit message"
            if self._is_pending_message(context)
            else "Signed-off-by trailer not found in the latest commit"
        )
        trailer = signoff_trailer(*self._resolve_author_identity(context))
        fix = suggest = None
        if trailer:
            fix = f"{message.rstrip()}\n\n{trailer}"
            suggest = f'Add the trailer "{trailer}" (git commit --signoff, or --amend --signoff for an existing commit)'
        self._print_failure(message, error=error, fix=fix, suggest=suggest)
        return ValidationResult.FAIL

    @staticmethod
    def _is_pending_message(context: ValidationContext) -> bool:
        """Whether the message describes a commit that does not exist yet."""
        return context.stdin_text is not None or context.commit_file is not None

    @classmethod
    def _resolve_author_identity(cls, context: ValidationContext) -> tuple[str, str]:
        """The (name, email) the sign-off would carry, by the same modes as the author.

        This runs only on a failure, but a hook still waits on it, so each
        mode asks git once and falls back to a second call only when the
        first left a part blank.
        """
        if context.rev is not None:
            return get_commit_author_identity(context.rev)
        pending = cls._is_pending_message(context)
        name, email = (
            get_git_user_identity() if pending else get_commit_author_identity()
        )
        if not name or not email:
            fallback_name, fallback_email = (
                get_commit_author_identity() if pending else get_git_user_identity()
            )
            name, email = name or fallback_name, email or fallback_email
        return name, email


class BodyValidator(BaseValidator):
    """Validates that commit messages contain a body when required."""

    def validate(self, context: ValidationContext) -> ValidationResult:
        if self._should_skip_commit_validation(context):
            return ValidationResult.SKIP

        message = self._get_commit_message(context)
        if not message:
            return ValidationResult.PASS

        self._checked_value = message

        # Split message into lines and check if there's content after the subject
        lines = message.strip().split("\n")

        # Filter out empty lines
        non_empty_lines = [line.strip() for line in lines if line.strip()]

        # If there's more than just the subject line, we have a body
        if len(non_empty_lines) > 1:
            return ValidationResult.PASS

        # Check if there's content after the first line (even if separated by empty lines)
        if len(lines) > 1:
            body_content = "\n".join(lines[1:]).strip()
            if body_content:
                return ValidationResult.PASS

        self._print_failure(message)
        return ValidationResult.FAIL


class ForcePushValidator(BaseValidator):
    """Validates that no force push is being performed.

    Reads pushed ref information from stdin (provided by git's pre-push hook)
    in the format::

        <local ref> <local sha1> <remote ref> <remote sha1>

    A force push is detected when the remote SHA is not an ancestor of the
    local SHA, meaning local history would overwrite the remote.
    """

    ZERO_SHA = "0000000000000000000000000000000000000000"

    def validate(self, context: ValidationContext) -> ValidationResult:
        # Emptiness, not absence, is the question here: unlike a message or a
        # branch name, stdin_text carries a *list* of refs, and no refs means
        # there is nothing to check either way. So this one stays a truth test
        # while the single-value readers above distinguish "" from None.
        if not context.stdin_text:
            if context.push_upstream_fallback:
                return self._check_current_branch_against_upstream()
            return ValidationResult.PASS

        for line in context.stdin_text.splitlines():
            result = self._check_push_line(line.strip())
            if result == ValidationResult.FAIL:
                return ValidationResult.FAIL

        return ValidationResult.PASS

    def _check_current_branch_against_upstream(self) -> ValidationResult:
        """Check whether pushing HEAD to its upstream would require force."""
        upstream_ref = get_upstream_branch()
        if not upstream_ref:
            return ValidationResult.PASS

        if self._collect_value:
            branch = get_branch_name()
            self._checked_value = f"{branch} -> {upstream_ref}"

        target_ref = get_upstream_remote_sha(upstream_ref) or upstream_ref
        returncode = git_merge_base(target_ref, "HEAD")
        if (
            returncode == 128
            and target_ref != upstream_ref
            and fetch_upstream_ref(upstream_ref)
        ):
            returncode = git_merge_base(target_ref, "HEAD")
        if returncode == 1:
            self._print_failure(f"{get_branch_name()} -> {upstream_ref}")
            return ValidationResult.FAIL

        return ValidationResult.PASS

    def _check_push_line(self, line: str) -> ValidationResult:
        """Check a single pushed ref line for force push."""
        if not line:
            return ValidationResult.PASS

        parts = line.split()
        if len(parts) < 4:
            return ValidationResult.PASS

        local_ref, local_sha, remote_ref, remote_sha = (
            parts[0],
            parts[1],
            parts[2],
            parts[3],
        )
        pair = f"{local_ref} -> {remote_ref}"
        # Accumulate every checked ref pair: a pre-push stdin may carry
        # several refs, and each one is validated individually.
        self._checked_value = (
            f"{self._checked_value}\n{pair}" if self._checked_value else pair
        )

        # Zero SHA for remote means a new branch push (not a force push)
        if remote_sha == self.ZERO_SHA:
            return ValidationResult.PASS

        # Check if the remote SHA is an ancestor of the local SHA.
        # returncode 0  -> remote is ancestor of local (fast-forward push, OK)
        # returncode 1  -> not an ancestor (force push detected)
        # returncode 128 -> SHA may be unknown locally; fetch remote ref and retry
        returncode = git_merge_base(remote_sha, local_sha)
        if returncode == 128:
            for remote in self._remote_candidates_for_push(remote_ref):
                if not fetch_remote_ref(remote, remote_ref):
                    continue
                returncode = git_merge_base(remote_sha, local_sha)
                if returncode != 128:
                    break
        if returncode == 1:
            self._print_failure(f"{local_ref} -> {remote_ref}")
            return ValidationResult.FAIL

        return ValidationResult.PASS

    def _remote_candidates_for_push(self, remote_ref: str) -> list[str]:
        """Return remotes worth fetching for a pushed branch ref."""
        if not remote_ref.startswith("refs/heads/"):
            return []

        remotes: list[str] = []
        upstream_ref = get_upstream_branch()
        upstream_parts = upstream_ref.split("/", 1)
        remote_branch = remote_ref.removeprefix("refs/heads/")
        if len(upstream_parts) == 2 and upstream_parts[1] == remote_branch:
            remotes.append(upstream_parts[0])

        remotes.extend(remote for remote in get_git_remotes() if remote not in remotes)
        return remotes


class CommitTypeValidator(BaseValidator):
    """Base validator for special commit types (merge, revert, fixup, WIP, empty)."""

    def validate(self, context: ValidationContext) -> ValidationResult:
        if self.rule.check == "ignore_authors":
            # The ignore_authors rule is about the commit author, not the
            # message; record it before the skip check so non-ignored
            # authors still carry the checked identity. An ignored author
            # means nothing was checked, so the value stays empty. The
            # author lookup only runs when structured consumers opt in.
            if self._collect_value:
                self._checked_value = self._resolve_current_author(context)
            if self._should_skip_commit_validation(context):
                self._checked_value = ""
                return ValidationResult.SKIP
        elif self._should_skip_commit_validation(context):
            return ValidationResult.SKIP

        message = self._get_commit_message(context)
        # allow_empty_commits is the rule that exists to judge an empty
        # message, so returning early on one made it unreachable: the branch
        # in _is_empty_commit_allowed that rejects an empty message could
        # never run. A message the caller supplied goes to the rule even when
        # it is empty; an empty one from git is still nothing to check.
        if not message and not self._message_was_supplied(context):
            # ignore_authors delivered its verdict above -- it judges the
            # author, so an absent message is no reason to disown it, and a
            # SKIP here would wrongly read as "author was bypassed".
            return (
                ValidationResult.PASS
                if self.rule.check == "ignore_authors"
                else ValidationResult.SKIP
            )

        self._checked_value = message

        # Check if this commit type is allowed based on rule configuration
        is_allowed = self._is_commit_type_allowed(message)

        if not is_allowed:
            fix = suggest = None
            if self.rule.check == "allow_wip_commits":
                fix = fix_wip(message)
                if fix:
                    suggest = f'Drop the WIP marker: "{fix.splitlines()[0]}"'
            self._print_failure(message, fix=fix, suggest=suggest)
            return ValidationResult.FAIL

        return ValidationResult.PASS

    def _is_commit_type_allowed(self, message: str) -> bool:
        """Check if the commit type is allowed based on the rule check."""
        check = self.rule.check

        if check == "allow_merge_commits":
            return self._is_merge_commit_allowed(message)
        elif check == "allow_revert_commits":
            return self._is_revert_commit_allowed(message)
        elif check == "allow_empty_commits":
            return self._is_empty_commit_allowed(message)
        elif check == "allow_fixup_commits":
            return self._is_fixup_commit_allowed(message)
        elif check == "allow_wip_commits":
            return self._is_wip_commit_allowed(message)

        return True

    def _is_merge_commit_allowed(self, message: str) -> bool:
        """Check if merge commits are allowed."""
        is_merge = message.startswith("Merge ")
        # If rule value is True, allow merge commits. If False, reject them.
        return not is_merge or self.rule.value

    def _is_revert_commit_allowed(self, message: str) -> bool:
        """Check if revert commits are allowed."""
        is_revert = message.lower().startswith("revert ")
        return not is_revert or self.rule.value

    def _is_empty_commit_allowed(self, message: str) -> bool:
        """Check if empty commits are allowed."""
        is_empty = not message.strip()
        return not is_empty or self.rule.value

    def _is_fixup_commit_allowed(self, message: str) -> bool:
        """Check if fixup commits are allowed."""
        is_fixup = message.startswith("fixup!")
        return not is_fixup or self.rule.value

    def _is_wip_commit_allowed(self, message: str) -> bool:
        """Check if WIP commits are allowed."""
        upper_msg = message.upper()
        is_wip = (
            upper_msg.startswith("WIP:")  # wip: / WIP:
            or upper_msg.startswith("[WIP]")  # [wip] / [WIP]
            or upper_msg.startswith("WIP ")  # WIP at start with space
            or upper_msg == "WIP"  # exact WIP
        )
        return not is_wip or self.rule.value


class AiAttributionValidator(BaseValidator):
    """Validates commit messages against AI attribution policy.

    Single responsibility: when configured to ``forbid``, rejects any commit
    that contains known AI tool signatures.  When set to ``ignore`` (the
    default), the check is a no-op.
    """

    def validate(self, context: ValidationContext) -> ValidationResult:
        if self._should_skip_commit_validation(context):
            return ValidationResult.SKIP

        message = self._get_commit_body(context)
        if not message:
            return ValidationResult.PASS

        policy = self.rule.value  # "ignore" | "forbid"
        if policy != "forbid":
            # No-op policy: nothing is checked, so no value is recorded.
            return ValidationResult.PASS

        signatures = detect_ai_signatures(message)
        if not signatures:
            # The message was scanned and no AI signature found.
            self._checked_value = message
            return ValidationResult.PASS

        tools = {s["tool"] for s in signatures}
        fix = strip_lines_containing(
            message, [s.get("matched_text", "") for s in signatures]
        )
        self._print_failure(
            ", ".join(sorted(tools)),
            error=f"AI-assisted commit is forbidden — detected tools: {', '.join(sorted(tools))}",
            suggest=(
                "This project forbids AI-assisted commits. Remove the AI trailer lines and re-commit."
                if fix
                else "This project forbids AI-assisted commits. Remove AI trailers and re-commit."
            ),
            fix=fix,
        )
        return ValidationResult.FAIL


class ValidationEngine:
    """Main validation engine that orchestrates all validations."""

    VALIDATOR_MAP: dict[str, type[BaseValidator]] = {
        "message": CommitMessageValidator,
        "subject_capitalized": SubjectCapitalizationValidator,
        "subject_imperative": SubjectImperativeValidator,
        "subject_max_length": SubjectLengthValidator,
        "subject_min_length": SubjectLengthValidator,
        "author_name": AuthorValidator,
        "author_email": AuthorValidator,
        "branch": BranchValidator,
        "merge_base": MergeBaseValidator,
        "require_signed_off_by": SignoffValidator,
        "require_body": BodyValidator,
        "allow_merge_commits": CommitTypeValidator,
        "allow_revert_commits": CommitTypeValidator,
        "allow_empty_commits": CommitTypeValidator,
        "allow_fixup_commits": CommitTypeValidator,
        "allow_wip_commits": CommitTypeValidator,
        "ignore_authors": CommitTypeValidator,
        "no_force_push": ForcePushValidator,
        "ai_attribution": AiAttributionValidator,
        "tag": TagValidator,
        "file_size": FilesValidator,
        "file_pattern": FilesValidator,
        "path_length": FilesValidator,
    }

    def __init__(self, rules: list[ValidationRule]):
        self.rules = rules

    def validate_all(self, context: ValidationContext) -> ValidationResult:
        """Run all validations, print the findings, and return the overall result.

        The failure blocks are printed once every rule has run, not as each
        rule fails: the banner above them names what was rejected, and that
        is only known once it is clear whether the failures are all about the
        commit, all about the branch, or spread across both.
        """
        failed, warned, skipped, blocks = self._run_validators(context)
        self._print_blocks(context, failed, blocks)
        self._print_notices(skipped, warned)
        # Only an enforced rule fails the run; a warning is reported and done.
        return ValidationResult.FAIL if failed else ValidationResult.PASS

    def _run_validators(
        self, context: ValidationContext
    ) -> tuple[list[str], list[str], list[str], list[tuple[dict, str]]]:
        """Run every rule with output held back.

        :returns: the checks that failed and are enforced, the ones that failed
            but only warn, the ones that were skipped (the last two in their
            display form), and the failure blocks for the printer in rule order.
        """
        failed: list[str] = []
        warned: list[str] = []
        skipped: list[str] = []
        blocks: list[tuple[dict, str]] = []

        for rule in self.rules:
            validator_class = self.VALIDATOR_MAP.get(rule.check)
            if not validator_class:
                continue  # Skip unknown validators

            validator: BaseValidator = validator_class(rule)
            validator._suppress_output = True  # printed later, after the banner
            result = validator.validate(context)
            blocks.extend(validator._failure_blocks)
            if result == ValidationResult.SKIP:
                skipped.append(rule.check.replace("_", "-"))
            elif result == ValidationResult.FAIL:
                if rule.severity == "warn":
                    warned.append(rule.check.replace("_", "-"))
                else:
                    failed.append(rule.check)

        return failed, warned, skipped, blocks

    @staticmethod
    def _print_blocks(
        context: ValidationContext, failed: list[str], blocks: list[tuple[dict, str]]
    ) -> None:
        """Print the banner, named for *failed*, then every failure block."""
        if not blocks:
            return

        from commit_check.util import (
            _print_failure,
            print_error_header,
            rejection_headline,
        )

        # Only an enforced failure earns the banner; a warning rejects
        # nothing. --compact and --no-banner keep it off entirely.
        if (
            failed
            and not context.no_banner
            and not context.compact
            and not print_error_header.has_been_called
        ):
            print_error_header(rejection_headline(failed))
        for rule_dict, value in blocks:
            _print_failure(
                rule_dict,
                value,
                no_banner=context.no_banner,
                compact=context.compact,
            )

    @staticmethod
    def _print_notices(skipped: list[str], warned: list[str]) -> None:
        """Name the skipped and the warning checks on stderr."""
        import sys

        if skipped:
            # A skipped check validated nothing, and a silent skip is
            # indistinguishable from a pass — which is how a merge commit at
            # HEAD once let a whole run report success having read nothing.
            # One line, stderr, so scripts parsing stdout are unaffected.
            print(
                f"⊘ skipped (not validated): {', '.join(skipped)}",
                file=sys.stderr,
            )

        if warned:
            # A warning was printed in full above; this one line says why the
            # run still passes, so a hook that exits 0 after red-looking output
            # is not mistaken for a broken hook.
            print(
                f"⚠ warnings (not enforced): {', '.join(warned)}",
                file=sys.stderr,
            )

    def validate_all_detailed(self, context: ValidationContext) -> list[CheckOutcome]:
        """Run all validations and return structured :class:`CheckOutcome` objects.

        Unlike :meth:`validate_all`, this method:

        * **Suppresses** all human-readable terminal output (ASCII art, colour).
        * Returns one :class:`CheckOutcome` per rule so callers can inspect or
          serialise individual check results (e.g. as JSON for AI agents).

        Example::

            engine = ValidationEngine(rules)
            outcomes = engine.validate_all_detailed(context)
            failed = [o for o in outcomes if o.status == "fail"]
        """
        outcomes: list[CheckOutcome] = []

        for rule in self.rules:
            validator_class = self.VALIDATOR_MAP.get(rule.check)
            if not validator_class:
                continue

            validator: BaseValidator = validator_class(rule)
            validator._suppress_output = True  # collect, don't print
            validator._collect_value = True  # report checked values on pass
            result = validator.validate(context)

            if result == ValidationResult.FAIL:
                failure = validator._last_failure or {}
                outcomes.append(
                    CheckOutcome(
                        check=rule.check,
                        status="warn" if rule.severity == "warn" else "fail",
                        value=failure.get("value", ""),
                        error=failure.get("error", ""),
                        suggest=failure.get("suggest", ""),
                        fix=failure.get("fix", ""),
                        rule_id=rule.rule_id or "",
                        docs_url=rule.docs_url or "",
                    )
                )
            else:
                # A skipped rule never ran, so it has no value to report and
                # must not be reported as a pass — see ValidationResult.SKIP.
                skipped = result == ValidationResult.SKIP
                outcomes.append(
                    CheckOutcome(
                        check=rule.check,
                        status="skip" if skipped else "pass",
                        value="" if skipped else (validator._checked_value or ""),
                        rule_id=rule.rule_id or "",
                        docs_url=rule.docs_url or "",
                    )
                )

        return outcomes
