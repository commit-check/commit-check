"""Check branch naming convention.
"""
import re
from commit_check.util import get_branch_name, error_tips


def check_branch(config) -> bool:
    checks = config['checks']
    for check in checks:
        if check['check'] == 'branch':
            if check['regex'] == "":
                return True
            branch_name = get_branch_name()
            result = re.match(check['regex'], branch_name)
            if result is None:
                error_tips(check['check'], check['regex'], check['error'])
                return False
    return True
