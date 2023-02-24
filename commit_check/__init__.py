"""The commit-check package's base module."""

RED = '\033[0;31m'
GREEN = "\033[32m"
YELLOW = '\033[93m'
RESET_COLOR = '\033[0m'

PASS = 0
FAIL = 1

"""
Use default config if .commit-check.yml not exist.
"""
DEFAULT_CONFIG = {
    'checks': [
        {
            'check': 'message',
            'regex': r'^(build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test){1}(\([\w\-\.]+\))?(!)?: ([\w ])+([\s\S]*)|(Merge).*|(fixup!.*)',
            'error': 'The commit message should be structured as follows:\n\n'
            '<type>[optional scope]: <description>\n'
            '[optional body]\n'
            '[optional footer(s)]\n\n'
            'More details please refer to https://www.conventionalcommits.org',
            'suggest': 'please check your commit message whether matches above regex'
        },
        {
            'check': 'branch',
            'regex': r'^(bugfix|feature|release|hotfix|task)\/.+|(master)|(main)|(HEAD)|(PR-.+)',
            'error': 'Branches must begin with these types: bugfix/ feature/ release/ hotfix/ task/',
            'suggest': 'run command `git checkout -b type/branch_name`',
        },
        {
            'check': 'author_name',
            'regex': r'^[A-Za-z ,.\'-]+$|.*(\[bot])',
            'error': 'The committer name seems invalid',
            'suggest': 'run command `git config user.name "Your Name"`',
        },
        {
            'check': 'author_email',
            'regex': r'^\S+@\S+\.\S+$',
            'error': 'The committer\'s email seems invalid',
            'suggest': 'run command `git config user.email yourname@example.com`',
        },
    ],
}


"""
Overwrite DEFAULT_CONFIG if `.commit-check.yml` exist.
"""

CONFIG_FILE = '.commit-check.yml'
