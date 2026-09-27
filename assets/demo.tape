# demo.tape — regenerate with `vhs assets/demo.tape` from the repository root.
#
# Needs vhs (https://github.com/charmbracelet/vhs) and commit-check on PATH.
#
# The hidden block below records inside a throwaway repository, so running this
# never leaves stray branches behind in the repository you invoke it from.

Output assets/demo.gif

Set Shell "zsh"

Set FontSize 16
# The longest line a failure prints is the CC001 suggestion, at 131 columns.
# This width measures 132 columns (checked with `tput cols` in the recorder,
# not calculated — the glyph advance is 10.26px, not the 9.6px you get from
# assuming 0.6em). Narrower breaks that line, and the URL above it, mid-word.
Set Width 1400
Set Height 600
# The palette of commit-check.com's terminal demos (docs/stylesheets/landing.css:
# .cc-term and the .cc-t-* colors), so the README and the site show one
# terminal. commit-check prints in bright red, green and yellow; the prompt
# below is cyan.
Set Theme { "name": "Commit Check", "background": "#0f1d28", "foreground": "#d6e1e8", "cursor": "#2c9ccd", "selection": "#22323f", "black": "#13212c", "red": "#ff7a6e", "green": "#4fc98b", "yellow": "#f2b866", "blue": "#2c9ccd", "magenta": "#c3a6f0", "cyan": "#7fc6e6", "white": "#d6e1e8", "brightBlack": "#8fa3b1", "brightRed": "#ff7a6e", "brightGreen": "#4fc98b", "brightYellow": "#f2b866", "brightBlue": "#7fc6e6", "brightMagenta": "#c3a6f0", "brightCyan": "#7fc6e6", "brightWhite": "#ffffff" }
Set Padding 24
Set TypingSpeed 50ms
Set PlaybackSpeed 1.0

Hide
# The identity matters: without it the initial commit fails, the repository is
# left with no commits at all, and every branch check then silently passes —
# which is exactly how this demo once recorded a failing branch as clean.
# ${DEMO_REPO:?} rather than a bare cd: when a command substitution produces
# nothing, zsh reads `cd $(...)` as plain `cd` and goes to $HOME — so a failing
# mktemp would have this git init a maintainer's home directory. The guard
# aborts the chain instead.
Type "DEMO_REPO=$(mktemp -d) && cd ${DEMO_REPO:?} && git init -q -b main . && git config user.name 'Dev' && git config user.email 'dev@example.com'"
Enter
Type "git commit -q --allow-empty -m 'feat: initial commit'"
Enter
Type "export PS1='%F{cyan}❯%f '"
Enter
Type "clear"
Enter
Sleep 2s

# --- A commit message that does not follow Conventional Commits ---
# Typed while hidden, so the recording opens on the rejection rather than on
# an empty prompt: the first frame is all a reader sees when the GIF is paused
# (GitHub pauses animated images for readers who ask for reduced motion) or
# has not finished loading.
Type "echo 'add user login' | commit-check -m"
Enter
Sleep 2s
Show
Sleep 4s

# --- The same message, fixed. A passing check prints nothing and exits 0, so
#     the demo reports the result rather than showing an empty line. ---
Type "echo 'feat: add user login' | commit-check -m && echo 'passed'"
Enter
Sleep 3s

Hide
Type "clear"
Enter
Show

# --- A branch name that does not follow Conventional Branch ---
Type "git switch -c user-login"
Enter
Sleep 1500ms
Type "commit-check -b"
Enter
Sleep 4s

# --- The same branch, fixed ---
Type "git switch -c feature/user-login"
Enter
Sleep 1500ms
Type "commit-check -b && echo 'passed'"
Enter
Sleep 3s

Hide
# Leave no throwaway repository behind. The same guard applies: an unset or
# empty DEMO_REPO aborts rather than handing rm -rf a bare path.
Type "cd / && rm -rf ${DEMO_REPO:?}"
Enter
Show
