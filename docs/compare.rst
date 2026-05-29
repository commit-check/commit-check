commit-check vs commitlint vs GitHub Rulesets
================================================

Choosing the right tool depends on what you need to enforce, where you need to
enforce it, and your team's existing stack.  This page compares **commit-check**
with the two most common alternatives people ask about: `commitlint`_ and
`GitHub Rulesets`_.

.. _commitlint: https://commitlint.js.org/
.. _GitHub Rulesets: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets


TL;DR
-----

- **commitlint** is the standard choice for commit message linting.
  18.6k stars, 3k+ dependents on npm — it is the incumbent and does its one
  job well.

- **commit-check** is for teams that want a broader Git metadata policy layer:
  messages, branch names, author identity, sign-off trailers, force-push
  safety — in one versioned TOML file that works locally, in CI, and with
  AI toolchains.

- **GitHub Rulesets** are platform-native enforcement built into GitHub.
  commit-check complements them with portable, config-as-code, local-first
  validation that works **before** code reaches GitHub — in your editor, in
  pre-commit hooks, and in CI pipelines on any platform.


commit-check vs commitlint
--------------------------

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Feature
     - Commit Check
     - commitlint
   * - Conventional Commits enforcement
     - ✅ semantic-aware
     - ✅ semantic-aware
   * - Branch naming validation
     - ✅ Conventional Branch
     - ❌
   * - Force push blocking
     - ✅ pre-push hook
     - ❌
   * - Author name / email validation
     - ✅
     - ❌
   * - Signed-off-by trailer enforcement
     - ✅ built-in
     - Partial (community plugin)
   * - Bot / automation author bypass
     - ✅
     - ❌
   * - Zero-config defaults
     - ✅ works out of the box
     - ❌ requires config file
   * - Configuration format
     - TOML
     - JS / JSON / YAML / TS
   * - Organization-level shared config
     - ✅ ``inherit_from`` (github: or URL)
     - ✅ shareable npm config packages
   * - Runtime
     - **Python** (3.9+)
     - **Node.js** (≥22.12)
   * - Pre-commit / Git hook integration
     - ✅ first-class
     - ✅ via husky
   * - CI/CD integration
     - ✅ env vars + CLI args
     - ✅
   * - GitHub Actions
     - ✅ dedicated action
     - ✅ community actions
   * - Machine-readable JSON output
     - ✅ ``--format json``, Python API
     - ❌ (text formatters only)
   * - Python API (no subprocess)
     - ✅ ``commit_check.api``
     - ❌ (JavaScript API only)
   * - Open source
     - ✅ MIT
     - ✅ MIT


Which one should you use?
~~~~~~~~~~~~~~~~~~~~~~~~~

**Use commitlint if:**

- You **only** need commit message linting
- Your project already uses Node.js and npm
- You want the established ecosystem with thousands of existing integrations

**Use commit-check if:**

- You want to validate **branch names** too (Conventional Branch)
- You want **author / email / signoff** checks in the same tool
- You want **TOML** policy files that are easy to read and diff
- You want **Python-native** tooling (no Node.js dependency)
- You want **JSON output** for automation scripts or AI agents
- You want **zero-config defaults** — run ``commit-check --message`` and get sensible checks immediately
- You want **one shared policy** across many repositories via ``inherit_from``


commit-check vs GitHub Rulesets
--------------------------------

GitHub Rulesets are the native policy layer on GitHub.com.  They can:

- Require pull requests, status checks, and CODEOWNERS reviews
- Require signed commits
- Block force pushes
- Restrict commit metadata (author email patterns, commit message regex, **branch/tag name regex**)
- Apply at the **organization** or **enterprise** level
- Protect branches and tags with ``fnmatch`` patterns

These are powerful and complementary capabilities.  commit-check does **not**
compete with them — it operates at a different layer.

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Feature
     - Commit Check
     - GitHub Rulesets
   * - Conventional Commits enforcement
     - ✅ semantic-aware
     - Partial (regex only, no type/scope awareness)
   * - Branch naming convention validation
     - ✅ Conventional Branch (semantic)
     - ✅ regex patterns
   * - Author name / email validation
     - ✅
     - ✅ (email regex in push rulesets)
   * - Signed-off-by enforcement
     - ✅
     - ❌
   * - Force push blocking
     - ✅ local pre-push
     - ✅ server-side
   * - Require pull requests
     - ❌ (not its scope)
     - ✅
   * - Require status checks / CODEOWNERS
     - ❌ (not its scope)
     - ✅
   * - Require signed commits
     - ❌ (not its scope)
     - ✅
   * - Configuration format
     - **TOML** (versionable, diffable)
     - GitHub UI or REST API
   * - Works offline / locally
     - ✅
     - ❌
   * - Works in pre-commit hooks
     - ✅
     - ❌
   * - Works on any Git platform
     - ✅
     - ❌ (GitHub only)
   * - Instant feedback (before push)
     - ✅
     - ❌ (only on push)
   * - Free for all teams
     - ✅ MIT
     - Requires GitHub plan (Free/Team/Enterprise)


How they fit together
~~~~~~~~~~~~~~~~~~~~~

GitHub Rulesets are **platform-native enforcement**.  commit-check is
**portable, config-as-code, local-first**, and usable before code reaches
GitHub.

.. code-block:: text

    ┌─────────────────────────────────────────────┐
    │               Your Workflow                 │
    │                                             │
    │  [Editor] ──► [pre-commit] ──► [git push] ──► [GitHub] │
    │                │                              │         │
    │          commit-check                  GitHub Rulesets  │
    │          (local feedback)             (server gating)  │
    └─────────────────────────────────────────────┘

A recommended setup:

#. **commit-check** in pre-commit hooks gives developers instant feedback before
   they commit or push — catching malformed messages, non-standard branch names,
   and missing sign-offs at the desk.
#. **GitHub Rulesets** enforce platform-level requirements that only GitHub can
   provide — signed commits, required reviews, status checks.
#. Both can share the same policy intent: your ``cchk.toml`` defines what a
   valid commit looks like; Rulesets add a second layer of defense on the
   server.

This is not an either/or choice.  Many teams will use **both** — commit-check
for local and CI validation, GitHub Rulesets for repository-level gating.
