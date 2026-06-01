#!/usr/bin/env python3
"""Export the Agent FastAPI OpenAPI schema without starting a server."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
AGENT_API_DIR = ROOT / "services" / "agent-api"
if str(AGENT_API_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_API_DIR))

from app.main import FastApiDependencyError, create_app  # noqa: E402


class OpenApiStore:
    """Placeholder store used only to build route metadata."""


def build_schema() -> dict[str, Any]:
    app = create_app(OpenApiStore())
    return app.openapi()


def main() -> int:
    parser = argparse.ArgumentParser(description="Export Agent API OpenAPI schema")
    parser.add_argument("--output", "-o", type=Path, help="Optional output JSON file")
    args = parser.parse_args()

    try:
        schema = build_schema()
    except FastApiDependencyError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    content = json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content + "\n", encoding="utf-8")
    else:
        print(content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
