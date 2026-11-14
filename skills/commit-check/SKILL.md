---
name: commit-check
description: Write commits, branch names and AI attribution that pass the project's commit-check policy (cchk.toml or commit-check.toml). Use before running git commit, when choosing a branch name, when a commit-check hook or CI check fails, or when the project has rules about AI co-authors and disclosure trailers.
license: MIT
compatibility: "Requires git and the commit-check CLI (Python 3.11+): pipx install commit-check, or run it with uvx commit-check."
metadata:
  source: https://github.com/commit-check/commit-check
  docs: https://commit-check.com
---

# Commit Check

[commit-check](https://commit-check.com) enforces a project's commit policy: commit message format, branch names, author name and email, sign-off, and whether AI tools may appear in a commit. The same policy runs in the pre-commit hook, in CI and on pull requests, so a commit that fails here will also fail there.

Check your work locally before you commit, so you fix it once instead of after review.

## 1. Read the project's policy

Look for the config file, in this order:

```text
cchk.toml
commit-check.toml
.github/cchk.toml
.github/commit-check.toml
```

Read it before you write a commit. It is the project's own rulebook: allowed commit types, subject length, whether a body or a `Signed-off-by` trailer is required, branch prefixes, and the AI attribution policy. If there is no file, the defaults apply: [Conventional Commits](https://www.conventionalcommits.org) messages and [Conventional Branch](https://conventionalbranch.org) names.

Check that the CLI is available with `commit-check --version`. If it is not installed, use `uvx commit-check` in place of `commit-check` in the commands below.

## 2. Check the message before you commit

Pipe the message you plan to use into the CLI:

```bash
printf '%s\n' "feat: add login page" | commit-check --message --compact
```

- Exit `0`: the message passes. Commit with exactly that text.
- Exit `1`: a rule failed. Each `[FAIL]` line names the rule (for example `CC001`) and what is wrong.
- Exit `2`: the config file is invalid or git cannot read the repository. Report it to the user; do not work around it.

For a multi-line message, write it to a file in the git directory, where it is never committed, and pass the path. Find the file with `git rev-parse --git-path`: in a worktree or a submodule `.git` is a file, not a directory, so `.git/COMMIT_MSG_DRAFT` cannot be written there.

```bash
draft="$(git rev-parse --git-path COMMIT_MSG_DRAFT)"
commit-check --message --compact "$draft"
```

Commit with `git commit -F "$draft"` once it passes.

To get the suggested fix in a form you can parse, add `--format json`. Each failed check has `error`, `suggest` and, when there is a mechanical fix, `fix` with the corrected text. Rule details are at `docs_url`.

When every failure has a mechanical fix (a type's case, a missing colon), `--fix` rewrites the file for you:

```bash
commit-check --message --fix "$draft"
```

Re-run the check after any change until it exits `0`.

## 3. Respect the AI attribution policy

The `ai_attribution` key under `[commit]` sets what the project accepts from AI tools:

| Value | What to do |
|---|---|
| `ignore` (default) | No rule. Follow the user's instructions. |
| `forbid` | Add no AI trailer or signature: no `Co-authored-by:` an AI tool, no "Generated with" line, no session link. Commit as the user, not as an agent identity. |
| `disclose` | Disclose AI help with an accepted trailer, `Assisted-by:` by default (the list is in `ai_disclosure_trailers`). Never list an AI tool as `Co-authored-by:` or `Signed-off-by:`. |

Under both `forbid` and `disclose`, a commit whose author is an AI tool fails (rule CC017). Commit with the user's git identity.

If `require_ai_session = true`, a commit you made must also link your session (rule CC018). Keep the link your tool writes, such as an `Agent-Logs-Url:` or `Entire-Checkpoint:` trailer or a Claude Code session URL, or add one of the trailers in `ai_session_trailers`. Never invent a link.

If the project forbids AI attribution but your tool adds a trailer on its own, remove the trailer from the message before committing; do not turn the check off.

To check only the AI rules on text that is not a commit message, such as a pull request description:

```bash
printf '%s\n' "$PR_BODY" | commit-check --ai-attribution-only --compact
```

## 4. Check the branch and author

```bash
commit-check --branch --compact          # current branch name
commit-check --author-name --author-email --compact
```

If the branch name fails, create a new branch with a compliant name and move your commits to it. Do not rename a branch that already has an open pull request without asking the user.

## Never bypass the check

- Do not run `git commit --no-verify` or `git commit -n`, and do not pass `--no-verify` to `git push`.
- Do not edit the config file, add yourself to `ignore_authors`, or add a rule to `warn` to make a failing check pass. Changing the policy is the user's decision.
- If a rule looks wrong for the change, stop and tell the user which rule failed and why.

## More

- Every rule, with examples: https://commit-check.com/rules/
- Configuration reference: https://commit-check.com
- Common AI policies as ready configs: https://commit-check.com/guides/policies/
