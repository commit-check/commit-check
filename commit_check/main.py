from __future__ import annotations

import argparse
import sys
from typing import Sequence

import commit_check.constants as C


def main(argv: Sequence[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    parser = argparse.ArgumentParser(prog='commit-check')

    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {C.VERSION}',
    )

    args = parser.parse_args(argv)

    return args.version


if __name__ == '__main__':
    raise SystemExit(main())
