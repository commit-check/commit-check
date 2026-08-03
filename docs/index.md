---
title: Commit Check
description: Enforce commit message, branch naming, author and signoff standards across your CLI, pre-commit hooks, CI, and AI agents.
hide:
  - navigation
  - toc
---

<div class="cc-hero" markdown>

# Clean commits. Clear standards.

Commit Check enforces the rules your Git history already depends on — commit
messages, branch names, committer identity, signoff — from one config, in every
place your team writes code.

[Get started :octicons-arrow-right-24:](getting-started/quickstart.md){ .md-button .md-button--primary }
[Browse the rules](rules.md){ .md-button }

</div>

---

## One config, enforced everywhere

Write the policy once. The same rules run on a developer's laptop, in CI, and in
whatever your AI agent is committing on your behalf.

=== "Command line"

    ```console
    $ commit-check --message --branch
    CC003 subject_imperative check failed ==> docs: revamped the profile
    Commit message should use imperative mood (e.g., 'fix bug' not 'fixed bug')
    Suggest: Change the first verb to imperative form
    Docs: https://docs.commit-check.com/rules/#cc003
    ```

=== "pre-commit"

    ```yaml title=".pre-commit-config.yaml"
    repos:
      - repo: https://github.com/commit-check/commit-check
        rev: v2.11.0
        hooks:
          - id: check-message
          - id: check-branch
          - id: check-author-email
    ```

=== "GitHub Actions"

    ```yaml title=".github/workflows/commit-check.yml"
    - uses: commit-check/commit-check-action@v1
      with:
        message: true
        branch: true
        pr-comments: ${{ github.event_name == 'pull_request' }}
    ```

=== "AI agents"

    ```json title="MCP server"
    {
      "mcpServers": {
        "commit-check": { "command": "commit-check-mcp" }
      }
    }
    ```

## What it checks

<div class="grid cards" markdown>

-   :material-message-text-outline:{ .lg .middle } __Commit messages__

    ---

    Conventional Commits by default, or your own pattern. Subject length, mood,
    capitalisation, required body, forbidden merge/fixup/WIP commits.

    [:octicons-arrow-right-24: CC001–CC013](rules.md#commit-message-rules)

-   :material-source-branch:{ .lg .middle } __Branch names__

    ---

    Conventional Branch naming, plus rebase checks that catch a branch drifting
    behind its target before CI wastes a run on stale code.

    [:octicons-arrow-right-24: CC201–CC202](rules.md#branch-rules)

-   :material-account-check-outline:{ .lg .middle } __Committer identity__

    ---

    Catch commits authored by `ec2-user` on a build box, or require everyone to
    contribute from a company address.

    [:octicons-arrow-right-24: CC101–CC102](rules.md#author-rules)

-   :material-file-sign:{ .lg .middle } __Signoff and DCO__

    ---

    Require the `Signed-off-by` trailer locally, so contributors find out before
    CI rejects the pull request.

    [:octicons-arrow-right-24: Signoff guide](guides/signoff.md)

-   :material-robot-outline:{ .lg .middle } __AI attribution__

    ---

    Whatever your project has decided about AI-assisted commits, enforce it
    mechanically instead of relitigating it in review.

    [:octicons-arrow-right-24: AI attribution guide](guides/ai-attribution.md)

-   :material-office-building-outline:{ .lg .middle } __Org-wide policy__

    ---

    Inherit a base config from a shared repository, then let each project
    override only what it needs.

    [:octicons-arrow-right-24: Organization guide](guides/organization.md)

</div>

## Built to be trusted

<div class="grid cards" markdown>

-   :material-shield-check:{ .lg .middle } __SLSA Level 3__

    ---

    Build provenance with artifact attestation you can verify before
    installing.

-   :material-tag-outline:{ .lg .middle } __Stable rule IDs__

    ---

    Every diagnostic carries an ID like `CC003` that never changes, so you can
    cite it in review, suppress it, or feed it to tooling.

-   :material-source-commit:{ .lg .middle } __Used in production__

    ---

    Running at Apache, Texas Instruments, Mila, and
    [many more](https://github.com/commit-check/commit-check-action/network/dependents).

</div>

## Ready in two minutes

```console
$ pip install commit-check
$ commit-check --message --branch
```

No configuration file needed to start — sensible defaults apply immediately, and
you tighten them when you are ready.

[Install :octicons-arrow-right-24:](getting-started/installation.md){ .md-button .md-button--primary }
[Why Commit Check?](getting-started/why.md){ .md-button }
