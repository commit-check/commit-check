<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/commit-check/.github/main/branding/banner-dark.png">
  <img src="https://raw.githubusercontent.com/commit-check/.github/main/branding/banner-light.png" alt="Commit Check">
</picture>

**Catch bad commits before they merge.**

[![PyPI](https://img.shields.io/pypi/v/commit-check?labelColor=0b1620&logo=pypi&logoColor=white&color=2c9ccd)](https://pypi.org/project/commit-check/)
[![Downloads](https://img.shields.io/pepy/dt/commit-check?labelColor=0b1620&color=2c9ccd)](https://pepy.tech/projects/commit-check)
[![CI](https://img.shields.io/github/actions/workflow/status/commit-check/commit-check/main.yml?branch=main&labelColor=0b1620&label=CI)](https://github.com/commit-check/commit-check/actions/workflows/main.yml)
[![Coverage](https://img.shields.io/codecov/c/github/commit-check/commit-check?labelColor=0b1620&color=2c9ccd&label=coverage)](https://codecov.io/gh/commit-check/commit-check)
[![OpenSSF Scorecard](https://img.shields.io/ossf-scorecard/github.com/commit-check/commit-check?labelColor=0b1620&color=2c9ccd&label=OpenSSF%20Scorecard)](https://scorecard.dev/viewer/?uri=github.com/commit-check/commit-check)

[Docs](https://commit-check.com/getting-started/) ·
[Rules](https://commit-check.com/rules/) ·
[GitHub Action](https://github.com/commit-check/commit-check-action) ·
[GitHub App](https://github.com/apps/commit-check) ·
[MCP server](https://github.com/commit-check/commit-check-mcp)

</div>

**Commit Check** validates commit messages, branch names, authors, sign-offs,
tags, committed files and AI attribution against one `cchk.toml` — in your
commit hook, in CI, on every pull request and inside your AI agent. When the
fix is obvious, it hands you the line.

![commit-check demo](https://github.com/commit-check/commit-check/raw/main/assets/demo.gif)

## Quick start

```bash
pip install commit-check        # Python 3.10+
commit-check --message --branch
```

No config needed: out of the box it checks [Conventional Commits](https://www.conventionalcommits.org)
and [Conventional Branch](https://conventionalbranch.org).

### Use with pre-commit

Stop bad commits before they exist. In `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/commit-check/commit-check
    rev: v2.18.1
    hooks:
      - id: check-message
      - id: check-branch
```

The hooks for the other checks (`check-author-name`, `check-author-email`,
`check-no-force-push`, `check-tag`, `check-files`) are listed in the
[pre-commit guide](https://commit-check.com/guides/pre-commit/).

### Everywhere else

The same `cchk.toml` drives all of them:

| Run it in | How |
|---|---|
| GitHub Actions | `uses: commit-check/commit-check-action@v2` — see [commit-check-action](https://github.com/commit-check/commit-check-action) |
| GitHub, no workflow | [Install the GitHub App](https://github.com/apps/commit-check) — one check run per commit |
| AI agents | `--format json`, the [Python API](#ai-native-usage), or the [MCP server](https://github.com/commit-check/commit-check-mcp) |

## What it checks

| Check | Flag | Rules |
|---|---|---|
| Commit message — Conventional Commits, subject length, case and mood, WIP and fixup commits, body, sign-off | `--message` | CC001–CC012 |
| AI attribution — forbid it, or require an `Assisted-by:` disclosure | `--message` | CC013–CC016 |
| Author name and email | `--author-name` `--author-email` | CC101–CC102 |
| Branch name — Conventional Branch, rebased onto a target | `--branch` | CC201–CC202 |
| Force push | `--no-force-push` | CC301 |
| Committed files — size, forbidden paths, path length | `--files` | CC302–CC304 |
| Tag names — SemVer or your own pattern | `--tag` | CC401 |

Every rule, with examples: [commit-check.com/rules](https://commit-check.com/rules/)

## Configure

Put a `cchk.toml` (or `commit-check.toml`) in the repository root or in `.github/`:

```toml
[commit]
subject_max_length = 72
require_signed_off_by = true
ai_attribution = "disclose"
ignore_authors = ["dependabot[bot]", "renovate[bot]"]

[branch]
conventional_branch = true
```

- **Roll out gently:** `warn = ["CC003"]` reports a rule in full without failing the run.
- **One policy per organization:** `inherit_from = "github:my-org/.github:cchk.toml"` — see [organization config](https://commit-check.com/guides/organization/).
- **Override anywhere:** every key has a CLI flag and a `CCHK_*` environment variable.
- **Editor support:** the schema is on [SchemaStore](https://www.schemastore.org/), so VS Code and JetBrains autocomplete `cchk.toml`.

<details>
<summary><b>Configuration reference</b> — every key, its default, CLI flag and environment variable</summary>

Priority: CLI > env > TOML > default. Booleans accept `true/false`, `yes/no`,
`1/0`; lists are comma-separated on the CLI and in env vars.

| Key | Default | CLI flag | Env var | Meaning |
|-----|---------|----------|---------|---------|
| `warn` (top level) | `[]` | — | — | Checks or rule IDs to report without failing the run (see "Report a rule without enforcing it") |
| `commit.conventional_commits` | `true` | `--conventional-commits` | `CCHK_CONVENTIONAL_COMMITS` | Enforce the Conventional Commits format (CC001) |
| `commit.message_pattern` | `""` | — | `CCHK_MESSAGE_PATTERN` | Custom regex the whole message must match; when set it replaces the Conventional Commits check (still reported as CC001) |
| `commit.subject_capitalized` | `false` | `--subject-capitalized` | `CCHK_SUBJECT_CAPITALIZED` | Require the subject to start with a capital letter (CC002) |
| `commit.subject_imperative` | `false` | `--subject-imperative` | `CCHK_SUBJECT_IMPERATIVE` | Require the subject to use the imperative mood (CC003) |
| `commit.subject_max_length` | `80` | `--subject-max-length` | `CCHK_SUBJECT_MAX_LENGTH` | Maximum subject length (CC004) |
| `commit.subject_min_length` | `5` | `--subject-min-length` | `CCHK_SUBJECT_MIN_LENGTH` | Minimum subject length (CC005) |
| `commit.allow_commit_types` | `feat, fix, docs, style, refactor, test, chore, perf, build, ci` | `--allow-commit-types` | `CCHK_ALLOW_COMMIT_TYPES` | Allowed `<type>` values in the subject |
| `commit.allow_merge_commits` | `true` | `--allow-merge-commits` | `CCHK_ALLOW_MERGE_COMMITS` | Allow merge commits (CC006) |
| `commit.allow_revert_commits` | `true` | `--allow-revert-commits` | `CCHK_ALLOW_REVERT_COMMITS` | Allow revert commits (CC007) |
| `commit.allow_empty_commits` | `true` | `--allow-empty-commits` | `CCHK_ALLOW_EMPTY_COMMITS` | Allow empty commit messages (CC008) |
| `commit.allow_fixup_commits` | `true` | `--allow-fixup-commits` | `CCHK_ALLOW_FIXUP_COMMITS` | Allow `fixup!` commits (CC009) |
| `commit.allow_wip_commits` | `true` | `--allow-wip-commits` | `CCHK_ALLOW_WIP_COMMITS` | Allow WIP commits (CC010) |
| `commit.require_body` | `false` | `--require-body` | `CCHK_REQUIRE_BODY` | Require a commit body (CC011) |
| `commit.require_signed_off_by` | `false` | `--require-signed-off-by` | `CCHK_REQUIRE_SIGNED_OFF_BY` | Require a `Signed-off-by:` trailer (CC012) |
| `commit.ignore_authors` | `[]` | `--ignore-authors` | `CCHK_IGNORE_AUTHORS` | Authors and co-authors whose commits skip the commit checks |
| `commit.ai_attribution` | `"ignore"` | `--ai-attribution` | `CCHK_AI_ATTRIBUTION` | `ignore`, `forbid` or `disclose`. `forbid` rejects commits carrying known AI tool signatures (CC013); `disclose` accepts AI assistance disclosed with one of `ai_disclosure_trailers` (CC014) and rejects the tool as a co-author (CC015) or as a sign-off (CC016) |
| `commit.ai_disclosure_trailers` | `Assisted-by, Generated-by` | `--ai-disclosure-trailers` | `CCHK_AI_DISCLOSURE_TRAILERS` | Trailers that disclose AI assistance under `disclose`; the first is the one a fix is written with. List `Co-authored-by` to accept the tool as a co-author |
| `commit.ai_disclosure_pattern` | `""` | `--ai-disclosure-pattern` | `CCHK_AI_DISCLOSURE_PATTERN` | Regex the disclosure's value must match under `disclose`, e.g. `^\S+/\S+` for `agent/model`; empty accepts any value, but a trailer with no value at all is always reported |
| `commit.author_email_pattern` | `"^.+@.+$"` | `--author-email-pattern` | `CCHK_AUTHOR_EMAIL_PATTERN` | Regex the author email must match (CC102, with `--author-email`) |
| `commit.author_name_pattern` | `""` | `--author-name-pattern` | `CCHK_AUTHOR_NAME_PATTERN` | Regex the author name must match (CC101, with `--author-name`) |
| `branch.conventional_branch` | `true` | `--conventional-branch` | `CCHK_CONVENTIONAL_BRANCH` | Enforce `<type>/<description>` branch names (CC201) |
| `branch.allow_branch_types` | `feature, bugfix, hotfix, release, chore, feat, fix, build, ci, docs, perf, refactor, test, style, ai, claude, codex, copilot, cursor, dependabot, renovate` | `--allow-branch-types` | `CCHK_ALLOW_BRANCH_TYPES` | Allowed branch `<type>` prefixes; each entry is a regex matched against the whole type |
| `branch.allow_branch_names` | `[]` | `--allow-branch-names` | `CCHK_ALLOW_BRANCH_NAMES` | Extra branch names allowed besides `main`, `master`, `HEAD`, `PR-.+`; each entry is a regex matched against the whole branch name, so `create-pull-request/.+` allows a family of them |
| `branch.require_rebase_target` | `""` | `--require-rebase-target` | `CCHK_REQUIRE_REBASE_TARGET` | Branch the current branch must be rebased onto (CC202); empty disables |
| `branch.ignore_authors` | `[]` | `--branch-ignore-authors` | `CCHK_BRANCH_IGNORE_AUTHORS` | Authors whose branches skip the branch checks |
| `push.allow_force_push` | `true` | — (`--no-force-push` runs the check) | `CCHK_ALLOW_FORCE_PUSH` | Reserved; has no effect today. CC301 runs only with `--no-force-push`, which always rejects a non-fast-forward push |
| `tag.regex` | SemVer with optional `v` | `--tag-regex` | `CCHK_TAG_REGEX` | Pattern tag names must match (CC401); empty disables |
| `files.max_size` | `""` (off) | `--files-max-size` | `CCHK_FILES_MAX_SIZE` | Largest committed file, in bytes or with `KB`/`MB`/`GB` (CC302) |
| `files.prohibited_patterns` | `[]` | `--files-prohibited-patterns` | `CCHK_FILES_PROHIBITED_PATTERNS` | fnmatch patterns committed paths must not match (CC303) |
| `files.max_path_length` | `0` (off) | `--files-max-path-length` | `CCHK_FILES_MAX_PATH_LENGTH` | Longest allowed committed path, in characters (CC304) |

Output and appearance are per-run flags, not configuration: `--format json`,
`--no-banner`, `--compact`, `--dry-run`, `--rev`, `--config`. Color follows
`NO_COLOR` / `FORCE_COLOR`. Long-form descriptions: [commit-check.com/configuration](https://commit-check.com/configuration/)

</details>

## AI-native usage

`--format json` gives each check a stable rule ID, the value it saw and a
suggestion — plus the corrected value itself when the correction is
mechanical, so an agent can apply it without interpreting anything:

```bash
echo "Fix: add streaming support" | commit-check -m --format json
```

The failing entry of its `checks` array:

```json
{
  "rule_id": "CC001",
  "check": "message",
  "status": "fail",
  "value": "Fix: add streaming support",
  "error": "The commit message should follow Conventional Commits. See https://www.conventionalcommits.org",
  "suggest": "Use \"fix: add streaming support\"",
  "fix": "fix: add streaming support",
  "docs_url": "https://commit-check.com/rules/#cc001"
}
```

The same result, without a subprocess:

```python
from commit_check.api import validate_message

validate_message("feat: add streaming support")["status"]  # "pass"
```

`commit_check.api` also has `validate_branch`, `validate_author` and
`validate_all`; each takes an optional `config` dict and returns the same shape.

Exit codes: `0` passed · `1` a check failed · `2` nothing was checked — bad
usage, or a config that is missing, is not valid TOML, names an unknown rule or
holds a regex that does not compile. `--dry-run` reports everything and exits `0`. More output formats: [examples](https://commit-check.com/example/).

## Why Commit Check

| | Commit Check | commitlint | GitHub Rulesets |
|---|:-:|:-:|:-:|
| Conventional Commits | ✅ | ✅ | regex only |
| Branch, tag, author and file rules | ✅ | ❌ | ✅\* |
| Feedback before the push | ✅ | ✅ | ❌ |
| Works with zero config | ✅ | ❌ | ❌ |
| No Node.js | ✅ | ❌ | ✅ |
| JSON output, Python API, MCP | ✅ | ❌ | ❌ |

\*Push rulesets need a Team or Enterprise plan for private repositories.
The full comparison, including YACC and custom hooks: [commit-check.com/compare](https://commit-check.com/compare/tools/)

## Show that you use it

[![commit-check](https://commit-check.com/badge.svg)](https://commit-check.com)

```text
[![commit-check](https://commit-check.com/badge.svg)](https://commit-check.com)
```

## Community

Questions and ideas go to [Discussions](https://github.com/commit-check/commit-check/discussions),
bugs to [Issues](https://github.com/commit-check/commit-check/issues).
Releases follow [Semantic Versioning](https://semver.org/). Released under the
[MIT License](https://github.com/commit-check/commit-check/blob/main/LICENSE).
