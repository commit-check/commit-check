"""Tests for ``commit-check-ci``, which checks a whole merge or pull request.

The tests build real repositories shaped like a GitLab Runner's and a Bitbucket
Pipelines step's checkout, set the variables those systems set, and let the
command run ``commit-check`` on them.
"""

from __future__ import annotations

import http.server
import json
import os
import subprocess
import sys
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import ClassVar

import pytest

from commit_check import ci

# Variables a CI system or the developer's shell may already have set, which
# the command or commit-check would read.
_PREFIXES = ("GITHUB_", "CI_", "BITBUCKET_", "SYSTEM_", "BUILD_", "CCHK_")
_NAMES = (
    "CHANGE_BRANCH",
    "BRANCH_NAME",
    "JENKINS_URL",
    "TAG_NAME",
    "FORCE_COLOR",
    "http_proxy",
    "HTTP_PROXY",
    "all_proxy",
    "ALL_PROXY",
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in list(os.environ):
        if name.startswith(_PREFIXES) or name in _NAMES:
            monkeypatch.delenv(name)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost")


def git(*args: str, cwd: Path) -> str:
    result = subprocess.run(
        ["git", "-c", "user.name=Dev One", "-c", "user.email=dev@example.com", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def commit(repo: Path, message: str) -> str:
    git("commit", "--quiet", "--allow-empty", "-m", message, cwd=repo)
    return git("rev-parse", "HEAD", cwd=repo)


class Upstream:
    """The repository on the server: ``main`` and a branch with two commits."""

    def __init__(self, root: Path, messages: tuple[str, str]) -> None:
        self.path = root / "project.git"
        self.path.mkdir()
        git("init", "--quiet", "--initial-branch=main", ".", cwd=self.path)
        self.base = commit(self.path, "feat: start the project")
        git("checkout", "--quiet", "-b", "feature/login", cwd=self.path)
        self.commits = [commit(self.path, message) for message in messages]
        self.head = self.commits[-1]
        git("checkout", "--quiet", "main", cwd=self.path)
        self.target = self.base

    def advance_target(self) -> None:
        """Move ``main`` on, so the branch is no longer rebased onto it."""
        self.target = commit(self.path, "fix: land something else first")


GOOD = ("feat: add the login form", "fix: trim the user name")
BAD = ("added the login form", "fix: trim the user name")


def gitlab_checkout(
    upstream: Upstream, root: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    """A merge request pipeline's checkout: only the pipeline's commit is fetched."""
    work = root / "build"
    work.mkdir()
    git("init", "--quiet", ".", cwd=work)
    git("remote", "add", "origin", str(upstream.path), cwd=work)
    git("fetch", "--quiet", "origin", f"+{upstream.head}:refs/pipelines/1", cwd=work)
    git("checkout", "--quiet", "--detach", upstream.head, cwd=work)
    for name, value in {
        "CI_MERGE_REQUEST_IID": "7",
        "CI_MERGE_REQUEST_TARGET_BRANCH_NAME": "main",
        "CI_MERGE_REQUEST_SOURCE_BRANCH_NAME": "feature/login",
        "CI_MERGE_REQUEST_DIFF_BASE_SHA": upstream.base,
        "CI_COMMIT_SHA": upstream.head,
        "CI_PROJECT_ID": "1",
        "CI_MERGE_REQUEST_PROJECT_ID": "1",
    }.items():
        monkeypatch.setenv(name, value)
    monkeypatch.chdir(work)
    return work


def bitbucket_checkout(
    upstream: Upstream, root: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    """A pull request step's checkout: the branch, with the destination merged in."""
    work = root / "build"
    git(
        "clone",
        "--quiet",
        "--branch",
        "feature/login",
        str(upstream.path),
        str(work),
        cwd=root,
    )
    git("merge", "--quiet", "--no-edit", upstream.target, cwd=work)
    for name, value in {
        "BITBUCKET_PR_ID": "12",
        "BITBUCKET_BRANCH": "feature/login",
        "BITBUCKET_PR_DESTINATION_BRANCH": "main",
        "BITBUCKET_PR_DESTINATION_COMMIT": upstream.target[:12],
        "BITBUCKET_COMMIT": upstream.head,
        "BITBUCKET_REPO_FULL_NAME": "team/project",
    }.items():
        monkeypatch.setenv(name, value)
    monkeypatch.chdir(work)
    return work


def require_rebase(work: Path) -> None:
    (work / "cchk.toml").write_text('[branch]\nrequire_rebase_target = "main"\n')


class TestReadSettings:
    def test_defaults_are_the_actions_defaults(self) -> None:
        assert ci.read_settings([]) == {
            "message": True,
            "branch": True,
            "author-name": False,
            "author-email": False,
            "files": False,
            "pr-title": False,
            "pr-body-ai-attribution": False,
        }

    def test_an_option_alone_switches_its_check_on(self) -> None:
        settings = ci.read_settings(["--author-email", "--pr-title"])
        assert settings["author-email"] is True
        assert settings["pr-title"] is True

    def test_an_option_takes_true_or_false(self) -> None:
        settings = ci.read_settings(["--message=false", "--files= True "])
        assert settings["message"] is False
        assert settings["files"] is True

    def test_a_variable_named_like_a_check_changes_nothing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # A project variable called BRANCH or MESSAGE is common in CI.
        monkeypatch.setenv("BRANCH", "release")
        monkeypatch.setenv("MESSAGE", "false")

        settings = ci.read_settings([])

        assert settings["branch"] is True
        assert settings["message"] is True

    def test_anything_but_true_or_false_is_refused(self) -> None:
        with pytest.raises(ci.Stop, match="--files must be true or false"):
            ci.read_settings(["--files=yes"])

    def test_an_option_is_not_guessed_from_its_first_letters(self) -> None:
        with pytest.raises(SystemExit):
            ci.read_settings(["--pr=true"])

    def test_version_names_the_command(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises(SystemExit) as stopped:
            ci.read_settings(["--version"])

        assert stopped.value.code == 0
        assert capsys.readouterr().out.startswith("commit-check-ci ")

    def test_main_reports_a_bad_value_and_exits_2(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert ci.main(["--message=maybe"]) == 2
        assert "--message must be true or false" in capsys.readouterr().err


class TestFindRequest:
    def test_none_outside_a_merge_or_pull_request(self) -> None:
        assert ci.find_request({"CI_COMMIT_SHA": "abc"}) is None

    def test_a_gitlab_merge_request_ends_at_the_checked_out_commit(self) -> None:
        request = ci.find_request(
            {
                "CI_MERGE_REQUEST_IID": "7",
                "CI_MERGE_REQUEST_TARGET_BRANCH_NAME": "main",
                "CI_MERGE_REQUEST_DIFF_BASE_SHA": "base",
                "CI_COMMIT_SHA": "tip",
            }
        )
        assert request == ci.Request("GitLab", "merge request", "main", "base", "tip")

    def test_a_merged_results_pipeline_ends_at_the_source_branch_commit(self) -> None:
        request = ci.find_request(
            {
                "CI_MERGE_REQUEST_IID": "7",
                "CI_MERGE_REQUEST_SOURCE_BRANCH_SHA": "tip",
                "CI_COMMIT_SHA": "merge",
            }
        )
        assert request is not None
        assert request.head == "tip"

    def test_a_bitbucket_pull_request_ends_at_its_own_commit(self) -> None:
        request = ci.find_request(
            {
                "BITBUCKET_PR_ID": "12",
                "BITBUCKET_PR_DESTINATION_BRANCH": "main",
                "BITBUCKET_PR_DESTINATION_COMMIT": "base",
                "BITBUCKET_COMMIT": "tip",
            }
        )
        assert request == ci.Request("Bitbucket", "pull request", "main", "base", "tip")


class TestGitLab:
    def test_every_commit_of_the_merge_request_is_checked(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capfd: pytest.CaptureFixture[str],
    ) -> None:
        upstream = Upstream(tmp_path, BAD)
        gitlab_checkout(upstream, tmp_path, monkeypatch)

        assert ci.main(["--message=true", "--branch=true"]) == 1

        out = capfd.readouterr().out
        assert f"Commit {upstream.commits[0][:8]} added the login form" in out
        assert "CC001" in out
        assert (
            f"Commit {upstream.commits[1][:8]} fix: trim the user name\n  passed" in out
        )
        # Oldest first, the order they were written in.
        assert out.index(upstream.commits[0][:8]) < out.index(upstream.commits[1][:8])
        assert "1 of 3 failed." in out

    def test_a_good_merge_request_passes(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capfd: pytest.CaptureFixture[str],
    ) -> None:
        gitlab_checkout(Upstream(tmp_path, GOOD), tmp_path, monkeypatch)

        assert (
            ci.main(["--author-name=true", "--author-email=true", "--files=true"]) == 0
        )
        assert "All 3 passed." in capfd.readouterr().out

    def test_the_target_branch_is_fetched_for_the_rebase_check(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capfd: pytest.CaptureFixture[str],
    ) -> None:
        upstream = Upstream(tmp_path, GOOD)
        upstream.advance_target()
        work = gitlab_checkout(upstream, tmp_path, monkeypatch)
        require_rebase(work)

        # Without the fetch the rule finds no origin/main, reports itself as
        # skipped, and the job passes.
        assert ci.main(["--message=false"]) == 1

        assert "CC202" in capfd.readouterr().out
        assert git("rev-parse", "origin/main", cwd=work) == upstream.target

    def test_a_pipeline_in_a_fork_fetches_from_the_target_project(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        upstream = Upstream(tmp_path, GOOD)
        work = gitlab_checkout(upstream, tmp_path, monkeypatch)
        git("remote", "set-url", "origin", str(tmp_path / "the-fork.git"), cwd=work)
        monkeypatch.setenv("CI_PROJECT_ID", "2")
        monkeypatch.setenv("CI_MERGE_REQUEST_PROJECT_URL", str(tmp_path / "project"))

        assert ci.main(["--message=false"]) == 0
        assert git("rev-parse", "origin/main", cwd=work) == upstream.target

    def test_a_failed_fetch_fails_the_branch_check(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capfd: pytest.CaptureFixture[str],
    ) -> None:
        gitlab_checkout(Upstream(tmp_path, GOOD), tmp_path, monkeypatch)
        monkeypatch.setenv("CI_MERGE_REQUEST_TARGET_BRANCH_NAME", "no-such-branch")

        assert ci.main(["--message=false"]) == 1

        out = capfd.readouterr().out
        assert (
            "Error: could not fetch the target branch 'no-such-branch' from origin"
            in out
        )
        assert "1 of 1 failed." in out

    def test_a_merge_request_without_a_target_branch_fails_the_branch_check(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capfd: pytest.CaptureFixture[str],
    ) -> None:
        gitlab_checkout(Upstream(tmp_path, GOOD), tmp_path, monkeypatch)
        monkeypatch.delenv("CI_MERGE_REQUEST_TARGET_BRANCH_NAME")

        assert ci.main(["--message=false"]) == 1
        assert "the merge request's target branch is not set" in capfd.readouterr().out

    def test_the_title_and_description_are_checked(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capfd: pytest.CaptureFixture[str],
    ) -> None:
        work = gitlab_checkout(Upstream(tmp_path, GOOD), tmp_path, monkeypatch)
        (work / "cchk.toml").write_text('[commit]\nai_attribution = "forbid"\n')
        monkeypatch.setenv("CI_MERGE_REQUEST_TITLE", "Login form")
        monkeypatch.setenv(
            "CI_MERGE_REQUEST_DESCRIPTION",
            "Adds the form.\n\nCo-authored-by: Claude <noreply@anthropic.com>",
        )
        monkeypatch.setenv("CI_MERGE_REQUEST_DESCRIPTION_IS_TRUNCATED", "true")

        code = ci.main(
            [
                "--message=false",
                "--branch=false",
                "--pr-title=true",
                "--pr-body-ai-attribution=true",
            ]
        )

        out = capfd.readouterr().out
        assert code == 1
        assert "Merge request title\n" in out
        assert "CC001" in out
        assert "only the first 2700 characters" in out
        assert "Merge request description\n" in out
        assert "CC013" in out
        assert "2 of 2 failed." in out

    @pytest.mark.parametrize(
        "title",
        [
            "Draft: feat: add the login form",
            "[Draft] feat: add the login form",
            "(draft)  feat: add the login form",
            "draft: [DRAFT] feat: add the login form",
        ],
    )
    def test_a_draft_marker_is_not_part_of_the_title(
        self,
        title: str,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capfd: pytest.CaptureFixture[str],
    ) -> None:
        gitlab_checkout(Upstream(tmp_path, GOOD), tmp_path, monkeypatch)
        monkeypatch.setenv("CI_MERGE_REQUEST_TITLE", title)

        assert ci.main(["--message=false", "--branch=false", "--pr-title=true"]) == 0
        assert "Merge request title\n  passed" in capfd.readouterr().out

    def test_a_title_that_only_starts_with_the_word_draft_is_checked_whole(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        gitlab_checkout(Upstream(tmp_path, GOOD), tmp_path, monkeypatch)
        monkeypatch.setenv("CI_MERGE_REQUEST_TITLE", "Draft the login form")

        assert ci.main(["--message=false", "--branch=false", "--pr-title=true"]) == 1

    def test_modules_in_the_checkout_do_not_replace_the_installed_ones(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capfd: pytest.CaptureFixture[str],
    ) -> None:
        # The checkout is the request's own content. A commit_check package or
        # a module named like one from the standard library in it must not be
        # what runs the checks.
        upstream = Upstream(tmp_path, BAD)
        work = gitlab_checkout(upstream, tmp_path, monkeypatch)
        fake = work / "commit_check"
        fake.mkdir()
        (fake / "__init__.py").write_text("")
        (fake / "main.py").write_text('print("replaced")\n')
        (work / "argparse.py").write_text('raise SystemExit("replaced")\n')

        assert ci.main(["--branch=false"]) == 1

        out = capfd.readouterr().out
        assert "CC001" in out
        assert "replaced" not in out

    def test_a_clone_that_ends_inside_the_merge_request_fails(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capfd: pytest.CaptureFixture[str],
    ) -> None:
        # The first commit has the bad message, and a clone of depth 1 does
        # not hold it. Fetching the target branch brings the base commit in,
        # so git lists the range without an error: one commit instead of two.
        upstream = Upstream(tmp_path, BAD)
        work = tmp_path / "build"
        git(
            "clone",
            "--quiet",
            "--depth=1",
            "--branch=feature/login",
            upstream.path.as_uri(),
            str(work),
            cwd=tmp_path,
        )
        monkeypatch.chdir(work)
        for name, value in {
            "CI_MERGE_REQUEST_IID": "7",
            "CI_MERGE_REQUEST_TARGET_BRANCH_NAME": "main",
            "CI_MERGE_REQUEST_SOURCE_BRANCH_NAME": "feature/login",
            "CI_MERGE_REQUEST_DIFF_BASE_SHA": upstream.base,
            "CI_COMMIT_SHA": upstream.head,
        }.items():
            monkeypatch.setenv(name, value)

        assert ci.main([]) == 1

        out = capfd.readouterr().out
        assert "the clone ends inside the merge request" in out
        assert 'set GIT_DEPTH to "0"' in out
        assert "All" not in out

    def test_a_range_that_cannot_be_read_fails_and_names_the_shallow_clone(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capfd: pytest.CaptureFixture[str],
    ) -> None:
        upstream = Upstream(tmp_path, GOOD)
        work = tmp_path / "build"
        git(
            "clone",
            "--quiet",
            "--depth=1",
            "--branch=feature/login",
            upstream.path.as_uri(),
            str(work),
            cwd=tmp_path,
        )
        monkeypatch.chdir(work)
        monkeypatch.setenv("CI_MERGE_REQUEST_IID", "7")
        monkeypatch.setenv("CI_MERGE_REQUEST_DIFF_BASE_SHA", upstream.base)
        monkeypatch.setenv("CI_COMMIT_SHA", upstream.head)

        assert ci.main(["--branch=false"]) == 1

        out = capfd.readouterr().out
        assert "could not list the merge request's commits" in out
        assert 'set GIT_DEPTH to "0"' in out

    def test_a_configuration_error_exits_2(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        work = gitlab_checkout(Upstream(tmp_path, GOOD), tmp_path, monkeypatch)
        (work / "cchk.toml").write_text('[commit]\nsubject_max_length = "long"\n')

        assert ci.main(["--branch=false"]) == 2

    def test_a_merge_request_without_commits_says_so(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capfd: pytest.CaptureFixture[str],
    ) -> None:
        upstream = Upstream(tmp_path, GOOD)
        gitlab_checkout(upstream, tmp_path, monkeypatch)
        monkeypatch.setenv("CI_MERGE_REQUEST_DIFF_BASE_SHA", upstream.head)

        assert ci.main(["--branch=false"]) == 0
        assert "The merge request adds no commits." in capfd.readouterr().out


class TestBitbucket:
    def test_only_the_pull_requests_own_commits_are_checked(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capfd: pytest.CaptureFixture[str],
    ) -> None:
        upstream = Upstream(tmp_path, BAD)
        upstream.advance_target()
        work = bitbucket_checkout(upstream, tmp_path, monkeypatch)
        # The step's merge of the destination is checked out, not the branch tip.
        assert git("rev-parse", "HEAD", cwd=work) != upstream.head

        assert ci.main([]) == 1

        out = capfd.readouterr().out
        assert out.count("\nCommit ") == 2
        assert "land something else first" not in out
        assert "Merge " not in out
        assert "1 of 3 failed." in out

    def test_the_destination_ref_is_made_from_the_commit_the_step_merged(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capfd: pytest.CaptureFixture[str],
    ) -> None:
        upstream = Upstream(tmp_path, GOOD)
        upstream.advance_target()
        work = bitbucket_checkout(upstream, tmp_path, monkeypatch)
        git("update-ref", "-d", "refs/remotes/origin/main", cwd=work)
        # The remote is out of reach: nothing may be fetched.
        git("remote", "set-url", "origin", str(tmp_path / "unreachable.git"), cwd=work)
        require_rebase(work)

        assert ci.main([]) == 1

        assert "CC202" in capfd.readouterr().out
        assert git("rev-parse", "origin/main", cwd=work) == upstream.target

    def test_a_destination_ref_the_clone_already_has_is_left_alone(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        upstream = Upstream(tmp_path, GOOD)
        work = bitbucket_checkout(upstream, tmp_path, monkeypatch)
        git("update-ref", "refs/remotes/origin/main", upstream.commits[0], cwd=work)

        assert ci.main(["--message=false"]) == 0
        assert git("rev-parse", "origin/main", cwd=work) == upstream.commits[0]

    def test_a_destination_ref_behind_the_destination_commit_is_moved_to_it(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capfd: pytest.CaptureFixture[str],
    ) -> None:
        upstream = Upstream(tmp_path, GOOD)
        behind = upstream.target
        upstream.advance_target()
        work = bitbucket_checkout(upstream, tmp_path, monkeypatch)
        git("update-ref", "refs/remotes/origin/main", behind, cwd=work)
        require_rebase(work)

        assert ci.main(["--message=false"]) == 1

        assert "CC202" in capfd.readouterr().out
        assert git("rev-parse", "origin/main", cwd=work) == upstream.target

    def test_a_destination_ref_that_cannot_be_written_fails_the_branch_check(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capfd: pytest.CaptureFixture[str],
    ) -> None:
        work = bitbucket_checkout(Upstream(tmp_path, GOOD), tmp_path, monkeypatch)
        git("update-ref", "-d", "refs/remotes/origin/main", cwd=work)
        # A branch of that name already exists, so git cannot write main below it.
        monkeypatch.setenv("BITBUCKET_PR_DESTINATION_BRANCH", "feature/login/next")
        git("update-ref", "refs/remotes/origin/feature/login", "HEAD", cwd=work)

        assert ci.main(["--message=false"]) == 1
        assert "Error: could not write refs/remotes/origin/feature/login/next" in (
            capfd.readouterr().out
        )

    def test_a_missing_destination_commit_fails_the_branch_check(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capfd: pytest.CaptureFixture[str],
    ) -> None:
        work = bitbucket_checkout(Upstream(tmp_path, GOOD), tmp_path, monkeypatch)
        git("update-ref", "-d", "refs/remotes/origin/main", cwd=work)
        monkeypatch.setenv("BITBUCKET_PR_DESTINATION_COMMIT", "0123456789ab")

        assert ci.main(["--message=false"]) == 1
        assert "the destination commit '0123456789ab' is not in the clone" in (
            capfd.readouterr().out
        )

    def test_a_pull_request_without_a_destination_commit_fails_the_branch_check(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capfd: pytest.CaptureFixture[str],
    ) -> None:
        work = bitbucket_checkout(Upstream(tmp_path, GOOD), tmp_path, monkeypatch)
        git("update-ref", "-d", "refs/remotes/origin/main", cwd=work)
        monkeypatch.delenv("BITBUCKET_PR_DESTINATION_COMMIT")

        assert ci.main(["--message=false"]) == 1
        assert "the destination commit '' is not in the clone" in capfd.readouterr().out

    def test_a_shallow_clone_is_named_with_the_setting_that_fixes_it(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capfd: pytest.CaptureFixture[str],
    ) -> None:
        upstream = Upstream(tmp_path, GOOD)
        work = tmp_path / "build"
        git(
            "clone",
            "--quiet",
            "--depth=1",
            "--branch=feature/login",
            upstream.path.as_uri(),
            str(work),
            cwd=tmp_path,
        )
        monkeypatch.chdir(work)
        monkeypatch.setenv("BITBUCKET_PR_ID", "12")
        monkeypatch.setenv("BITBUCKET_PR_DESTINATION_COMMIT", upstream.base[:12])
        monkeypatch.setenv("BITBUCKET_COMMIT", upstream.head)

        assert ci.main(["--branch=false"]) == 1

        out = capfd.readouterr().out
        assert "could not list the pull request's commits" in out
        assert "set `clone: depth: full` on this step" in out

    def test_the_description_needs_an_access_token_too(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capfd: pytest.CaptureFixture[str],
    ) -> None:
        bitbucket_checkout(Upstream(tmp_path, GOOD), tmp_path, monkeypatch)

        code = ci.main(
            ["--message=false", "--branch=false", "--pr-body-ai-attribution=true"]
        )

        assert code == 1
        assert "Pull request description\n  Error: Bitbucket does not pass" in (
            capfd.readouterr().out
        )

    def test_the_title_needs_an_access_token(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capfd: pytest.CaptureFixture[str],
    ) -> None:
        bitbucket_checkout(Upstream(tmp_path, GOOD), tmp_path, monkeypatch)

        assert ci.main(["--message=false", "--branch=false", "--pr-title=true"]) == 1

        out = capfd.readouterr().out
        assert "Pull request title\n  Error: Bitbucket does not pass" in out
        assert "BITBUCKET_ACCESS_TOKEN" in out


class Api(http.server.BaseHTTPRequestHandler):
    """Stands in for the Bitbucket API."""

    reply: ClassVar[tuple[int, dict[str, str], bytes]] = (200, {}, b"{}")
    seen: ClassVar[list[tuple[str, str | None]]] = []

    def do_GET(self) -> None:
        Api.seen.append((self.path, self.headers.get("Authorization")))
        status, headers, body = Api.reply
        self.send_response(status)
        for name, value in headers.items():
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:
        pass


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch) -> Iterator[type[Api]]:
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Api)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    Api.seen = []
    Api.reply = (200, {}, b"{}")
    monkeypatch.setattr(ci, "BITBUCKET_API", f"http://127.0.0.1:{server.server_port}")
    yield Api
    server.shutdown()
    server.server_close()
    thread.join()


PULL_REQUEST_ENV = {
    "BITBUCKET_PR_ID": "12",
    "BITBUCKET_REPO_FULL_NAME": "team/project",
    "BITBUCKET_ACCESS_TOKEN": "s3cret",
}


class TestBitbucketApi:
    def test_reads_the_pull_request_with_the_token(self, api: type[Api]) -> None:
        api.reply = (200, {}, json.dumps({"title": "feat: add login"}).encode())

        pull_request = ci.bitbucket_pull_request(PULL_REQUEST_ENV)

        assert pull_request == {"title": "feat: add login"}
        assert api.seen == [
            ("/repositories/team/project/pullrequests/12", "Bearer s3cret")
        ]

    def test_the_repository_can_come_from_the_workspace_and_slug(
        self, api: type[Api]
    ) -> None:
        env = {
            "BITBUCKET_PR_ID": "12",
            "BITBUCKET_WORKSPACE": "team",
            "BITBUCKET_REPO_SLUG": "project",
            "BITBUCKET_ACCESS_TOKEN": "s3cret",
        }

        ci.bitbucket_pull_request(env)

        assert api.seen[0][0] == "/repositories/team/project/pullrequests/12"

    def test_a_refused_token_is_reported_without_the_token(
        self, api: type[Api]
    ) -> None:
        api.reply = (401, {}, b"{}")

        with pytest.raises(ci.Stop, match="HTTP Error 401") as error:
            ci.bitbucket_pull_request(PULL_REQUEST_ENV)
        assert "s3cret" not in str(error.value)

    def test_a_redirect_is_refused_so_the_token_goes_nowhere_else(
        self, api: type[Api]
    ) -> None:
        api.reply = (302, {"Location": "http://127.0.0.1:9/elsewhere"}, b"")

        with pytest.raises(
            ci.Stop, match="redirect to http://127.0.0.1:9/elsewhere refused"
        ):
            ci.bitbucket_pull_request(PULL_REQUEST_ENV)
        assert len(api.seen) == 1

    @pytest.mark.parametrize("body", [b"not json", b"[]"])
    def test_a_reply_that_is_not_a_pull_request_is_an_error(
        self, api: type[Api], body: bytes
    ) -> None:
        api.reply = (200, {}, body)

        with pytest.raises(ci.Stop, match="Bitbucket API"):
            ci.bitbucket_pull_request(PULL_REQUEST_ENV)

    @pytest.mark.parametrize(
        "env",
        [
            {**PULL_REQUEST_ENV, "BITBUCKET_PR_ID": "12/../../x"},
            {**PULL_REQUEST_ENV, "BITBUCKET_REPO_FULL_NAME": "team/project/extra"},
            {"BITBUCKET_PR_ID": "12", "BITBUCKET_ACCESS_TOKEN": "s3cret"},
        ],
    )
    def test_an_id_or_repository_that_is_not_one_is_not_put_in_the_url(
        self, api: type[Api], env: dict[str, str]
    ) -> None:
        with pytest.raises(ci.Stop, match="repository or id is not set"):
            ci.bitbucket_pull_request(env)
        assert api.seen == []

    def test_the_title_and_description_come_from_one_api_read(
        self,
        api: type[Api],
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capfd: pytest.CaptureFixture[str],
    ) -> None:
        api.reply = (
            200,
            {},
            json.dumps(
                {"title": "feat: add the login form", "description": None}
            ).encode(),
        )
        bitbucket_checkout(Upstream(tmp_path, GOOD), tmp_path, monkeypatch)
        monkeypatch.setenv("BITBUCKET_ACCESS_TOKEN", "s3cret")

        code = ci.main(
            [
                "--message=false",
                "--branch=false",
                "--pr-title=true",
                "--pr-body-ai-attribution=true",
            ]
        )

        out = capfd.readouterr().out
        assert code == 0
        assert "Pull request title\n  passed" in out
        assert "Pull request description\n  passed" in out
        assert len(api.seen) == 1


class TestOutsideARequest:
    def test_the_last_commit_and_the_branch_are_checked(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capfd: pytest.CaptureFixture[str],
    ) -> None:
        upstream = Upstream(tmp_path, GOOD)
        git("checkout", "--quiet", "feature/login", cwd=upstream.path)
        monkeypatch.chdir(upstream.path)

        assert ci.main([]) == 0

        out = capfd.readouterr().out
        assert "Not a merge or pull request pipeline" in out
        assert f"Commit {upstream.head[:8]} fix: trim the user name\n  passed" in out
        assert "All 2 passed." in out

    def test_nothing_runs_when_every_check_is_off(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capfd: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.chdir(Upstream(tmp_path, GOOD).path)

        assert ci.main(["--message=false", "--branch=false"]) == 0
        assert "nothing was checked" in capfd.readouterr().out


def test_a_commit_check_killed_by_a_signal_fails_the_job(
    monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str]
) -> None:
    killed: subprocess.CompletedProcess[bytes] = subprocess.CompletedProcess(
        args=[], returncode=-9
    )
    monkeypatch.setattr(ci.subprocess, "run", lambda *args, **kwargs: killed)
    job = ci.Job(ci.read_settings([]), {})

    job.check("Branch", ["--branch"])

    assert job.exit_code == 1
    assert job.failed == 1
    assert "passed" not in capfd.readouterr().out


def test_the_module_runs_as_a_command() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "commit_check.ci", "--message=maybe"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "--message must be true or false" in result.stderr


def test_a_subject_is_printed_without_its_control_characters(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    upstream = Upstream(tmp_path, ("feat: add \x1b[31mred\x1b[0m text", "fix: x"))
    monkeypatch.chdir(upstream.path)

    assert ci.subject_of(upstream.commits[0]) == "feat: add ?[31mred?[0m text"
