# demo.tape — Generate demo.gif with: brew install vhs && vhs docs/demo.tape

Output demo.gif

Set Shell "zsh"

Set FontSize 16
Set Width 1000
Set Height 550
Set Theme "Dracula"
Set Padding 24
Set TypingSpeed 50ms
Set PlaybackSpeed 1.0

# --- Scene 1: Invalid commit message ---
Type "echo 'add user login' | commit-check -m"
Enter
Sleep 2s

# --- Scene 2: Valid commit message ---
Type "echo 'feat: add user login' | commit-check -m"
Enter
Sleep 2s

# --- Scene 4: Invalid branch name ---
Type "git checkout -b user-login"
Enter
Sleep 2s
Type "commit-check -b"
Enter
Sleep 2s

# --- Scene 5: Valid branch name ---
Type "git checkout -b feature/user-login"
Enter
Sleep 2s
Type "commit-check -b"
Enter
Sleep 2s
