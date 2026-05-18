from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pydantic import ValidationError

from app.processor import ProcessingMode, process_incident_file_with_mode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_parser = subparsers.add_parser("ingest", help="Parse and triage one markdown incident report.")
    ingest_parser.add_argument("file", type=Path)
    ingest_parser.add_argument(
        "--mode",
        choices=[mode.value for mode in ProcessingMode],
        default=ProcessingMode.DETERMINISTIC.value,
        help="Processing mode to use. Defaults to deterministic.",
    )

    args = parser.parse_args(argv)

    if args.command == "ingest":
        try:
            result = process_incident_file_with_mode(args.file, args.mode)
        except (FileNotFoundError, RuntimeError, ValueError, ValidationError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

        print(result.model_dump_json(indent=2))
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
