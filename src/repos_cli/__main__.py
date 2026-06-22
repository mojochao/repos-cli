"""Enable ``python -m repos_cli``."""

import sys

from repos_cli.cli import main

if __name__ == "__main__":
    sys.exit(main())
