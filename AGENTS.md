# AGENTS.md — AI Agent Guidelines

This file provides working guidelines for AI coding agents (e.g., GitHub Copilot, Claude Code, Cursor, etc.) contributing to this repository.

## Workflow

- All changes must be submitted to the `main` branch **via a pull request**. Never push commits directly to `main`.

## Git Rules

- **Follow the Conventional Branch spec** for branch names: `<type>/<description>` with lowercase kebab-case descriptions. Allowed types: `feature/`, `bugfix/`, `hotfix/`, `release/`, `chore/`. Example: `chore/add-agent-guidelines`.
- **Follow the Conventional Commits spec** for commit messages: `<type>: <description>` (e.g., `feat: ...`, `fix: ...`, `chore: ...`, `docs: ...`).
- **No force push.** Never use `git push --force` or `git push --force-with-lease`.
- **Additive commits only.** When addressing review feedback, add new commits on top. Never rebase, squash commits (e.g., do not use `git rebase -i` to squash history after the PR is open).

## Staging Files

- Stage **only the files you changed**: `git add <file>...`.
- Never use `git add .` / `git add -A` / `git add --all`, and never stage unrelated or generated files.
