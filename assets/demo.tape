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
Set Theme "Dracula"
Set Padding 24
Set TypingSpeed 50ms
Set PlaybackSpeed 1.0

Hide
# The identity matters: without it the initial commit fails, the repository is
# left with no commits at all, and every branch check then silently passes —
# which is exactly how this demo once recorded a failing branch as clean.
Type "cd $(mktemp -d) && git init -q -b main . && git config user.name 'Dev' && git config user.email 'dev@example.com'"
Enter
Type "git commit -q --allow-empty -m 'feat: initial commit'"
Enter
Type "export PS1='%F{cyan}❯%f '"
Enter
Type "clear"
Enter
Sleep 2s
Show

# --- A commit message that does not follow Conventional Commits ---
Type "echo 'add user login' | commit-check -m"
Enter
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
