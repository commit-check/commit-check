"""A commit message read against the ``disclose`` AI attribution policy.

``ai_attribution = "disclose"`` welcomes AI assistance on three conditions,
each its own rule so a project can warn on one while enforcing the others:

* it is disclosed with one of the project's trailers (CC014);
* the tool is not credited as a co-author (CC015);
* the tool does not sign off the commit (CC016).

Nothing here can see assistance that left no trace, so the first condition
is judged on the traces there are: a co-author line, a sign-off, a vendor's
own mark, a disclosure written with some other trailer. Any of those without
an accepted disclosure is a commit that says "AI was here" in every way but
the one the project asked for.

Everything in this module is pure: no git, no output. The validator in
:mod:`commit_check.engine` turns a report into a verdict.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

from commit_check.ai_signatures import detect_ai_signatures, find_trailers
from commit_check.ai_signatures_data import (
    GENERIC_AI,
    PERSON_TRAILERS,
    ROLE_CO_AUTHOR,
    ROLE_DISCLOSURE,
    ROLE_SIGNOFF,
)
from commit_check.fixes import append_trailer, rewrite_lines

#: One signature as :func:`detect_ai_signatures` reports it.
Signature = dict[str, str]

_PERSON_KEYS = frozenset(key.lower() for key in PERSON_TRAILERS)


@dataclass(frozen=True)
class Disclosure:
    """A trailer with an accepted key, and whether it counts."""

    key: str  # as written in the message
    value: str
    line: str
    # Why it does not count: "empty" (no value), "pattern" (the value does
    # not match ai_disclosure_pattern); "" when it does.
    problem: str = ""

    @property
    def ok(self) -> bool:
        return not self.problem


@dataclass(frozen=True)
class AiPolicyReport:
    """What one message says about AI assistance, sorted by what each rule asks."""

    disclosures: list[Disclosure]
    #: The tool credited under a person trailer the project does not accept
    #: as a disclosure.
    co_author_lines: list[Signature]
    #: The tool certifying the Developer Certificate of Origin.
    signoff_lines: list[Signature]
    #: A disclosure written with a trailer the project does not accept.
    other_disclosures: list[Signature]
    #: A vendor's own mark: a "Generated with" line, a session-ID trailer.
    stamps: list[Signature]

    @property
    def disclosed(self) -> bool:
        """Whether an accepted, well-formed disclosure is present."""
        return any(d.ok for d in self.disclosures)

    @property
    def malformed(self) -> list[Disclosure]:
        return [d for d in self.disclosures if d.problem]

    @property
    def evidence(self) -> list[Signature]:
        """Every sign of AI assistance that is not itself an accepted disclosure."""
        return [
            *self.co_author_lines,
            *self.signoff_lines,
            *self.other_disclosures,
            *self.stamps,
        ]

    @property
    def undisclosed(self) -> bool:
        """AI assistance shows, and no accepted disclosure says so."""
        return bool(self.evidence) and not self.disclosed

    @property
    def compliant(self) -> bool:
        return not (
            self.undisclosed
            or self.malformed
            or self.co_author_lines
            or self.signoff_lines
        )


def analyze(message: str, accepted: list[str], pattern: str = "") -> AiPolicyReport:
    """Read *message* under a policy accepting the *accepted* trailers.

    :param accepted: The trailer keys that disclose AI assistance, in the
        project's spelling; matched case-insensitively.
    :param pattern: A regex the disclosure's value must match from its
        start (``re.match``), or empty for any non-empty value.

    The three rules of the policy each ask about the same message under the
    same settings, so the reading is memoised and done once. The report and
    the lists it holds are shared between them and are never modified.
    """
    return _analyze(message, tuple(accepted), pattern)


@lru_cache(maxsize=8)
def _analyze(message: str, accepted: tuple[str, ...], pattern: str) -> AiPolicyReport:
    """:func:`analyze`, with the arguments in a form a cache can key on."""
    accepted_keys = list(accepted)
    signatures = detect_ai_signatures(message)
    ai_lines = {s["matched_text"] for s in signatures}

    disclosures: list[Disclosure] = []
    for key, value, line in find_trailers(message, accepted_keys):
        line = line.strip()
        # A person trailer discloses a tool only when its value names one:
        # a human co-author under an accepted key is a co-author, not a
        # disclosure.
        if key.lower() in _PERSON_KEYS and line not in ai_lines:
            continue
        if not value:
            problem = "empty"
        elif pattern and not re.match(pattern, value):
            problem = "pattern"
        else:
            problem = ""
        disclosures.append(Disclosure(key, value, line, problem))
    disclosure_lines = {d.line for d in disclosures}

    co_authors: list[Signature] = []
    signoffs: list[Signature] = []
    others: list[Signature] = []
    stamps: list[Signature] = []
    for signature in signatures:
        if signature["matched_text"] in disclosure_lines:
            continue
        role = signature["role"]
        if role == ROLE_CO_AUTHOR:
            co_authors.append(signature)
        elif role == ROLE_SIGNOFF:
            signoffs.append(signature)
        elif role == ROLE_DISCLOSURE:
            others.append(signature)
        else:
            stamps.append(signature)
    return AiPolicyReport(disclosures, co_authors, signoffs, others, stamps)


def _disclosed_value(signature: Signature) -> str:
    """What the disclosure written for *signature* should say.

    The name the tool gave itself, minus any email — the most specific thing
    the commit already carries ("Claude Opus 4.5" rather than "Claude Code")
    — and the name it is known by when the line has none.
    """
    if signature["role"] == ROLE_DISCLOSURE:
        return signature["value"]
    name = signature["value"].split("<", 1)[0].strip()
    return name or signature["tool"]


def propose_fix(
    message: str, report: AiPolicyReport, accepted: list[str], pattern: str = ""
) -> str | None:
    """The message corrected to comply, or ``None`` when that takes a guess.

    A line that credits the tool as a person, or discloses it with a trailer
    the project does not accept, becomes the disclosure when the message has
    none and goes when it has one. A vendor's own mark is left where it is —
    it is not what the policy objects to — and the disclosure is added
    beside it. A disclosure someone wrote badly is theirs to rewrite: which
    model, in which format, is not this tool's to guess.

    The result is read again under the same policy before it is offered, so
    a correction that would still fail is never named.
    """
    if report.compliant or report.malformed:
        return None
    key = accepted[0]
    needed = not report.disclosed
    rewrites: dict[str, str | None] = {}
    for signature in (
        *report.co_author_lines,
        *report.signoff_lines,
        *report.other_disclosures,
    ):
        rewrites[signature["matched_text"]] = (
            f"{key}: {_disclosed_value(signature)}" if needed else None
        )
    fixed = (rewrite_lines(message, rewrites) if rewrites else None) or message
    if needed and not rewrites:
        # Only a vendor's mark says a tool was here, so nothing is rewritten
        # and the disclosure is added. A mark that names no particular tool
        # gives nothing to write after the key.
        tools = list(dict.fromkeys(s["tool"] for s in report.stamps))
        if GENERIC_AI.name in tools:
            return None
        for tool in tools:
            fixed = append_trailer(fixed, f"{key}: {tool}")
    if fixed == message or not analyze(fixed, accepted, pattern).compliant:
        return None
    return fixed
