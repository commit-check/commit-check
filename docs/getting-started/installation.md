# Installation

Commit Check runs anywhere Python does, and ships as a GitHub Action and an MCP
server for the places it doesn't.

## Command line

=== "pip"

    ```console
    $ pip install commit-check
    ```

=== "uv"

    ```console
    $ uv tool install commit-check
    ```

=== "pipx"

    ```console
    $ pipx install commit-check
    ```

Verify the install:

```console
$ commit-check --version
```

The CLI is also available as `cchk`, which is the same program under a shorter
name.

!!! tip "Supported Python versions"

    Commit Check supports Python 3.10 through 3.14, on Linux, macOS and Windows.

## As a pre-commit hook

No installation step — [pre-commit](https://pre-commit.com) fetches it for you.
See the [pre-commit guide](../guides/pre-commit.md).

## As a GitHub Action

No installation step. See the
[GitHub Actions guide](../guides/github-actions.md).

## Verifying the download

Releases are built with [SLSA Level 3](https://slsa.dev) provenance. To verify a
release artifact came from this repository's build pipeline:

```console
$ gh attestation verify commit_check-*.whl --repo commit-check/commit-check
```

## Next steps

<div class="grid cards" markdown>

-   :material-rocket-launch-outline:{ .lg .middle } __Quick start__

    ---

    Catch your first bad commit in five minutes.

    [:octicons-arrow-right-24: Quick start](quickstart.md)

-   :material-book-open-variant:{ .lg .middle } __Rules reference__

    ---

    Every rule, what it does, and why it matters.

    [:octicons-arrow-right-24: Rules](../rules.md)

</div>
