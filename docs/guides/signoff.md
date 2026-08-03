# Require signoff (DCO)

Projects that use the [Developer Certificate of Origin](https://developercertificate.org/)
require every commit to carry a `Signed-off-by` trailer. The Linux kernel and
much of the CNCF work this way.

A DCO bot rejecting a pull request after the fact is a poor experience: the
contributor has to rewrite history for every commit in the branch. Checking
locally fixes it before it becomes a problem.

## Turn it on

```toml title="cchk.toml"
[commit]
require_signed_off_by = true
```

This enables [CC012](../rules.md#cc012), which is off by default.

## Signing off

```console
$ git commit --signoff -m "fix: handle an empty config file"
```

The trailer is appended automatically from your `user.name` and `user.email`:

```text
fix: handle an empty config file

Signed-off-by: Your Name <you@example.com>
```

Forgot it? Fix the last commit in place:

```console
$ git commit --amend --signoff --no-edit
```

Fix a whole branch:

```console
$ git rebase --signoff main
```

!!! tip "Make it automatic"

    Signing off is easy to forget. Combine this rule with the
    [pre-commit hook](pre-commit.md) so a missing trailer is caught at commit
    time, not at review time.

## Identity matters

The DCO is a statement about who wrote the code, so it only means something if
the identity is real. [CC101](../rules.md#cc101) and
[CC102](../rules.md#cc102) check the committer name and email, and are enabled
by default when their check runs:

```console
$ commit-check --author-name --author-email
```

To require a company address:

```toml title="cchk.toml"
[commit]
author_email_pattern = "^.+@example\\.com$"
```

## Bots

Automation cannot meaningfully sign the DCO, and forcing it to produces
meaningless trailers. Exempt bots instead:

```toml title="cchk.toml"
[commit]
require_signed_off_by = true
ignore_authors = ["dependabot[bot]", "renovate[bot]"]
```

`ignore_authors` matches the commit author and any `Co-authored-by:` trailers.
