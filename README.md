# Commit Check

Check commit message formatting, branch naming, referencing Jira tickets, and more

## About

commit-check is a tool designed for teams.

Its main purpose is to standardize the format of commit messages and branch naming.

The reason behind it is that it is easier to read and enforces writing descriptive commits. Besides that, having conventional commits and branch naming makes it possible to parse them and use them for something else, like:

* triggering specific types of builds
* generating automatically the version or a changelog
* easy to identify branch according to the branch type

## Installation

Global installation

```bash
sudo pip3 install -U commit-check
```

User installation

```bash
pip install -U commit-check
```

On macOS, it can also be installed via homebrew:

TODO

```
brew install commit-check
```

## Usage

### Add .commit-check.yml

Create a config file `.commit-check.yml` under your repository, e.g. [.commit-check.yml](.commit-check.yml)

The content of the config file should be in the following format.

```yaml
checks:
  - check: message
    regex: '^(build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test){1}(\([\w\-\.]+\))?(!)?: ([\w ])+([\s\S]*)'
    error: "<type>: <description>

    For Example. feat: Support new feature xxxx

    Between type and description MUST have a colon and space.

    More please refer to https://www.conventionalcommits.org"
  - check: branch
    regex: '^(bugfix|feature|release|hotfix|task)\/.+|(master)|(main)'
    error: "Branches must begin with these types: bugfix/ feature/ release/ hotfix/ task/"
```

### Use default configuration

If you do not set .commit-check.yml, `commit-check` will use the default configuration. i.e. the commit message will follow the rules of [conventional commits](https://www.conventionalcommits.org/en/v1.0.0/#summary), but will not check branch naming.

If you want to skip the `commit-check`, you can use the option `-n` or `--no-verify`.

### Integrating with pre-commit

```yaml
-   repo: https://github.com/commit-check/commit-check
    rev: v1.0.0
    hooks:
    -   id: check-message
    -   id: check-branch
```

### Integrating with GitHub Action

```yaml
name: commit-check

on: pull_request

jobs:
  cpp-linter:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: commit-check/commit-check@v1
        id: linter
        with:
          message: file
          branch: file

      - name: Fail fast?!
        if: steps.commit-check.outputs.checks-failed > 0
        run: echo "commit-check failed!"
        # for actual deployment
        # run: exit 1
```

### Integrating with git hooks

TODO

## Example

### Check commit message failed

```
Commit rejected by Commit-Check.

  (c).-.(c)    (c).-.(c)    (c).-.(c)    (c).-.(c)    (c).-.(c)
   / ._. \      / ._. \      / ._. \      / ._. \      / ._. \
 __\( C )/__  __\( H )/__  __\( E )/__  __\( C )/__  __\( K )/__
(_.-/'-'\-._)(_.-/'-'\-._)(_.-/'-'\-._)(_.-/'-'\-._)(_.-/'-'\-._)
   || E ||      || R ||      || R ||      || O ||      || R ||
 _.' `-' '._  _.' `-' '._  _.' `-' '._  _.' `-' '._  _.' `-' '.
(.-./`-'\.-.)(.-./`-`\.-.)(.-./`-`\.-.)(.-./`-'\.-.)(.-./`-`\.-.)
 `-'     `-'  `-'     `-'  `-'     `-'  `-'     `-'  `-'     `-'

Commit rejected.

Invalid commit message.

message does't match regex: ^(build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test){1}(\([\w\-\.]+\))?(!)?: ([\w ])+([\s\S]*)

<type>: <description>
For Example. feat: Support new feature xxxx
Between type and description MUST have a colon and space.
More please refer to https://www.conventionalcommits.or
```

### Check branch naming failed

```
Commit rejected by Commit-Check.

  (c).-.(c)    (c).-.(c)    (c).-.(c)    (c).-.(c)    (c).-.(c)
   / ._. \      / ._. \      / ._. \      / ._. \      / ._. \
 __\( C )/__  __\( H )/__  __\( E )/__  __\( C )/__  __\( K )/__
(_.-/'-'\-._)(_.-/'-'\-._)(_.-/'-'\-._)(_.-/'-'\-._)(_.-/'-'\-._)
   || E ||      || R ||      || R ||      || O ||      || R ||
 _.' `-' '._  _.' `-' '._  _.' `-' '._  _.' `-' '._  _.' `-' '.
(.-./`-'\.-.)(.-./`-`\.-.)(.-./`-`\.-.)(.-./`-'\.-.)(.-./`-`\.-.)
 `-'     `-'  `-'     `-'  `-'     `-'  `-'     `-'  `-'     `-'

Commit rejected.

Invalid branch name.

branch does't match regex: ^(bugfix|feature|release|hotfix|task)\/.+|(master)|(main)

Branches must begin with these types: bugfix/ feature/ release/ hotfix/ task/
```

## Have question or feedback?

To provide feedback (requesting a feature or reporting a bug) please post to [issues](https://github.com/commit-check/commit-check/issues).

## License

The scripts and documentation in this project are released under the [MIT License](LICENSE)
