# Commit Check

[![CI](https://github.com/commit-check/commit-check/actions/workflows/main.yml/badge.svg)](https://github.com/commit-check/commit-check/actions/workflows/main.yml)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=commit-check_commit-check&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=commit-check_commit-check)
[![PyPI](https://img.shields.io/pypi/v/commit-check?logo=python&logoColor=white&color=%232c9ccd)](https://pypi.org/project/commit-check/)
[![PyPI Downloads](https://img.shields.io/pypi/dm/commit-check?color=%232c9ccd)](https://pypi.org/project/commit-check/)
[![Python Versions](https://img.shields.io/pypi/pyversions/commit-check?logo=python&logoColor=white)](https://pypi.org/project/commit-check/)
[![commit-check](https://img.shields.io/badge/commit--check-enabled-brightgreen?logo=Git&logoColor=white&color=%232c9ccd)](https://github.com/commit-check/commit-check)
[![CodeCov](https://codecov.io/gh/commit-check/commit-check/branch/main/graph/badge.svg?token=GC2U5V5ZRT)](https://codecov.io/gh/commit-check/commit-check)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/commit-check/commit-check/badge)](https://api.securityscorecards.dev/projects/github.com/commit-check/commit-check)

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
  - [Use Default Configuration](#use-default-configuration)
  - [Use Custom Configuration File](#use-custom-configuration-file)
  - [Organization-Level Configuration (inherit_from)](#organization-level-configuration-inherit_from)
  - [Use CLI Arguments or Environment Variables](#use-cli-arguments-or-environment-variables)
  - [Check Push Safety](#check-push-safety)
- [AI-Native Usage](#ai-native-usage)
  - [Machine-Readable JSON Output (--format json)](#machine-readable-json-output---format-json)
  - [Quieter Human-Readable Output](#quieter-human-readable-output)
  - [Python API (no subprocess required)](#python-api-no-subprocess-required)
- [Examples](#examples)
- [Badging your repository](#badging-your-repository)
- [Why Commit Check?](#why-commit-check)
- [Versioning](#versioning)
- [Have question or feedback?](#have-question-or-feedback)
- [License](#license)

## Overview

**Commit Check** is a lightweight policy engine for Git commit metadata.

It validates commit messages, branch names, author identity, signoff trailers,
AI attribution policy, and push safety — using one versioned TOML policy across
local hooks, CI, GitHub Actions, and AI automation.

- **One policy file:** `cchk.toml`
- **Multiple enforcement points:** CLI, pre-commit, CI / GitHub Actions
- **Machine-readable output:** JSON + Python API for automation and AI agents

![commit-check demo](https://github.com/commit-check/commit-check/raw/main/docs/demo.gif)

<br>

## Quick Start

**1. Install and run with zero configuration:**

```bash
pip install commit-check
commit-check --message --branch
```

**2. Add to your pre-commit hooks** (`.pre-commit-config.yaml`):

```yaml
repos:
  - repo: https://github.com/commit-check/commit-check
    rev: v2.11.1
    hooks:
      - id: check-message
      - id: check-branch
```

**3. Add a badge to your repository:**

```text
[![commit-check](https://img.shields.io/badge/commit--check-enabled-brightgreen?logo=Git&logoColor=white&color=%232c9ccd)](https://github.com/commit-check/commit-check)
```

## Installation

To install Commit Check, you can use pip:

```bash
pip install commit-check
```

Or install directly from the GitHub repository:

```bash
pip install git+https://github.com/commit-check/commit-check.git@main
```

Then, run `commit-check --help` or `cchk --help` (alias for `commit-check`) from the command line.
For more information, see the [docs](https://commit-check.github.io/commit-check/cli_args.html).

## Configuration

Commit Check can be configured in three ways (in order of priority):

1. **Command-line arguments** — Override settings for specific runs
2. **Environment variables** — Configure via `CCHK_*` environment variables
3. **Configuration files** — Use `cchk.toml` or `commit-check.toml`

### Use Default Configuration

- **Commit Check** uses a [default configuration](https://github.com/commit-check/commit-check/blob/main/docs/configuration.rst) if you do not provide a `cchk.toml` or `commit-check.toml` file.

- The default configuration is lenient — it only checks whether commit messages follow the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/#summary) specification and branch names follow the [Conventional Branch](https://conventionalbranch.org#summary) convention.

### Use Custom Configuration File

To customize the behavior, create a configuration file named `cchk.toml` or `commit-check.toml` in your repository's root directory or in the `.github` folder, e.g., [`cchk.toml`](https://github.com/commit-check/commit-check/blob/main/cchk.toml) or `.github/cchk.toml`.

```toml
[commit]
# https://www.conventionalcommits.org
conventional_commits = true
subject_imperative = true
subject_max_length = 80
allow_commit_types = ["feat", "fix", "docs", "style", "refactor", "test", "chore", "ci"]
allow_merge_commits = true
allow_wip_commits = false
require_signed_off_by = false
# Bypass checks for bot/automation authors and co-authors:
ignore_authors = ["dependabot[bot]", "renovate[bot]", "copilot[bot]"]
# AI attribution policy: "ignore" (default) or "forbid"
# "forbid" rejects commits with known AI tool signatures
ai_attribution = "forbid"

[branch]
# https://conventionalbranch.org
conventional_branch = true
allow_branch_types = ["feature", "bugfix", "hotfix", "release", "chore", "feat", "fix"]
```

> **Tip: IDE Autocompletion**
>
> commit-check's TOML schema is published on [SchemaStore](https://www.schemastore.org/),
> so editors like VS Code (via [Even Better TOML](https://marketplace.visualstudio.com/items?itemName=tamasfe.even-better-toml)),
> PyCharm, and IntelliJ provide autocompletion, validation, and documentation
> tooltips for `cchk.toml` out of the box — no manual schema path configuration needed.

### Organization-Level Configuration (inherit_from)

Share a base configuration across all repositories in your organization using `inherit_from`:

```toml
# .github/cchk.toml — inherits from org-level config, then overrides locally
inherit_from = "github:my-org/.github:cchk.toml"

[commit]
subject_max_length = 72  # Local override
```

The `inherit_from` field accepts:

- A **GitHub shorthand** (recommended): `inherit_from = "github:owner/repo:path/to/cchk.toml"`
- A **GitHub shorthand with ref**: `inherit_from = "github:owner/repo@main:path/to/cchk.toml"`
- A **local file path** (relative or absolute): `inherit_from = "../shared/cchk.toml"`
- An **HTTPS URL**: `inherit_from = "https://example.com/cchk.toml"`

The `github:` shorthand fetches from `raw.githubusercontent.com`. HTTP (non-TLS) URLs are rejected for security.

Local settings always **override** the inherited base configuration.

### Use CLI Arguments or Environment Variables

For one-off checks or CI/CD pipelines, you can configure via CLI arguments or environment variables:

```bash
# Using CLI arguments
commit-check --message --subject-imperative=true --subject-max-length=72

# Using environment variables
export CCHK_SUBJECT_IMPERATIVE=true
export CCHK_SUBJECT_MAX_LENGTH=72
commit-check --message

# In pre-commit hooks (.pre-commit-config.yaml)
repos:
  - repo: https://github.com/commit-check/commit-check
    rev: v2.11.1
    hooks:
      - id: check-message
        args:
          - --subject-imperative=false
          - --subject-max-length=100
```

See the [Configuration documentation](https://commit-check.github.io/commit-check/configuration.html) for all available options.

### Check Push Safety

Use `--no-force-push` in a `pre-push` hook to inspect the ref updates Git
provides on stdin, or run it directly to compare `HEAD` with the current
branch's configured upstream:

```bash
# Standalone preflight check against the current branch's upstream
commit-check --no-force-push
```

```yaml
# In pre-commit hooks (.pre-commit-config.yaml)
repos:
  - repo: https://github.com/commit-check/commit-check
    rev: v2.11.1
    hooks:
      - id: check-no-force-push
        stages: [pre-push]
```

Piping `git push` into `commit-check` is not a prevention mechanism. The
push has already been started, and standard `git push` output does not carry
the pre-push ref metadata that `commit-check` uses.

## AI-Native Usage

Commit Check is designed to be consumed by AI agents, LLM toolchains, and
automation scripts — not just by humans reading terminal output.

### Machine-Readable JSON Output (`--format json`)

Pass `--format json` to any CLI invocation to receive structured JSON instead
of human-readable ASCII art.  The exit code is unchanged (`0` = pass, `1` = fail),
so existing CI scripts continue to work:

```bash
echo "feat: add streaming support" | commit-check -m --format json
```

```json
{
  "status": "pass",
  "checks": [
    { "check": "message",           "status": "pass", "value": "", "error": "", "suggest": "" },
    { "check": "subject_imperative", "status": "pass", "value": "", "error": "", "suggest": "" }
  ]
}
```

On failure the failing checks carry the full `error` and `suggest` fields
an agent needs to self-correct:

```bash
echo "wip bad commit" | commit-check -m --format json
```

```json
{
  "status": "fail",
  "checks": [
    {
      "check":   "message",
      "status":  "fail",
      "value":   "wip bad commit",
      "error":   "The commit message should follow Conventional Commits. See https://www.conventionalcommits.org",
      "suggest": "Use <type>(<scope>): <description>, where <type> is one of: feat, fix, docs, ..."
    }
  ]
}
```

### Quieter Human-Readable Output

For terminal workflows that still want plain text, commit-check now supports
two lower-noise output modes:

- `--no-banner` keeps the normal failure details and suggestions, but removes
  the ASCII-art failure banner.
- `--compact` emits a single `[FAIL]` line per failing check and implies
  `--no-banner`.

```bash
echo "wip bad commit" | commit-check -m --no-banner
```

```text
Type message check failed ==> wip bad commit
It doesn't match regex: ^(build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test){1}(\([\w\-\.]+\))?(!)?: ([\w ])+([\s\S]*)|(Merge).*|(fixup!.*)
The commit message should follow Conventional Commits. See https://www.conventionalcommits.org
Suggest: Use <type>(<scope>): <description>, where <type> is one of: feat, fix, docs, ...
```

```bash
echo "wip bad commit" | commit-check -m --compact
```

```text
[FAIL] message: wip bad commit
```

### Python API (no subprocess required)

The `commit_check.api` module exposes a lightweight, import-friendly interface
so AI agents, tools, and scripts can validate commits **without spawning a
subprocess**.  All functions return plain dicts that are easy to serialise,
forward to an LLM, or chain into larger workflows:

```python
from commit_check.api import validate_message, validate_branch, validate_all

# --- validate a single commit message ---
result = validate_message("feat: add streaming support")
print(result["status"])          # "pass"

# --- validate a branch name ---
result = validate_branch("feature/add-streaming")
print(result["status"])          # "pass"

# --- run multiple checks at once ---
result = validate_all(
    message="feat: implement new feature",
    branch="feature/new-feature",
    author_name="Ada Lovelace",
    author_email="ada@example.com",
)
if result["status"] == "fail":
    for check in result["checks"]:
        if check["status"] == "fail":
            print(f"[{check['check']}] {check['error']}")
            print(f"  suggestion: {check['suggest']}")

# --- supply a custom config to restrict allowed types ---
result = validate_message(
    "docs: update readme",
    config={"commit": {"allow_commit_types": ["feat", "fix"]}},
)
print(result["status"])          # "fail" — 'docs' not in allowed types
```

**Return-value schema** (all API functions):

```python
{
    "status": "pass" | "fail",
    "checks": [
        {
            "check":   "<rule name>",
            "status":  "pass" | "fail",
            "value":   "<actual value that was checked>",
            "error":   "<human-readable error description>",
            "suggest": "<how to fix>",
        },
        # ... one entry per active rule
    ]
}
```

Available API functions:

- `validate_message(message, *, config=None)` — validate a commit message string
- `validate_branch(branch=None, *, config=None)` — validate a branch name (defaults to current git branch)
- `validate_author(name=None, email=None, *, config=None)` — validate author name/email
- `validate_all(message, branch, author_name, author_email, *, config=None)` — run all checks at once

For detailed usage instructions including pre-commit hooks, CLI commands, and STDIN examples, see the [Usage Examples documentation](https://commit-check.github.io/commit-check/example.html).

## Examples

### Check Commit Message Failed

```text
Commit rejected by Commit-Check.

  (c).-.(c)    (c).-.(c)    (c).-.(c)    (c).-.(c)    (c).-.(c)
   / ._. \      / ._. \      / ._. \      / ._. \      / ._. \
 __\( C )/__  __\( H )/__  __\( E )/__  __\( C )/__  __\( K )/__
(_.-/'-'\-._)(_.-/'-'\-._)(_.-/'-'\-._)(_.-/'-'\-._)(_.-/'-'\-._)
   || E ||      || R ||      || R ||      || O ||      || R ||
 _.' '-' '._  _.' '-' '._  _.' '-' '._  _.' '-' '._  _.' '-' '._
(.-./`-´\.-.)(.-./`-´\.-.)(.-./`-´\.-.)(.-./`-´\.-.)(.-./`-´\.-.)
 `-´     `-´  `-´     `-´  `-´     `-´  `-´     `-´  `-´     `-´

Commit rejected.

Type message check failed ==> test commit message check
The commit message should follow Conventional Commits. See https://www.conventionalcommits.org
Suggest: Use <type>(<scope>): <description>, where <type> is one of: feat, fix, docs, style, refactor, test, chore, ci
```

### Check Branch Naming Failed

```text
Commit rejected by Commit-Check.

  (c).-.(c)    (c).-.(c)    (c).-.(c)    (c).-.(c)    (c).-.(c)
   / ._. \      / ._. \      / ._. \      / ._. \      / ._. \
 __\( C )/__  __\( H )/__  __\( E )/__  __\( C )/__  __\( K )/__
(_.-/'-'\-._)(_.-/'-'\-._)(_.-/'-'\-._)(_.-/'-'\-._)(_.-/'-'\-._)
   || E ||      || R ||      || R ||      || O ||      || R ||
 _.' '-' '._  _.' '-' '._  _.' '-' '._  _.' '-' '._  _.' '-' '._
(.-./`-´\.-.)(.-./`-´\.-.)(.-./`-´\.-.)(.-./`-´\.-.)(.-./`-´\.-.)
 `-´     `-´  `-´     `-´  `-´     `-´  `-´     `-´  `-´     `-´

Commit rejected.

Type branch check failed ==> test-branch
The branch should follow Conventional Branch. See https://conventionalbranch.org
Suggest: Use <type>/<description> with allowed types or add branch name to allow_branch_names in config, or use ignore_authors in config branch section to bypass
```

More examples see [example documentation](https://commit-check.github.io/commit-check/example.html).

## Badging your repository

You can add a badge to your repository to show that you use commit-check!

[![commit-check](https://img.shields.io/badge/commit--check-enabled-brightgreen?logo=Git&logoColor=white&color=%232c9ccd)](https://github.com/commit-check/commit-check)

**Markdown**

```text
[![commit-check](https://img.shields.io/badge/commit--check-enabled-brightgreen?logo=Git&logoColor=white&color=%232c9ccd)](https://github.com/commit-check/commit-check)
```

**reStructuredText**

```text
.. image:: https://img.shields.io/badge/commit--check-enabled-brightgreen?logo=Git&logoColor=white&color=%232c9ccd
    :target: https://github.com/commit-check/commit-check
    :alt: commit-check
```

## Why Commit Check?

The table below compares common approaches to commit policy enforcement.
`commitlint` is a specialized commit-message linter. [GitHub Rulesets][github-rulesets]
are platform-native server-side enforcement.  Custom Git hooks and the
`pre-commit` framework are integration mechanisms, so the last column
reflects a DIY approach rather than built-in product features.

[github-rulesets]: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets

| Feature | Commit Check | commitlint | YACC <sup id="f2">[\[2\]](#fn2)</sup> | GitHub Rulesets | Custom hooks |
|---------|-------------|------------|------|-----------------|-------------|
| Conventional Commits enforcement | ✅ | ✅ | Partial | Partial <sup id="f4">[\[4\]](#fn4)</sup> | DIY |
| Branch naming validation | ✅ | ❌ | ✅ | ✅ <sup id="f4">[\[4\]](#fn4)</sup> | DIY |
| Force push blocking | ✅ | ❌ | ❌ | ✅ | DIY |
| Author name / email validation | ✅ | ❌ | ✅ | ✅ <sup id="f4">[\[4\]](#fn4)</sup> | DIY |
| Signed-off-by trailer enforcement | ✅ | Partial <sup id="f1">[\[1\]](#fn1)</sup> | ❌ | ❌ | DIY |
| Co-author ignore list | ✅ | ❌ | Partial <sup id="f3">[\[3\]](#fn3)</sup> | ❌ | DIY |
| Organization-level shared config | ✅ | ✅ | ✅ | ✅ | DIY |
| Zero-config defaults | ✅ | ❌ | ❌ | ❌ | ❌ |
| Works without Node.js | ✅ | ❌ | ✅ | ✅ | Depends |
| Native TOML configuration | ✅ | ❌ | ❌ | ❌ | Depends |
| Git hook / pre-commit integration | ✅ | Partial | ❌ | ❌ | ✅ |
| CI/CD-friendly configuration | ✅ | Partial | ❌ | ❌ | DIY |
| Open source & free | ✅ | ✅ | ❌ | ❌ <sup id="f5">[\[5\]](#fn5)</sup> | ✅ |
| Client-side (pre-commit) enforcement | ✅ | ✅ | ❌ | ❌ | ✅ |
| AI-native (JSON API + Python SDK) | ✅ | ❌ | ❌ | ❌ | ❌ |

For `commitlint`, organization-level shared config is typically delivered via
shareable config packages or local files.

For `YACC` (Yet Another Commit Checker), conventional commit enforcement
is regex-based rather than Conventional Commits-aware; author validation
verifies committer name/email against Bitbucket user accounts or custom regex;
the plugin supports global → project → repository config inheritance;
it is a server-side pre-receive hook and merge check (no client-side
pre-commit), is paid (per-user licensing), and runs on Java (no Node.js needed).

For [GitHub Rulesets][github-rulesets], push rulesets enforce metadata via regex patterns —
they can match branch/tag names, commit messages, and author email, but have
no awareness of Conventional Commits semantics (types, scopes, breaking-change
markers).  They apply server-side and require a GitHub plan (Free for public
repos, Team/Enterprise for private/internal repos with push rulesets).  They
are not portable to other Git platforms and do not provide local pre-commit
feedback.

`DIY` means you can implement a
capability with custom Git hooks or `pre-commit` scripts, but it is not
provided as a turnkey policy layer.

<b id="fn1">[1]</b> `commitlint` provides a community `signed-off-by` rule
(`@commitlint/rule-signed-off-by`) that must be installed and configured
separately; it is not part of the default
`@commitlint/config-conventional` preset.
[↩](#f1)

<b id="fn2">[2]</b> [Yet Another Commit Checker](https://marketplace.atlassian.com/apps/1211854/yet-another-commit-checker)
is a paid Bitbucket Server / Data Center plugin (server-side pre-receive hook
and merge check).
[↩](#f2)

<b id="fn3">[3]</b> YACC can exclude commits from specific Bitbucket users, user groups,
or service users (bots), but does not parse `Co-authored-by:` trailers
in commit messages.
[↩](#f3)

<b id="fn4">[4]</b> GitHub Rulesets enforce these via regex patterns in push rulesets
(metadata restrictions).  They are regex-based and do not understand
Conventional Commits or Conventional Branch semantics.
[↩](#f4)

<b id="fn5">[5]</b> GitHub Rulesets require a GitHub plan.  Push rulesets (metadata
restrictions) require Team or Enterprise plans for private/internal repos;
branch/tag rulesets are available on Free plans for public repos.
[↩](#f5)

## Versioning

Versioning follows [Semantic Versioning](https://semver.org/).

## Have question or feedback?

Please post to [issues](https://github.com/commit-check/commit-check/issues) or start a [discussion](https://github.com/commit-check/commit-check/discussions) for feedback, feature requests, or bug reports.

## License

This project is released under the [MIT License](https://github.com/commit-check/commit-check/blob/main/LICENSE).
