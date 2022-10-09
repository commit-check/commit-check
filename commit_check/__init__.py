"""The commit-check package's base module."""

VERSION = '0.1.0'
RED = '\033[0;31m'
YELLOW = '\033[93m'
RESET_COLOR = '\033[0m'

# BANNED_KEYWORDS = ['TO' + 'DO', 'X' + 'XX', 'W' + 'IP']
"""
Use default config if .commit-check.yml not exist.
"""
DEFAULT_CONFIG = {
    'checks': [
        {
            'check': 'message',
            'regex': r'^(build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test){1}(\\([\\w\\-\\.]+\\))?(!)?: ([\\w ])+([\\s\\S]*)',
            'error': 'The commit message should be structured as follows:\n\n'
            '<type>[optional scope]: <description>\n'
            '[optional body]\n'
            '[optional footer(s)]\n\n'
            'More details please refer to https://www.conventionalcommits.org',
        },
        {
            'check': 'branch',
            'regex': r'^(bugfix|feature|release|hotfix|task)\/.+|(master)|(main)|',
            'error': 'Branches must begin with these types: bugfix/ feature/ release/ hotfix/ task/',
        },
        {
            'check': 'email',
            'regex': r'/^\S+@\S+\.\S+$/',
            'error': 'The email address seems invalid',
        },
    ],
}


"""
Overwrite default config if .commit-check.yml exist.
"""

CONFIG_FILE = '.commit-check.yml'
