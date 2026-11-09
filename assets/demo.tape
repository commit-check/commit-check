# demo.tape — regenerate with `vhs assets/demo.tape` from the repository root.
#
# Needs vhs (https://github.com/charmbracelet/vhs), zsh, and commit-check on
# PATH (`pip install -e .` records the output of this checkout).
#
# Everything runs inside a throwaway repository made in the hidden block
# below, so recording never touches the repository you run it from.

Output assets/demo.gif

Set Shell "zsh"
Set FontFamily "JetBrains Mono"
Set FontSize 16
# Wide enough for the longest line the demo prints (the CC013 suggestion)
# without wrapping.
Set Width 1320
Set Height 700
# The palette of commit-check.com's terminal demos (docs/stylesheets/landing.css:
# .cc-term and the .cc-t-* colors), so the README and the site show one
# terminal.
Set Theme { "name": "Commit Check", "background": "#0f1d28", "foreground": "#d6e1e8", "cursor": "#2c9ccd", "selection": "#22323f", "black": "#13212c", "red": "#ff7a6e", "green": "#4fc98b", "yellow": "#f2b866", "blue": "#2c9ccd", "magenta": "#c3a6f0", "cyan": "#7fc6e6", "white": "#d6e1e8", "brightBlack": "#8fa3b1", "brightRed": "#ff7a6e", "brightGreen": "#4fc98b", "brightYellow": "#f2b866", "brightBlue": "#7fc6e6", "brightMagenta": "#c3a6f0", "brightCyan": "#7fc6e6", "brightWhite": "#ffffff" }
Set WindowBar Colorful
Set BorderRadius 10
Set Margin 20
Set MarginFill "#0b1620"
Set Padding 20
Set TypingSpeed 45ms
Set PlaybackSpeed 1.0

Hide
# ${DEMO_REPO:?} rather than a bare cd: when a command substitution produces
# nothing, zsh reads `cd $(...)` as plain `cd` and goes to $HOME, so a failing
# mktemp would set up the demo in a maintainer's home directory. The guard
# aborts the chain instead.
Type "DEMO_REPO=$(mktemp -d) && cd ${DEMO_REPO:?} && git init -q -b main . && git config user.name 'Dev' && git config user.email 'dev@example.com'"
Enter
# The project's policy: Conventional Commits with a short list of types (which
# also keeps the suggestion line short), no AI attribution, Conventional Branch.
Type `printf '[commit]\nallow_commit_types = ["feat", "fix", "docs", "chore"]\nai_attribution = "forbid"\n\n[branch]\nconventional_branch = true\n' > cchk.toml`
Enter
# The commit-msg hook a pre-commit install would add: check the message and
# the branch, and correct what has a mechanical fix.
Type `printf '#!/bin/sh\nexec commit-check --fix --message "$1" --branch\n' > .git/hooks/commit-msg && chmod +x .git/hooks/commit-msg`
Enter
# The initial commit is made before the hook can see it, on main.
Type "git add cchk.toml && git commit -q --no-verify -m 'chore: add commit-check config' && git switch -q -c login-page && touch login.html && git add login.html"
Enter
Type "export PS1='%F{cyan}❯%f '"
Enter
Type "clear"
Enter
Sleep 1s

# --- The policy, then a commit that breaks all three parts of it ---
# Typed while hidden, so the recording opens on the rejection rather than on
# an empty prompt: the first frame is all a reader sees when the GIF is paused
# (GitHub pauses animated images for readers who ask for reduced motion) or
# has not finished loading.
Type "cat cchk.toml"
Enter
Type `git commit -m "Add login page" -m "Co-authored-by: Claude <noreply@anthropic.com>"`
Enter
Sleep 2s
Show
Sleep 8s

Hide
Type "clear"
Enter
Show

# --- A Conventional Branch name, and a message with a mechanical slip: the
#     hook corrects it and the commit goes through ---
Type "git switch -c feature/login-page"
Enter
Sleep 1200ms
Type `git commit -m "Feat add login page"`
Enter
Sleep 2500ms
Type "git log --oneline -1"
Enter
Sleep 4s

Hide
# Leave no throwaway repository behind. The same guard applies: an unset or
# empty DEMO_REPO aborts rather than handing rm -rf a bare path.
Type "cd / && rm -rf ${DEMO_REPO:?}"
Enter
Show
