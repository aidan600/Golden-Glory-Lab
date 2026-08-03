"""Developer-facing CLI over the production PoB importer entry points."""

from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path
from typing import Sequence

from .importer import importPobRawXml, importPobShareCode
from .serializer import deterministic_json


def _read_utf8_exact(path: str) -> str:
    return Path(path).read_bytes().decode("utf-8", errors="strict")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Emit deterministic Golden Glory Lab PoB neutral JSON."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--raw-xml", metavar="FILE", help="Import a UTF-8 raw XML file.")
    source.add_argument(
        "--share-code-file", metavar="FILE", help="Import a UTF-8 PoB share-code file."
    )
    source.add_argument("--share-code", metavar="CODE", help="Import a supplied PoB share code.")
    parser.add_argument(
        "--producing-pob-version",
        help="Optional caller-supplied producing PoB version; never inferred from targetVersion.",
    )
    parser.add_argument(
        "--debug", action="store_true", help="Print a traceback for unexpected tool failures."
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    options = {"producingPobVersion": args.producing_pob_version}
    try:
        if args.raw_xml:
            result = importPobRawXml(_read_utf8_exact(args.raw_xml), options)
        elif args.share_code_file:
            result = importPobShareCode(_read_utf8_exact(args.share_code_file), options)
        else:
            result = importPobShareCode(args.share_code, options)
        sys.stdout.buffer.write(deterministic_json(result).encode("utf-8"))
        return 0 if result["status"] == "success" else 2
    except Exception as error:  # pragma: no cover - explicit developer debug boundary
        if args.debug:
            traceback.print_exc()
        else:
            sys.stderr.write(
                f'{{"code":"CLI_UNEXPECTED_FAILURE","message":{error!r}}}\n'
            )
        return 3


if __name__ == "__main__":
    raise SystemExit(main())

