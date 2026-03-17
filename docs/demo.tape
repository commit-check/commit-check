# demo.tape — Generate demo.gif with: brew install vhs && vhs demo.tape

Output demo.gif

Set Shell "fish"
Set FontSize 14
Set Width 900
Set Height 500
Set Theme "Dracula"
Set Padding 20
Set TypingSpeed 60ms
Set PlaybackSpeed 1.0

# --- Scene 1: Show the tool ---
Type "commit-check --version"
Enter
Sleep 1s

# --- Scene 2: Invalid commit message (triggers error) ---
Type "echo 'add user login' | commit-check -m"
Enter
Sleep 2s

# --- Scene 3: Valid commit message ---
Type "echo 'feat: add user login' | commit-check -m"
Enter
Sleep 1.5s

# --- Scene 4: Invalid branch name check ---
Type "git checkout -b user-login -q 2>/dev/null; commit-check -b"
Enter
Sleep 2s

# --- Scene 5: Valid branch name ---
Type "git checkout -b feature/user-login -q 2>/dev/null; commit-check -b"
Enter
Sleep 2s

# --- End ---
Type "For more details, please checkout https://commit-check.github.io"
Sleep 2s
