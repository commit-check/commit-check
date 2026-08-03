# Command-line recipes

Ways to invoke the checks directly. For wiring them into a workflow, see the
[pre-commit](guides/pre-commit.md) and [GitHub Actions](guides/github-actions.md)
guides instead — those cover the setup this page assumes you already have.

Every option is listed in the [CLI reference](cli.md).

## Checking a commit message

The message can come from the repository, a file, or standard input.

=== "From the repository"

    Validates `HEAD`'s message. This is what the `commit-msg` hook runs.

    ```console
    $ commit-check -m
    ```

=== "From a file"

    ```console
    $ commit-check -m commit_message.txt
    ```

=== "From stdin"

    Useful in scripts and for trying a message before committing it.

    ```console
    $ echo "feat(auth): add OAuth2 login" | commit-check -m
    ```

### Trying a message before you write it

```console
$ echo "updated the parser" | commit-check -m
CC001 message check failed ==> updated the parser
The commit message should follow Conventional Commits.
Suggest: Use <type>(<scope>): <description>, where <type> is one of: feat, fix, ...
Docs: https://docs.commit-check.com/rules/#cc001
```

Fix it and it goes quiet:

```console
$ echo "fix(parser): handle empty input" | commit-check -m
```

### Multi-line messages

A body and trailers survive a heredoc, so you can test the whole thing:

```console
$ cat > /tmp/msg.txt << 'EOF'
fix(auth): resolve login timeout

Users were timing out during login. Raises the session timeout and
reports the failure instead of hanging.

Fixes #123
EOF
$ commit-check -m /tmp/msg.txt
```

## Checking the branch

```console
$ commit-check --branch
```

Runs [CC201](rules.md#cc201), and [CC202](rules.md#cc202) if
`require_rebase_target` is set. `master`, `main`, `HEAD` and `PR-*` are always
accepted; everything else needs a `<type>/<description>` shape:

```text
fix/empty-config-crash
feature/role-caching
release/v1.2.0
```

## Checking the committer

```console
$ commit-check --author-name --author-email
```

Either flag works alone. [CC101](rules.md#cc101) and
[CC102](rules.md#cc102) describe what the built-in patterns accept and how to
tighten them.

## Blocking force pushes

```console
$ commit-check --no-force-push
```

Compares the current branch against its upstream and fails if pushing would
require a force. Better as a `pre-push` hook, which sees the actual refs being
pushed:

```yaml title=".pre-commit-config.yaml"
repos:
  - repo: https://github.com/commit-check/commit-check
    rev: v2.11.0
    hooks:
      - id: check-no-force-push
        stages: [pre-push]
```

!!! warning "Piping `git push` into it does not prevent anything"

    `git push | commit-check --no-force-push` reads too late — the push has
    already started — and `git push` output does not carry the ref lines Git
    hands to a `pre-push` hook. Install the hook instead.

## Pointing at a different config

```console
$ commit-check -m --config /path/to/cchk.toml
```

Useful for testing a policy change before committing it, or for a monorepo
where one directory follows different rules. See
[Configuration](configuration.md) for where the file is looked up by default
and how CLI, environment and file settings override each other.

## Output for scripts and CI

=== "JSON"

    Machine-readable, one object per check, including `rule_id` and `docs_url`.

    ```console
    $ commit-check -m --format json
    ```

=== "Compact"

    One line per failure. Implies `--no-banner`.

    ```console
    $ commit-check -m --compact
    [FAIL] CC003 subject_imperative: docs: revamped the profile
    ```

=== "No banner"

    Plain text without the ASCII art, which is noise in a CI log.

    ```console
    $ commit-check -m --no-banner
    ```

=== "Dry run"

    Reports problems but always exits `0`. For adopting the policy on a
    repository whose history is not clean yet.

    ```console
    $ commit-check -m --dry-run
    ```

### Checking a range of commits

Nothing built in, but the exit code makes it a one-liner:

```bash title="check-recent.sh"
#!/usr/bin/env bash
# Check the last N commit messages; exits non-zero if any fail.
status=0
for sha in $(git rev-list -n "${1:-10}" HEAD); do
  if ! git log -1 --format=%B "$sha" | commit-check -m --compact; then
    echo "  ↑ $sha"
    status=1
  fi
done
exit $status
```

### Reading the JSON

```console
$ commit-check -m --format json | jq -r '.checks[] | select(.status == "fail") | .rule_id'
CC001
```

Each failed check carries the rule ID, the offending value, the suggestion and
a link to its documentation — the same information the text output prints, in a
form other tools can consume.
