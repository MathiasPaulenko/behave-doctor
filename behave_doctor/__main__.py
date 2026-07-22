"""Entry point for ``python -m behave_doctor``."""

from __future__ import annotations

import sys

from behave_doctor.cli import main

if __name__ == "__main__":
    sys.exit(main())
