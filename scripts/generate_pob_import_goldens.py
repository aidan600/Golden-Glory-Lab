"""Regenerate committed deterministic PoB importer golden JSON.

Inputs: permanent synthetic XML fixtures under fixtures/pob/proof.
Outputs: named neutral-contract JSON under fixtures/pob/golden.
Network use: none.
Limit: these outputs prove importer regression behavior, not game mechanics.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from golden_glory_lab.pob_import import deterministic_json_bytes, importPobRawXml  # noqa: E402


def main() -> int:
    source = ROOT / "fixtures" / "pob" / "proof" / "comprehensive.xml"
    target = ROOT / "fixtures" / "pob" / "golden" / "comprehensive.raw.neutral-v1.json"
    result = importPobRawXml(source.read_bytes().decode("utf-8", errors="strict"))
    if result["status"] != "success":
        raise RuntimeError(f"golden source failed import: {result['failure']}")
    output = deterministic_json_bytes(result)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(output)
    print(f"generated {target.relative_to(ROOT)}")
    print(f"bytes={len(output)} sha256={hashlib.sha256(output).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
