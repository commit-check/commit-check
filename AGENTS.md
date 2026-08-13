# AGENTS.md — AI Agent Guidelines

This file provides working guidelines for AI coding agents (e.g., GitHub Copilot, Claude Code, Cursor, etc.) contributing to this repository.

## Workflow

- All changes must be submitted to the `main` branch **via a pull request**. Never push commits directly to `main`.

## Keep the README pinned to the released version

**Do this on every change, whatever you came here to do.** It is not a release-time task — the README's pre-commit snippets are the first thing a new user copies, and a stale pin is invisible: the snippet keeps working, it just installs an older release than the README describes. Nothing in the test suite reads these pins, so only this check catches them. They had fallen three releases behind before anyone noticed.

1. **Find the latest released version.**

   ```console
   $ curl -s https://pypi.org/pypi/commit-check/json | python -c "import json,sys; print(json.load(sys.stdin)['info']['version'])"
   ```

   The [releases page](https://github.com/commit-check/commit-check/releases) answers the same question. A **draft** release is not released — it has no tag and no package, so it is not the answer here.

2. **Check every pin in the README.**

   ```console
   $ grep -n "rev: v" README.md
   ```

   Each one must name that version. Update any that do not, in the same pull request — do not open a follow-up issue for it.

3. **Say so in the pull request description** when you moved them, so the bump is not a silent diff in an unrelated change.

The one exception is a pull request that prepares an unpublished release: there the pins are written **ahead** of the tag, on purpose, and the release is published before the pull request merges.

`.pre-commit-config.yaml` is a different case and is **not** covered by this rule. That pin is this repository running its own hooks, and pre-commit resolves it against real tags when CI runs — so pointing it at a version that is not published yet breaks the build. Bump it only after the release exists.

## Git Rules

- **Follow the Conventional Branch spec** for branch names: `<type>/<description>` with lowercase kebab-case descriptions. Allowed types: `feature/`, `bugfix/`, `hotfix/`, `release/`, `chore/`. Example: `chore/add-agent-guidelines`.
- **Follow the Conventional Commits spec** for commit messages: `<type>: <description>` (e.g., `feat: ...`, `fix: ...`, `chore: ...`, `docs: ...`).
- **No force push.** Never use `git push --force` or `git push --force-with-lease`.
- **Additive commits only.** When addressing review feedback, add new commits on top. Never rebase, squash commits (e.g., do not use `git rebase -i` to squash history after the PR is open).

## Staging Files

- Stage **only the files you changed**: `git add <file>...`.
- Never use `git add .` / `git add -A` / `git add --all`, and never stage unrelated or generated files.
