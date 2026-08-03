# Release highlights

The changes worth knowing about, newest first, each pointing at the page that
documents it properly. For the full record of every change, see the
[changelog](changelog.md).

## 2.11.0 — AI attribution policy

Commits carrying the trailers AI coding tools add — Claude Code, Copilot,
Codex, Gemini, Cursor, Devin, Aider, Windsurf, Tabby — can now be rejected.

```toml title="cchk.toml"
[commit]
ai_attribution = "forbid"   # "ignore" is the default
```

Whether AI-assisted commits are acceptable is a policy question with no single
right answer, so this stays off until you turn it on.

[:octicons-arrow-right-24: AI attribution guide](guides/ai-attribution.md) ·
[CC013](rules.md#cc013)

## 2.10.0 — Bot branch prefixes accepted by default

`dependabot/` and `renovate/` branches pass branch validation without
configuration. Automation was previously failing a check it could not satisfy.

[:octicons-arrow-right-24: CC201](rules.md#cc201)

## 2.9.0 — AI agent branch prefixes accepted by default

`ai/`, `claude/`, `codex/`, `copilot/` and `cursor/` joined the default branch
types, following
[Conventional Branch v1.1.0](https://conventional-branch.github.io/).

[:octicons-arrow-right-24: CC201](rules.md#cc201)

## 2.8.0 — Custom message patterns

`message_pattern` replaces the generated Conventional Commits regex with one of
your own, for teams that already enforce a different format.

```toml title="cchk.toml"
[commit]
message_pattern = "^PROJ-\\d+: .+"
```

This release also dropped Python 3.9. The minimum is now 3.10.

[:octicons-arrow-right-24: CC001](rules.md#cc001) ·
[Configuration](configuration.md)

## 2.7.0 — Force push blocking

A `pre-push` hook that refuses a force push to a shared branch, plus a
`--no-force-push` flag for running the same check by hand.

```toml title="cchk.toml"
[push]
allow_force_push = false
```

[:octicons-arrow-right-24: CC301](rules.md#cc301) ·
[Command-line recipes](example.md#blocking-force-pushes)

## 2.6.0 — Output controls for scripts and CI

`--format json` for machine-readable results, `--compact` for one line per
failure, and `--no-banner` to drop the ASCII art that only adds noise to a CI
log.

[:octicons-arrow-right-24: Command-line recipes](example.md#output-for-scripts-and-ci)

## 2.5.0 — Organization-wide configuration

`inherit_from` lets a repository pull a shared base config and override only
what it needs, so a policy change no longer means editing every repository.

```toml title=".github/cchk.toml"
inherit_from = "github:my-org/.github:cchk.toml"
```

[:octicons-arrow-right-24: Organization guide](guides/organization.md)

## 2.0.0 — TOML configuration

The configuration format moved from YAML to TOML, the CLI was simplified, and
settings became overridable by environment variable and command-line flag.
This is a breaking change from 1.x.

[:octicons-arrow-right-24: Migrating from v1](migration.md)
