"""Command-line entry point for building or searching the guidance index."""

import argparse
import json

from .store import build_index, retrieve


def main() -> None:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("build", help="Rebuild Chroma from top-level .txt/.md files in documents/")
    search = commands.add_parser("search", help="Search indexed guidance")
    search.add_argument("query")
    args = parser.parse_args()
    try:
        result = build_index() if args.command == "build" else retrieve(args.query)
    except (ValueError, FileNotFoundError, ModuleNotFoundError) as error:
        parser.exit(1, f"Cannot {args.command}: {error}\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
