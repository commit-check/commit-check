# Contributing

Thank you for investing your time in contributing to our project! We welcome feedback, bug reports, and pull requests!

## New contributor guide

Our development branch is `main`. When submitting pull requests, please adhere to the following guidelines:

* Add tests for any new features and bug fixes.
* Put a reasonable amount of comments into the code.
* Fork [commit-check](https://github.com/commit-check/commit-check) on your GitHub user account.
* Create a branch from `main`, make your changes on the new branch, and then create a PR against the `main` branch of the commit-check repository.
* Separate unrelated changes into multiple pull requests for better review and management.

By contributing any code or documentation to this repository (by raising pull requests or otherwise), you explicitly agree to the [License Agreement](https://github.com/commit-check/commit-check/blob/main/LICENSE).

We appreciate your contributions to make Commit Check even better!

## Development

### Debug commit-check pre-commit hook

```bash
pre-commit try-repo  ./../commit-check/ check-message --verbose --hook-stage prepare-commit-msg --commit-msg-filename .git/COMMIT_EDITMSG
```

### Debug commit-check wheel package

```bash
python3 -m pip install --upgrade pip
pip install -e ./../commit-check/
commit-check -m
```

### Test commit-check pre-commit hook on GitHub

```yaml
-   repo: https://github.com/commit-check/commit-check
    rev: the tag or revision # update it to test commit hash
    hooks:
    -   id: check-message
    -   id: check-branch
    -   id: check-author-email
```
