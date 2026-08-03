# Set an AI attribution policy

AI coding tools add trailers to commit messages identifying themselves. Whether
that is welcome, required, or unacceptable is a decision each project makes for
itself — and the industry has landed in different places:

- The **Linux kernel** added an `Assisted-by:` trailer, treating AI assistance
  as something to disclose.
- **Some projects disallow AI-assisted contributions outright**, usually over
  provenance and licensing.
- **Most projects have no stated position**, which means the question resurfaces
  in every code review.

Commit Check does not take a side. It gives you a way to enforce whichever
position your project has already taken, so it stops being relitigated.

## The default: no opinion

```toml
[commit]
ai_attribution = "ignore"   # the default
```

[CC013](../rules.md#cc013) is off. Commits carrying AI trailers pass, and so do
commits without them.

## Forbidding AI-attributed commits

```toml title="cchk.toml"
[commit]
ai_attribution = "forbid"
```

Commits carrying a recognised AI signature now fail:

```text
CC013 ai_attribution check failed ==> feat: add caching layer
AI attribution policy violation
Suggest: This project forbids AI-assisted commits. Remove AI trailers and re-commit.
Docs: https://docs.commit-check.com/rules/#cc013
```

### What counts as a signature

Trailers and co-author lines naming Claude Code, GitHub Copilot, Codex, Gemini,
Cursor, Devin, Aider, Windsurf and Tabby, plus generic AI model patterns.

!!! warning "This checks disclosure, not authorship"

    CC013 reads commit metadata. It detects a commit that *says* it was
    AI-assisted; it cannot detect one that was AI-assisted and did not say so.

    Set against a policy of "no AI contributions", it is an honesty check on
    contributors who are already following the rules — not an enforcement
    mechanism against those who aren't. Be clear with yourself about which of
    those you are buying.

## Exempting automation

Bots that legitimately carry AI trailers can be excluded:

```toml title="cchk.toml"
[commit]
ai_attribution = "forbid"
ignore_authors = ["dependabot[bot]", "renovate[bot]"]
```

## Documenting the decision

Whichever way you go, the config file is not where contributors look. State the
policy where they will see it — `CONTRIBUTING.md`, the pull request template —
and let Commit Check be the mechanism rather than the announcement.

Enforcing an undocumented policy produces a confusing failure for somebody
acting in good faith.
