"""Rule-driven commit message fixer. Zero LLM dependencies."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from commit_check.imperatives import IMPERATIVES
from commit_check.util import cmd_output


# Verbs where -ed suffix stripping alone fails (e.g. -ied forms).
# Only list genuinely tricky forms — regular -ed verbs (fixed→fix, added→add)
# are handled by the suffix rules in _to_imperative().
PAST_TO_IMPERATIVE: dict = {
    "simplified": "simplify",
    "applied": "apply",
    "modified": "modify",
    "unified": "unify",
    "verified": "verify",
    "specified": "specify",
    "classified": "classify",
    "notified": "notify",
}

# Canonical order for fix transforms (each operates on output of the previous).
_TRANSFORM_ORDER = [
    "allow_wip_commits",
    "subject_imperative",
    "subject_capitalized",
    "require_signed_off_by",
]

# Human-readable reasons for checks that cannot be auto-fixed.
_UNFIXABLE_REASONS: dict = {
    "message": "conventional commits type correction deferred to v2",
    "subject_max_length": "subject too long; shorten manually",
    "subject_min_length": "subject too short; expand manually",
    "require_body": "body required; add context manually",
    "allow_merge_commits": "cannot undo commit type",
    "allow_revert_commits": "cannot undo commit type",
    "allow_fixup_commits": "cannot undo fixup commit type",
    "allow_empty_commits": "cannot fix empty commit",
    "allow_wip_commits": "WIP: prefix removal yields empty subject",
}

# Regex for a conventional commit prefix (requires a colon).
# Matches: type[(scope)][!]:space(s)
_CONV_PREFIX_RE = re.compile(r"^(\w+(?:\([^)]*\))?[!]?:)(\s*)(.*)", re.DOTALL)

# Regex for extracting first word of description after an optional conventional prefix.
_CONV_FIRST_WORD_RE = re.compile(r"^(\w+(?:\([^)]*\))?[!]?:\s*)(\w+)(.*)", re.DOTALL)
_PLAIN_FIRST_WORD_RE = re.compile(r"^(\w+)(.*)", re.DOTALL)


@dataclass
class FixResult:
    """Result of a fix operation."""

    original_message: str
    fixed_message: str
    fixed: List[str] = field(default_factory=list)
    unfixable: List[Tuple[str, str]] = field(default_factory=list)


class CommitFixer:
    """Rule-driven commit message fixer. Zero LLM dependencies."""

    def fix(self, message: str, failed_checks: List[str]) -> FixResult:
        """Apply fix transforms in canonical order. Returns FixResult.

        Transforms run in _TRANSFORM_ORDER; each operates on the output of
        the previous. Checks not in _TRANSFORM_ORDER are reported unfixable.
        Unrecognized check names are silently skipped.
        """
        current = message
        fixed: List[str] = []
        unfixable: List[Tuple[str, str]] = []

        # Apply fixable transforms in canonical order.
        for check in _TRANSFORM_ORDER:
            if check not in failed_checks:
                continue
            new_msg, reason = self._apply_transform(check, current)
            if new_msg is None:
                unfixable.append(
                    (check, reason or _UNFIXABLE_REASONS.get(check, "cannot auto-fix"))
                )
            else:
                current = new_msg
                fixed.append(check)

        # Report remaining failed checks not handled above as unfixable.
        handled = {c for c in fixed} | {c for c, _ in unfixable}
        for check in failed_checks:
            if check not in handled:
                reason = _UNFIXABLE_REASONS.get(check, "cannot auto-fix")
                unfixable.append((check, reason))

        return FixResult(
            original_message=message,
            fixed_message=current,
            fixed=fixed,
            unfixable=unfixable,
        )

    # ------------------------------------------------------------------
    # Internal dispatch
    # ------------------------------------------------------------------

    def _apply_transform(
        self, check: str, message: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """Dispatch to the appropriate transform.

        Returns (new_message, None) on success, or (None, reason) if unfixable.
        """
        if check == "allow_wip_commits":
            return self._fix_wip(message)
        if check == "subject_imperative":
            return self._fix_imperative(message)
        if check == "subject_capitalized":
            return self._fix_capitalized(message)
        if check == "require_signed_off_by":
            return self._fix_signoff(message)
        return (None, "no transform available")

    # ------------------------------------------------------------------
    # Transforms
    # ------------------------------------------------------------------

    def _fix_wip(self, message: str) -> Tuple[Optional[str], Optional[str]]:
        """Strip WIP: prefix from the subject line.

        Matches exactly what CommitTypeValidator detects:
        message.upper().startswith("WIP:").
        """
        first_line, *rest = message.split("\n", 1)
        if not first_line.upper().startswith("WIP:"):
            return (message, None)  # check not applicable — no-op
        stripped = first_line[4:].strip()  # remove "WIP:" + leading whitespace
        if not stripped:
            return (None, "WIP: prefix removal yields empty subject")
        new_msg = "\n".join([stripped] + rest) if rest else stripped
        return (new_msg, None)

    def _fix_imperative(self, message: str) -> Tuple[Optional[str], Optional[str]]:
        """Convert first verb of subject to imperative mood."""
        first_line, *rest = message.split("\n", 1)

        # Try to match a conventional commit prefix (requires a colon).
        conv_m = _CONV_FIRST_WORD_RE.match(first_line)
        if conv_m:
            prefix = conv_m.group(1)  # e.g. "feat: " or "fix(scope)!: "
            first_word = conv_m.group(2)
            remainder = conv_m.group(3)  # rest of subject after first word
        else:
            # Plain commit — no conventional prefix.
            prefix = ""
            plain_m = _PLAIN_FIRST_WORD_RE.match(first_line)
            if not plain_m:
                return (None, "unknown verb form — fix manually")
            first_word = plain_m.group(1)
            remainder = plain_m.group(2)

        imperative = _to_imperative(first_word)
        if imperative is None:
            return (None, f"unknown verb form '{first_word}' — fix manually")

        # Preserve original capitalisation style (e.g. "Fixed" → "Fix").
        if first_word and first_word[0].isupper():
            imperative = imperative[0].upper() + imperative[1:]

        new_first = prefix + imperative + remainder
        new_msg = "\n".join([new_first] + rest) if rest else new_first
        return (new_msg, None)

    def _fix_capitalized(self, message: str) -> Tuple[Optional[str], Optional[str]]:
        """Capitalise the description part of the subject line."""
        first_line, *rest = message.split("\n", 1)

        conv_m = _CONV_PREFIX_RE.match(first_line)
        if conv_m:
            # Conventional commit: capitalise the description after "type: ".
            prefix_with_colon = conv_m.group(1)  # e.g. "feat:" or "fix(scope)!:"
            spaces = conv_m.group(2)  # whitespace after colon
            description = conv_m.group(3)  # rest of subject
            if not description:
                # Nothing to capitalise.
                return (message, None)
            fixed_desc = description[0].upper() + description[1:]
            new_first = prefix_with_colon + spaces + fixed_desc
        else:
            # Plain commit: capitalise the first character.
            if not first_line:
                return (message, None)
            new_first = first_line[0].upper() + first_line[1:]

        new_msg = "\n".join([new_first] + rest) if rest else new_first
        return (new_msg, None)

    def _fix_signoff(self, message: str) -> Tuple[Optional[str], Optional[str]]:
        """Append Signed-off-by trailer using git config user.name / user.email."""
        name = cmd_output(["git", "config", "user.name"]).strip()
        email = cmd_output(["git", "config", "user.email"]).strip()
        if not name or not email:
            return (
                None,
                "git user identity not configured"
                " (run: git config user.name / git config user.email)",
            )
        signoff = f"Signed-off-by: {name} <{email}>"
        new_msg = message.rstrip("\n") + f"\n\n{signoff}"
        return (new_msg, None)


# ------------------------------------------------------------------
# Verb form helpers
# ------------------------------------------------------------------


def _to_imperative(word: str) -> Optional[str]:
    """Try to convert *word* to its imperative form.

    Priority order:
      3a. PAST_TO_IMPERATIVE table  (-ied forms and other tricky cases)
      3b. -ed suffix rule           (fixed→fix, added→add)
      3c. -ing suffix rule          (adding→add, running→run)
      3d. -s/-es suffix rule        (fixes→fix, adds→add)

    Returns None if the form cannot be determined.
    """
    lower = word.lower()

    # Step 3a: explicit table lookup.
    if lower in PAST_TO_IMPERATIVE:
        return PAST_TO_IMPERATIVE[lower]

    # Step 3b: -ed suffix.
    if lower.endswith("ed") and len(lower) > 4:
        stem = lower[:-2]
        if len(stem) >= 3 and stem in IMPERATIVES:
            return stem

    # Step 3c: -ing suffix.
    if lower.endswith("ing") and len(lower) > 5:
        stem = lower[:-3]
        # Direct IMPERATIVES check (e.g. "adding" → "add").
        if len(stem) >= 3 and stem in IMPERATIVES:
            return stem
        # Doubled-consonant de-gemination (e.g. "running" → "runn" → "run").  # codespell:ignore runn
        if len(stem) >= 2:
            vowels = set("aeiou")
            last = stem[-1]
            if last == stem[-2] and last.isalpha() and last not in vowels:
                undoubled = stem[:-1]
                if len(undoubled) >= 3 and undoubled in IMPERATIVES:
                    return undoubled

    # Step 3d: -es then -s suffix.
    if lower.endswith("es") and len(lower) > 4:
        stem = lower[:-2]
        if len(stem) >= 3 and stem in IMPERATIVES:
            return stem
    if lower.endswith("s") and len(lower) > 3:
        stem = lower[:-1]
        if len(stem) >= 3 and stem in IMPERATIVES:
            return stem

    return None
