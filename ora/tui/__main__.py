"""Entry point for python -m ora."""

import argparse
import sys

from ora.app import OrAApp


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ora",
        description="OrA — Autonomous AI Command Center TUI"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="OrA 0.1.0"
    )
    
    # Parse args - if --help or --version is passed, argparse handles it and exits
    args = parser.parse_args()
    
    # If we get here, no special args were passed, so launch the TUI
    app = OrAApp()
    app.run()


if __name__ == "__main__":
    main()
