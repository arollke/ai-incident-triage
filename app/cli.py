from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pydantic import ValidationError

from app.processor import process_incident_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_parser = subparsers.add_parser("ingest", help="Parse and triage one markdown incident report.")
    ingest_parser.add_argument("file", type=Path)

    args = parser.parse_args(argv)

    if args.command == "ingest":
        try:
            result = process_incident_file(args.file)
        except (FileNotFoundError, ValueError, ValidationError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

        print(result.model_dump_json(indent=2))
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
