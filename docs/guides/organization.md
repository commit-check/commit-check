# Enforce one policy across an organization

Copying `cchk.toml` into forty repositories works until the day you want to
change it. `inherit_from` lets each repository pull a shared base config and
override only what it genuinely needs.

## The shared config

Put the policy in a repository every project can read — GitHub's `.github`
repository is the conventional home:

```toml title="my-org/.github → cchk.toml"
[commit]
conventional_commits = true
subject_imperative = true
subject_max_length = 72
allow_merge_commits = false

[branch]
conventional_branch = true
allow_branch_types = ["feature", "bugfix", "hotfix", "release", "chore"]
```

## Inheriting it

Each repository then needs one line:

```toml title="any-repo → .github/cchk.toml"
inherit_from = "github:my-org/.github:cchk.toml"
```

Local settings win, so a project with a different constraint overrides just that
one option:

```toml title="a-repo-with-longer-subjects → .github/cchk.toml"
inherit_from = "github:my-org/.github:cchk.toml"

[commit]
subject_max_length = 100      # everything else comes from the org config
```

## Pinning the version

By default the shorthand resolves to the parent repository's default branch,
which means a change to the org config takes effect everywhere on the next run.
That is usually what you want. When it isn't, pin to a ref:

```toml
inherit_from = "github:my-org/.github@v1:cchk.toml"
```

## Other sources

=== "GitHub shorthand"

    ```toml
    inherit_from = "github:my-org/.github:cchk.toml"
    ```

=== "Local path"

    ```toml
    inherit_from = "../../shared/org-cchk.toml"
    ```

    Useful in a monorepo, where the shared config is already checked out.

=== "HTTPS URL"

    ```toml
    inherit_from = "https://example.com/shared/cchk.toml"
    ```

    Plain HTTP is rejected.

!!! warning "Inheritance fails open"

    If the parent config is unreachable — a network blip, a renamed file, a
    private repository — Commit Check silently falls back to the local config
    rather than failing the build. This keeps CI green during an outage, but it
    also means a typo in `inherit_from` is easy to miss. Verify the merged
    result when you first set it up:

    ```console
    $ commit-check --message --format json
    ```

## Rolling it out

Turning on a strict policy across an organization at once produces a wall of
red. A gentler sequence:

1. Ship the org config with `dry-run` enabled in CI, so violations are reported
   but nothing blocks.
2. Look at what actually fails. Some rules will turn out to be wrong for some
   teams — that is information, not an obstacle.
3. Turn off `dry-run` for repositories whose history is already clean.
4. Tighten the shared config over time.

See the [GitHub Actions guide](github-actions.md) for the `dry-run` input.
