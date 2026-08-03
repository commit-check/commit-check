# Quick start

By the end of this page you will have Commit Check rejecting a bad commit
message on your machine, and you will understand what it is telling you.

It takes about five minutes and needs nothing but a Git repository.

## 1. Install

```console
$ pip install commit-check
```

## 2. Watch it reject something

Commit Check works with no configuration at all. Make a deliberately bad commit
in a scratch repository:

```console
$ git init demo && cd demo
$ git commit --allow-empty -m "updated the parser"
```

Now check it:

```console
$ commit-check --message
```

```text
CC001 message check failed ==> updated the parser
The commit message should follow Conventional Commits. See https://www.conventionalcommits.org
Suggest: Use <type>(<scope>): <description>, where <type> is one of: feat, fix, docs, ...
Docs: https://docs.commit-check.com/rules/#cc001
```

Four things are happening in that output, and each is deliberate:

| Part | What it gives you |
|---|---|
| `CC001` | A stable rule ID. It will mean the same thing in five years. |
| `==> updated the parser` | The exact value that failed, not just "invalid message". |
| `Suggest:` | What to do about it. |
| `Docs:` | Why the rule exists, and how to configure or disable it. |

## 3. Fix it

```console
$ git commit --amend -m "fix(parser): handle empty input"
$ commit-check --message
```

No output and an exit code of `0`. Commit Check is quiet when it is happy.

## 4. Check the branch too

```console
$ git switch -c my-changes
$ commit-check --branch
```

```text
CC201 branch check failed ==> my-changes
The branch should follow Conventional Branch. See https://conventionalbranch.org
Suggest: Use <type>/<description> with allowed types
Docs: https://docs.commit-check.com/rules/#cc201
```

Rename it to something structured and it passes:

```console
$ git branch -m fix/empty-input
$ commit-check --branch
```

!!! tip "Checks are opt-in per run"

    `commit-check --message` never evaluates branch rules, and vice versa. Each
    check is selected by its own flag, so you can run exactly what a given hook
    or CI job needs. The
    [rules reference](../rules.md) lists which flag activates each rule.

## 5. Write down your policy

So far you have been running the defaults. Create a `cchk.toml` in the
repository root — or in `.github/` — to make the policy explicit:

```toml title="cchk.toml"
[commit]
conventional_commits = true
subject_imperative = true          # (1)!
subject_max_length = 72
allow_wip_commits = false          # (2)!

[branch]
conventional_branch = true
```

1. Off by default. Turning it on rejects `fixed a bug` in favour of `fix a bug`.
2. `allow_*` options describe what is *permitted*. Set to `false` to enforce.

Run it again and the new rules apply:

```console
$ commit-check --message
```

!!! warning "Defaults are not "nothing""

    Even with no config file, Conventional Commits, Conventional Branch, subject
    length limits of 5–80 characters, and author name/email patterns are
    enforced. Check the *Default* column in the
    [rules reference](../rules.md) before assuming a rule is off.

## 6. Make it automatic

Running the command by hand does not scale. Wire it into the two places it
belongs:

<div class="grid cards" markdown>

-   :material-git:{ .lg .middle } __Before the commit lands__

    ---

    A pre-commit hook rejects the message as you write it, so nothing bad
    reaches the branch in the first place.

    [:octicons-arrow-right-24: Pre-commit guide](../guides/pre-commit.md)

-   :material-github:{ .lg .middle } __On every pull request__

    ---

    A GitHub Action checks every commit in the PR and can comment on the PR
    with what needs fixing.

    [:octicons-arrow-right-24: GitHub Actions guide](../guides/github-actions.md)

</div>

## Where to go next

- **[Rules reference](../rules.md)** — every rule, what it does, why it matters,
  and how to configure it.
- **[Configuration](../configuration.md)** — every option, its type and default,
  plus the environment variable and CLI flag that override it.
- **[Why Commit Check](why.md)** — the reasoning behind the tool.
