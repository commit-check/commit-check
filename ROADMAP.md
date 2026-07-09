# Roadmap

> _Last updated: 2026-07-09_

This document outlines the planned direction for **commit-check**. It is a living
document — priorities shift based on community feedback, contributor interest,
and ecosystem changes.

---

## Short Term (Next 1–3 Months)

### Quality & Infrastructure

- **End-to-end integration tests** — Add tests that operate on real (ephemeral)
  Git repositories to complement existing unit tests and catch regressions that
  mock-based tests miss.
- **Performance benchmarks** — Use CodSpeed or a similar CI benchmark runner to
  track per-PR performance for common validation paths.
- **SLSA Level 3 for PyPI** — Extend the existing artifact attestation workflow
  (used by the GitHub Action) to cover the PyPI package as well.

### Ecosystem

- **GitLab CI template** — Provide a ready-to-use `.gitlab-ci.yml` snippet so
  commit-check works natively in GitLab pipelines.
- **Homebrew formula** — Make `brew install commit-check` possible for macOS
  users who prefer Homebrew over pip.

### Documentation

- **Migration guide for v1 → v2** — The v2 release changed the config format
  from YAML to TOML. A dedicated migration guide will help existing users
  upgrade smoothly.
- **API reference** — Auto-generated reference docs for the `commit_check.api`
  Python module, hosted on the documentation site.

---

## Medium Term (3–6 Months)

### Features

- **Commit signature verification** — Support for GPG/SSH commit signature
  verification, a commonly requested feature (see issues #37, #217).
- **Custom commit type patterns** — Allow different regex patterns for different
  commit types (e.g., `feat` requires an issue reference, `fix` is optional).
- **Pre-receive hook variant** — A server-side hook script for self-hosted Git
  servers (GitLab, Gitea, etc.) that enforces commit-check policy on incoming
  pushes.
- **Auto‑fix mode** — A `--fix` flag that rewrites a non-compliant commit message
  to match the configured conventions (interactive, with confirmation).

### AI & Automation

- **Expanded AI attribution detection** — Broaden the catalog of detected AI tool
  signatures as new coding agents emerge.
- **LLM-friendly error context** — Enriched JSON output that includes the exact
  constraint that was violated and a machine-readable corrective action hint.

### Platform Support

- **VS Code extension** — A lightweight extension that surfaces commit-check
  results in the editor when composing commit messages.
- **Bitbucket Pipelines integration** — Example workflow and documentation for
  Bitbucket users.
- **Windows installer** — A standalone installer (e.g., via WiX or Inno Setup)
  for Windows users who do not use Python.

---

## Long Term (6+ Months)

### Enterprise & Scale

- **Centralized policy distribution** — A mechanism for organizations to publish
  and version commit policies from a central repository, consumed by many
  downstream repos without per-repo config changes.
- **Audit log / compliance reporting** — Generate structured reports of all
  commits checked, failures, and waivers — useful for SOC 2 / ISO 27001 audits.

### Community

- **Plugin system** — Allow third-party validators to be installed as plugins
  so the community can contribute new checks without modifying core.
- **Localization** — Support for error messages in multiple languages (中文,
  Español, etc.).

### Integrations

- **GitHub App / Checks API** — A GitHub App that posts commit-check results
  as check runs with inline annotations, without requiring workflow YAML changes.
- **pre-commit.ci integration** — Seamless support for the pre-commit.ci
  service, which auto-fixes PRs from automated hooks.

---

## How to Influence the Roadmap

The roadmap is driven by community input. If you'd like to see something
prioritized:

1. **Upvote existing issues** — 👍 reactions on GitHub Issues help gauge demand.
2. **Open a feature request** — Use the
   [feature request template](
   https://github.com/commit-check/commit-check/issues/new?template=feature-request.yml).
3. **Submit a PR** — Even a draft implementation goes a long way toward
   prioritization.

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to get started.

---

## Legend

| Status | Meaning |
|--------|---------|
| 🟢 Active | Being worked on or planned with a specific target |
| 🟡 Exploring | Under consideration, needs more input or research |
| 🔵 Future | Desired but no concrete timeline |
