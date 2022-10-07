"""The commit-check package's base module."""

VERSION = '0.1.0'
RED = '\033[41m'  # Background red.
YELLOW = '\033[93m'
RESET_COLOR = '\033[0m'

# BANNED_KEYWORDS = ['TO' + 'DO', 'X' + 'XX', 'W' + 'IP']

DEFAULT_CONFIG = {
    'checks': [
        {
            'check': 'message', 
            'regex': '^(build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test){1}(\\([\\w\\-\\.]+\\))?(!)?: ([\\w ])+([\\s\\S]*)', 
            'error': '<type>: <description>\nFor Example. feat: Support for async execution\nBetween type and description MUST have a colon and space.\nMore please refer to https://www.conventionalcommits.org '
        }, 
        {
            'check': 'branch', 
            'regex': '^(bugfix|feature|release|hotfix|task)\\/[\\w-.]+|(master)|(main)', 
            'error': 'Branches must begin with these types: bugfix/ feature/ release/ hotfix/ task/'
        }
    ]
}


CONFIG_FILE = '.commit-check.yml'
