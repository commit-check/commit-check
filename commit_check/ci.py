"""Check the merge or pull request a CI job runs for: ``commit-check-ci``.

GitHub has the Commit Check Action for this. On GitLab CI and Bitbucket
Pipelines a job runs this command instead: it finds the request from the
variables the CI system sets, and runs ``commit-check`` on the source branch,
on the request's title and description, and once for every commit the request
adds.

Each check is switched on or off by an option named after the Action's input:
``--author-email`` or ``--author-email=true`` to run it, ``--message=false``
to leave it out. The ``=true`` and ``=false`` forms are there for CI templates,
which fill in a value.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from .config_merger import ConfigMerger
from .main import _VersionAction

# Option name -> on by default. The names are the Action's input names.
CHECKS: dict[str, bool] = {
    "message": True,
    "branch": True,
    "author-name": False,
    "author-email": False,
    "files": False,
    "pr-title": False,
    "pr-body-ai-attribution": False,
}

# The checks that run once for every commit, with the commit-check flag each one is.
COMMIT_CHECKS = ("message", "author-name", "author-email", "files")

HELP = {
    "message": "check the message of every commit the request adds",
    "branch": "check the name of the source branch",
    "author-name": "check the author name of every commit",
    "author-email": "check the author email of every commit",
    "files": "check the files every commit changes against the [files] rules",
    "pr-title": "check the title against the commit message rules",
    "pr-body-ai-attribution": (
        "check the description against the AI attribution rules"
    ),
}

BITBUCKET_API = "https://api.bitbucket.org/2.0"

# GitLab passes at most this much of a description to a job.
GITLAB_DESCRIPTION_LIMIT = 2700

# What marks a GitLab merge request as a draft. A draft cannot be merged, so
# the marker is never part of the title that lands.
GITLAB_DRAFT_MARKER = re.compile(
    r"\A\s*(?:(?:\[draft\]|\(draft\)|draft:)\s*)+", re.IGNORECASE
)


class Stop(Exception):
    """The job cannot do what it was asked; the message says why."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse every redirect: one would carry the access token elsewhere."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        raise urllib.error.URLError(f"redirect to {newurl} refused")


@dataclass(frozen=True)
class Request:
    """The merge or pull request this job runs for."""

    forge: str
    noun: str
    target: str
    """The branch it merges into."""
    base: str
    """The commit its own commits start after."""
    head: str
    """Its own last commit, which is not always the commit checked out."""


def parse_bool(option: str, text: str) -> bool:
    value = text.strip().lower()
    if value == "true":
        return True
    if value == "false":
        return False
    raise Stop(f"--{option} must be true or false, got {text!r}")


def read_settings(argv: Sequence[str] | None) -> dict[str, bool]:
    """Which checks to run: the option when it is given, else the default."""
    parser = argparse.ArgumentParser(
        prog="commit-check-ci",
        description=(
            "Check the merge or pull request this CI job runs for, on GitLab CI "
            "or Bitbucket Pipelines: the source branch, the title, the "
            "description, and every commit the request adds. Outside a merge or "
            "pull request it checks the branch and the last commit."
        ),
        epilog=(
            "Rules come from cchk.toml, as for commit-check. On Bitbucket the "
            "title and description are read from its API with the access token "
            "in $BITBUCKET_ACCESS_TOKEN. Docs: https://commit-check.com/"
        ),
        allow_abbrev=False,
    )
    parser.add_argument("-v", "--version", action=_VersionAction)
    for option, default in CHECKS.items():
        parser.add_argument(
            f"--{option}",
            nargs="?",
            const="true",
            metavar="true|false",
            help=f"{HELP[option]} (default: {str(default).lower()})",
        )
    args = vars(parser.parse_args(argv))
    settings = {}
    for option, default in CHECKS.items():
        given = args[option.replace("-", "_")]
        settings[option] = default if given is None else parse_bool(option, given)
    return settings


def find_request(env: Mapping[str, str]) -> Request | None:
    """The merge or pull request named by the CI system's variables."""
    if env.get("CI_MERGE_REQUEST_IID"):
        return Request(
            forge="GitLab",
            noun="merge request",
            target=env.get("CI_MERGE_REQUEST_TARGET_BRANCH_NAME", ""),
            base=env.get("CI_MERGE_REQUEST_DIFF_BASE_SHA", ""),
            # A merged results pipeline checks out a merge commit GitLab made
            # and names the request's own last commit here. In any other merge
            # request pipeline this is empty and the checkout is that commit.
            head=env.get("CI_MERGE_REQUEST_SOURCE_BRANCH_SHA")
            or env.get("CI_COMMIT_SHA", ""),
        )
    if env.get("BITBUCKET_PR_ID"):
        return Request(
            forge="Bitbucket",
            noun="pull request",
            target=env.get("BITBUCKET_PR_DESTINATION_BRANCH", ""),
            base=env.get("BITBUCKET_PR_DESTINATION_COMMIT", ""),
            # Bitbucket merges the destination into the checkout before the
            # step runs; this is the pull request's own last commit.
            head=env.get("BITBUCKET_COMMIT", ""),
        )
    return None


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def resolve_commit(rev: str) -> str:
    """The full id of the commit ``rev`` names, or ``""`` when the clone lacks it."""
    if not rev:
        return ""
    result = git(
        "rev-parse", "--verify", "--quiet", "--end-of-options", f"{rev}^{{commit}}"
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def subject_of(rev: str) -> str:
    """The commit's subject line, safe to print: it is text anyone can write."""
    subject = git("log", "-1", "--format=%s", "--end-of-options", rev).stdout.strip()
    return "".join(char if char.isprintable() else "?" for char in subject)


def is_ancestor(commit: str, of: str) -> bool:
    return git("merge-base", "--is-ancestor", commit, of).returncode == 0


def shallow_ends() -> set[str]:
    """The commits a shallow clone stops at: their parents were not fetched."""
    path = git("rev-parse", "--git-path", "shallow").stdout.strip()
    try:
        return set(Path(path).read_text(encoding="ascii").split())
    except OSError:
        return set()


def shallow_hint(request: Request) -> str:
    if git("rev-parse", "--is-shallow-repository").stdout.strip() != "true":
        return ""
    if request.forge == "GitLab":
        return ' The clone is shallow: set GIT_DEPTH to "0" for this job.'
    return " The clone is shallow: set `clone: depth: full` on this step."


def rebase_check_is_on() -> bool:
    """Whether ``require_rebase_target`` is set, by the file or the environment.

    It is the one rule that reads the target branch.
    """
    try:
        config = ConfigMerger.from_all_sources(argparse.Namespace())
    except (OSError, ValueError):
        # commit-check says what is wrong with the configuration when it runs.
        return True
    branch = config.get("branch")
    return isinstance(branch, dict) and bool(branch.get("require_rebase_target"))


def prepare_target(request: Request, env: Mapping[str, str]) -> None:
    """Make ``origin/<target>`` exist, which the rebase check (CC202) reads.

    Neither system fetches the target branch for a merge or pull request.
    Without it the rule reports itself as skipped and the job would pass with
    a branch that was never compared.
    """
    if not request.target:
        raise Stop(f"the {request.noun}'s target branch is not set in the environment")
    ref = f"refs/remotes/origin/{request.target}"
    if request.forge == "GitLab":
        # A pipeline that runs in a fork has the fork as origin; the target
        # branch lives in the project the merge request was opened against.
        source = "origin"
        target_project = env.get("CI_MERGE_REQUEST_PROJECT_ID")
        if target_project and target_project != env.get("CI_PROJECT_ID"):
            source = env.get("CI_MERGE_REQUEST_PROJECT_URL", "") + ".git"
        fetch = git(
            "fetch",
            "--quiet",
            "--no-tags",
            source,
            f"+refs/heads/{request.target}:{ref}",
        )
        if fetch.returncode != 0:
            raise Stop(
                f"could not fetch the target branch {request.target!r} from {source}, "
                f"which the rebase check needs: {fetch.stderr.strip()}"
            )
        return
    # Nothing is fetched on Bitbucket: the step already merged the destination
    # commit into the checkout, so the clone holds it.
    commit = resolve_commit(request.base)
    if not commit:
        raise Stop(
            f"the destination commit {request.base!r} is not in the clone, "
            f"so the rebase check has nothing to compare with.{shallow_hint(request)}"
        )
    if resolve_commit(ref) and is_ancestor(commit, ref):
        # The clone's own ref is at the destination commit or past it. One
        # that is behind it would let a branch pass that is not rebased.
        return
    update = git("update-ref", ref, commit)
    if update.returncode != 0:
        raise Stop(f"could not write {ref}: {update.stderr.strip()}")


def request_commits(request: Request) -> list[str]:
    """The commits the request adds, oldest first."""
    result = git(
        "rev-list", "--reverse", "--end-of-options", f"{request.base}..{request.head}"
    )
    if not request.base or not request.head or result.returncode != 0:
        raise Stop(
            f"could not list the {request.noun}'s commits "
            f"({request.base or '?'}..{request.head or '?'}).{shallow_hint(request)}"
        )
    commits = result.stdout.split()
    # git lists a range that runs into the end of a shallow clone without an
    # error: the commits beyond it are simply absent, and would go unchecked.
    if shallow_ends().intersection(commits):
        raise Stop(
            f"the clone ends inside the {request.noun}, so its older commits "
            f"cannot be read.{shallow_hint(request)}"
        )
    return commits


def bitbucket_pull_request(env: Mapping[str, str]) -> dict[str, object]:
    """Read the pull request from the Bitbucket API, which is where its text is."""
    token = env.get("BITBUCKET_ACCESS_TOKEN", "").strip()
    if not token:
        raise Stop(
            "Bitbucket does not pass a pull request's title or description to "
            "the step. Set BITBUCKET_ACCESS_TOKEN to an access token with the "
            "Pull requests: Read scope so they can be read from the API."
        )
    repository = env.get("BITBUCKET_REPO_FULL_NAME") or "/".join(
        (
            env.get("BITBUCKET_WORKSPACE") or env.get("BITBUCKET_REPO_OWNER", ""),
            env.get("BITBUCKET_REPO_SLUG", ""),
        )
    )
    number = env.get("BITBUCKET_PR_ID", "")
    if (
        not number.isdigit()
        or repository.count("/") != 1
        or "" in repository.split("/")
    ):
        raise Stop("the pull request's repository or id is not set in the environment")
    api_request = urllib.request.Request(
        f"{BITBUCKET_API}/repositories/{repository}/pullrequests/{number}",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    try:
        with urllib.request.build_opener(NoRedirect()).open(
            api_request, timeout=30
        ) as response:
            pull_request = json.load(response)
    except (urllib.error.URLError, TimeoutError, ValueError) as error:
        raise Stop(
            f"could not read the pull request from the Bitbucket API: {error}"
        ) from None
    if not isinstance(pull_request, dict):
        raise Stop("the Bitbucket API did not return a pull request")
    return pull_request


class Job:
    """Runs the checks and remembers the worst result."""

    def __init__(self, settings: dict[str, bool], env: Mapping[str, str]) -> None:
        self.settings = settings
        self.env = env
        self.ran = 0
        self.failed = 0
        self.exit_code = 0
        self._pull_request: dict[str, object] | None = None

    def check(self, heading: str, args: list[str], text: str | None = None) -> None:
        """Run one ``commit-check`` call under a heading of its own."""
        print(heading, flush=True)
        result = subprocess.run(
            # -P: -m would otherwise put the working directory, which is the
            # request's checkout, ahead of the installed package and the
            # standard library on the module search path.
            [sys.executable, "-P", "-m", "commit_check.main", *args, "--no-banner"],
            # A check that is given no text reads none: whatever the runner
            # left on standard input is not the branch name or the message.
            input=b"" if text is None else text.encode("utf-8"),
            check=False,
        )
        self.ran += 1
        if result.returncode == 0:
            print("  passed", flush=True)
            return
        self.failed += 1
        # A commit-check killed by a signal reports a negative code; it failed too.
        self.exit_code = max(self.exit_code, result.returncode, 1)

    def stop(self, heading: str, error: Stop) -> None:
        """Count a check that could not run as failed, and say why."""
        print(heading, flush=True)
        print(f"  Error: {error}", flush=True)
        self.ran += 1
        self.failed += 1
        self.exit_code = max(self.exit_code, 1)

    def request_text(self, request: Request, field: str) -> str:
        """The request's ``title`` or ``description``."""
        if request.forge == "GitLab":
            text = self.env.get(f"CI_MERGE_REQUEST_{field.upper()}", "")
            return GITLAB_DRAFT_MARKER.sub("", text) if field == "title" else text
        if self._pull_request is None:
            self._pull_request = bitbucket_pull_request(self.env)
        value = self._pull_request.get(field)
        return value if isinstance(value, str) else ""

    def run(self) -> int:
        request = find_request(self.env)
        if request is None:
            self.run_without_request()
        else:
            self.run_for(request)
        if self.ran == 0:
            print("Every check is switched off; nothing was checked.", flush=True)
        elif self.failed:
            print(f"\n{self.failed} of {self.ran} failed.", flush=True)
        else:
            print(f"\nAll {self.ran} passed.", flush=True)
        return self.exit_code

    def run_for(self, request: Request) -> None:
        if self.settings["branch"]:
            self.check_branch(request)
        if self.settings["pr-title"]:
            self.check_title(request)
        if self.settings["pr-body-ai-attribution"]:
            self.check_description(request)
        flags = [f"--{name}" for name in COMMIT_CHECKS if self.settings[name]]
        if flags:
            self.check_commits(request, flags)

    def check_branch(self, request: Request) -> None:
        try:
            prepare_target(request, self.env)
        except Stop as error:
            # Only the rebase check reads the target branch. A pipeline that
            # runs in a fork of a private project cannot fetch it at all, and
            # without that rule there is nothing the fetch was needed for.
            if rebase_check_is_on():
                self.stop("Branch", error)
                return
        self.check("Branch", ["--branch"])

    def check_title(self, request: Request) -> None:
        heading = f"{request.noun.capitalize()} title"
        try:
            title = self.request_text(request, "title")
        except Stop as error:
            self.stop(heading, error)
            return
        self.check(heading, ["--pr-title"], text=title + "\n")

    def check_description(self, request: Request) -> None:
        heading = f"{request.noun.capitalize()} description"
        try:
            description = self.request_text(request, "description")
        except Stop as error:
            self.stop(heading, error)
            return
        if self.env.get("CI_MERGE_REQUEST_DESCRIPTION_IS_TRUNCATED") == "true":
            print(
                f"Note: GitLab passed only the first {GITLAB_DESCRIPTION_LIMIT} "
                "characters of the description, so only that part is checked.",
                flush=True,
            )
        self.check(heading, ["--ai-attribution-only"], text=description + "\n")

    def check_commits(self, request: Request, flags: list[str]) -> None:
        """Run the per-commit checks on every commit the request adds."""
        try:
            commits = request_commits(request)
        except Stop as error:
            self.stop("Commits", error)
            return
        if not commits:
            print(f"The {request.noun} adds no commits.", flush=True)
        for sha in commits:
            self.check(f"Commit {sha[:8]} {subject_of(sha)}", [*flags, "--rev", sha])

    def run_without_request(self) -> None:
        """Outside a merge or pull request there is one commit to check: HEAD."""
        print(
            "Not a merge or pull request pipeline: checking the last commit only.",
            flush=True,
        )
        if self.settings["branch"]:
            self.check("Branch", ["--branch"])
        flags = [f"--{name}" for name in COMMIT_CHECKS if self.settings[name]]
        if flags:
            self.check(
                f"Commit {resolve_commit('HEAD')[:8]} {subject_of('HEAD')}",
                # --rev: without it the author checks read the identity the
                # runner would commit with, not the author of this commit.
                [*flags, "--rev", "HEAD"],
            )


def main(argv: Sequence[str] | None = None) -> int:
    """The ``commit-check-ci`` command. Exits 0, 1 (a check failed) or 2."""
    try:
        settings = read_settings(argv)
    except Stop as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    return Job(settings, os.environ).run()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
