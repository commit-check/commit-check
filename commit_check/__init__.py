"""The commit-check package's base module."""

VERSION = '0.1.0'
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
            'check': 'commit_message',
            'regex': r'^(build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test){1}(\([\w\-\.]+\))?(!)?: ([\w ])+([\s\S]*)',
            'error': 'The commit message should be structured as follows:\n\n'
            '<type>[optional scope]: <description>\n'
            '[optional body]\n'
            '[optional footer(s)]\n\n'
            'More details please refer to https://www.conventionalcommits.org',
            'suggest': 'git commit --amend'
        },
        {
            'check': 'branch_name',
            'regex': r'^(bugfix|feature|release|hotfix|task)\/.+|(master)|(main)|(HEAD)|(PR-.+)',
            'error': 'Branches must begin with these types: bugfix/ feature/ release/ hotfix/ task/',
            'suggest': 'git checkout -b new_branch_name',
        },
        {
            'check': 'author_email',
            'regex': r'/^\S+@\S+\.\S+$/',
            'error': 'The email address seems invalid',
        },
    ],
}


"""
Overwrite DEFAULT_CONFIG if `.commit-check.yml` exist.
"""

CONFIG_FILE = '.commit-check.yml'
