# Bitbucket Pipelines Pipe: Commit Check

Check a pull request against your team's commit policy: the source branch name, every commit message the pull request adds, and optionally the commit authors, the changed files, and the pull request's title and description. The rules live in `cchk.toml` in your repository, the same file the [Commit Check](https://commit-check.com/) CLI, pre-commit hooks and GitHub Action read.

## YAML Definition

Add the following snippet to the script section of your `bitbucket-pipelines.yml` file:

```yaml
- pipe: commit-check/commit-check:2.25.0
  variables:
    # MESSAGE: '<boolean>' # Optional
    # BRANCH: '<boolean>' # Optional
    # AUTHOR_NAME: '<boolean>' # Optional
    # AUTHOR_EMAIL: '<boolean>' # Optional
    # FILES: '<boolean>' # Optional
    # PR_TITLE: '<boolean>' # Optional
    # PR_BODY_AI_ATTRIBUTION: '<boolean>' # Optional
    # BITBUCKET_ACCESS_TOKEN: '<string>' # Optional
```

## Variables

| Variable | Usage |
| --- | --- |
| MESSAGE | Check the message of every commit the pull request adds. Default: `true`. |
| BRANCH | Check the name of the source branch. Default: `true`. |
| AUTHOR_NAME | Check the author name of every commit. Default: `false`. |
| AUTHOR_EMAIL | Check the author email of every commit. Default: `false`. |
| FILES | Check the files every commit changes against the `[files]` rules. Default: `false`. |
| PR_TITLE | Check the pull request title against the commit message rules. Needs `BITBUCKET_ACCESS_TOKEN`. Default: `false`. |
| PR_BODY_AI_ATTRIBUTION | Check the pull request description against the AI attribution rules. Needs `BITBUCKET_ACCESS_TOKEN`. Default: `false`. |
| BITBUCKET_ACCESS_TOKEN | An access token with the **Pull requests: Read** scope. Bitbucket does not pass a pull request's title or description to the step, so the pipe reads them from the Bitbucket API. Only needed for `PR_TITLE` and `PR_BODY_AI_ATTRIBUTION`. |

## Details

In a pull request pipeline the pipe checks the source branch once and every commit the pull request adds, one by one, oldest first. Each check prints its own result, and the step fails when any of them fails.

- The rules come from `cchk.toml` or `commit-check.toml`, at the root of your repository or in `.github/`. Without one, Commit Check's defaults apply: [Conventional Commits](https://www.conventionalcommits.org/) messages and [Conventional Branch](https://conventionalbranch.org/) names. See the [configuration reference](https://commit-check.com/configuration/).
- A setting can also come from a `CCHK_` variable, such as `CCHK_SUBJECT_MAX_LENGTH: '72'`, passed under `variables` like any other.
- Bitbucket merges the destination branch into the pull request before the step runs. The checks stop at `BITBUCKET_COMMIT`, the pull request's own last commit, so commits that only came in with that merge are not checked.
- With a clone that ends inside the pull request the step fails and says so, rather than pass with commits unchecked. `clone: depth: full` avoids it.
- Outside a pull request pipeline, such as a `branches` pipeline, the pipe checks the branch and the last commit only.
- Editing a pull request's title or description does not start a pipeline. Run the step again after an edit.

The pipe runs `commit-check-ci` from the [commit-check](https://pypi.org/project/commit-check/) package of the same version, and shows the same output as the CLI.

## Prerequisites

None for the commit and branch checks.

For `PR_TITLE` and `PR_BODY_AI_ATTRIBUTION`, create a [repository access token](https://support.atlassian.com/bitbucket-cloud/docs/repository-access-tokens/) with the **Pull requests: Read** scope and store it as a secured [repository variable](https://support.atlassian.com/bitbucket-cloud/docs/variables-and-secrets/) named `BITBUCKET_ACCESS_TOKEN`.

## Examples

Basic example. Check the branch name and every commit message in each pull request:

```yaml
pipelines:
  pull-requests:
    '**':
      - step:
          name: Commit Check
          clone:
            depth: full
          script:
            - pipe: commit-check/commit-check:2.25.0
```

Advanced example. Also check the commit author emails, the pull request title and its AI attribution:

```yaml
pipelines:
  pull-requests:
    '**':
      - step:
          name: Commit Check
          clone:
            depth: full
          script:
            - pipe: commit-check/commit-check:2.25.0
              variables:
                AUTHOR_EMAIL: 'true'
                PR_TITLE: 'true'
                PR_BODY_AI_ATTRIBUTION: 'true'
                BITBUCKET_ACCESS_TOKEN: $BITBUCKET_ACCESS_TOKEN
```

Leave out the branch check and override one rule without a `cchk.toml`:

```yaml
            - pipe: commit-check/commit-check:2.25.0
              variables:
                BRANCH: 'false'
                CCHK_SUBJECT_MAX_LENGTH: '72'
```

## Support

If you'd like help with this pipe, or you have an issue or feature request, [open an issue](https://github.com/commit-check/commit-check/issues) or ask in [GitHub Discussions](https://github.com/commit-check/commit-check/discussions).

If you're reporting an issue, please include:

- the version of the pipe
- the relevant logs and error messages
- steps to reproduce

## License

MIT. The source is in [commit-check/commit-check](https://github.com/commit-check/commit-check/tree/main/bitbucket-pipe) on GitHub; this repository is published from it on every release.
