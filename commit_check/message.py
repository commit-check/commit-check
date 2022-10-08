import re
from commit_check.util import get_commit_message, error_tips


def check_message(config) -> bool:
    checks = config['checks']
    for check in checks:
        if check['check'] == 'message':
            messages = get_commit_message()
            for message in messages:
                result = re.match(check['regex'], message)
                if result is None:
                    error_tips('message', check['regex'], check['error'])
                    return False
    return True
