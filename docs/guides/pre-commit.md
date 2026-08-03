# Run as a pre-commit hook

A pre-commit hook is the cheapest place to enforce commit policy: the developer
finds out while they are still writing the message, not after a CI round trip.

## Setup

Add Commit Check to `.pre-commit-config.yaml`:

```yaml title=".pre-commit-config.yaml"
repos:
  - repo: https://github.com/commit-check/commit-check
    rev: v2.11.0
    hooks:
      - id: check-message
      - id: check-branch
      - id: check-author-name
      - id: check-author-email
```

Then install the hooks. `check-message` runs at the `commit-msg` stage, so it
needs its own install step:

```console
$ pre-commit install --hook-type commit-msg
$ pre-commit install
```

That is it. The next malformed commit message is rejected before it exists.

## Available hooks

| Hook ID | Stage | Rules |
|---|---|---|
| `check-message` | `commit-msg` | [CC001–CC013](../rules.md#commit-message-rules) |
| `check-branch` | `pre-commit` | [CC201–CC202](../rules.md#branch-rules) |
| `check-author-name` | `pre-commit` | [CC101](../rules.md#cc101) |
| `check-author-email` | `pre-commit` | [CC102](../rules.md#cc102) |
| `check-no-force-push` | `pre-push` | [CC301](../rules.md#cc301) |

`check-no-force-push` also needs its own install:

```console
$ pre-commit install --hook-type pre-push
```

## Configuring without a TOML file

Options can be passed as hook arguments, which keeps everything in one file:

```yaml title=".pre-commit-config.yaml"
repos:
  - repo: https://github.com/commit-check/commit-check
    rev: v2.11.0
    hooks:
      - id: check-message
        args:
          - --subject-imperative=true
          - --subject-max-length=72
          - --allow-merge-commits=false
```

A `cchk.toml` is usually the better choice once you have more than a couple of
options, because CI and the CLI read it too. See
[Configuration](../configuration.md) for the precedence rules.

## Skipping a hook

Occasionally you need to get a commit through — a mid-rebase fixup, an
automated migration. `pre-commit` supports this natively:

```console
$ SKIP=check-message git commit -m "wip"
```

!!! warning "Local hooks are not a policy boundary"

    Anyone can pass `--no-verify`. Hooks exist to give fast feedback to people
    who want to follow the policy, not to stop people who don't. Pair them with
    the [GitHub Action](github-actions.md), which runs where it cannot be
    skipped.

## Troubleshooting

If `check-message` never seems to run, it is almost always because
`pre-commit install --hook-type commit-msg` was not run — a plain
`pre-commit install` only wires up the `pre-commit` stage.

More in [Troubleshooting](../troubleshoot.md).
