"""Check branch naming convention.
"""
import re

from commit_check.util import get_branch_name


def check_branch(config):
    checks = config["checks"]
    for check in checks:
        if check['check'] == 'branch':
            branch_name = get_branch_name()
            retval = re.match(check['regex'], branch_name)
            if not retval:
                raise ("error failed")
        else:
            pass
