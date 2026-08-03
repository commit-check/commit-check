# Why Commit Check

## The problem

Git history is a database that every team writes to and almost nobody validates.

The cost shows up later, and indirectly. Release notes get written by hand
because commit subjects cannot be grouped. `git bisect` walks through merge
commits that record nothing but a sync. A commit is attributed to `ec2-user`
because a build box had no `user.name`. A contribution has to be rejected
months after the fact because it never carried a `Signed-off-by` trailer.

None of these are caught by a linter, a type checker, or a test suite. They are
all caught by review, which means they are caught inconsistently, by whoever
happens to be looking, and only after the work is done.

## The approach

Commit Check treats commit metadata the way linters treat code: a policy written
down once, enforced identically everywhere, with a stable identifier for every
diagnostic so that findings can be discussed, suppressed, and tracked.

**One config.** A single `cchk.toml` drives the CLI, the pre-commit hook, the
GitHub Action, and the MCP server. There is no second place where the rules can
disagree with themselves.

**Fails where it is cheap.** The same check that runs in CI runs in your
`commit-msg` hook. Finding out that a subject is malformed takes a second
locally and a full CI cycle plus a force-push remotely.

**Stable rule IDs.** Every rule has an ID like [CC003](../rules.md#cc003) that
never changes once released. You can cite it in a review comment, link to its
documentation, and eventually suppress it per-rule.

**Explains itself.** A failure names the rule, quotes the offending value, says
how to fix it, and links to the reasoning.

## Where it fits

Commit Check is deliberately narrow: it validates *metadata*, not code. It is a
lightweight, open alternative to
[GitHub Enterprise metadata restrictions](https://docs.github.com/en/enterprise-server@3.11/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#metadata-restrictions)
and Bitbucket's paid
[Yet Another Commit Checker](https://marketplace.atlassian.com/apps/1211854/yet-another-commit-checker),
without requiring a particular forge or an enterprise plan.

If you already run `ruff`, `eslint`, or `golangci-lint` on your source, Commit
Check is the equivalent for the commits that carry it.

## What it is not

- **Not a code linter.** It never reads your source files.
- **Not a replacement for review.** It enforces the mechanical rules so review
  can spend its attention on the change itself.
- **Not opinionated by default.** Most rules are off until you turn them on. See
  the [rules reference](../rules.md) for what applies out of the box.
