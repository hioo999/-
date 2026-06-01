#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


FORBIDDEN_KEYS = {
    "answer",
    "api_key",
    "case_name",
    "case_title",
    "chunk_text",
    "document_text",
    "file_name",
    "file_path",
    "prompt",
    "question",
    "test_output",
    "test_outputs",
}
FORBIDDEN_VALUE_PATTERNS = [
    ("OpenAI-style API key", re.compile(r"\bsk-[A-Za-z0-9][A-Za-z0-9_-]{16,}\b")),
    ("personal macOS path", re.compile(r"/Users/(?!shared(?:/|\b)|Shared(?:/|\b))[A-Za-z0-9._-]+/[^\s'\"]+")),
    ("seeded case text", re.compile(r"Secret Case Name|secret-contract|张三|李四|乙方已经付款|乙方是否付款")),
]


def scan_node(node, path: str, errors: list[str]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            current = f"{path}.{key}" if path else key
            if key in FORBIDDEN_KEYS:
                errors.append(f"forbidden report key: {current}")
            scan_node(value, current, errors)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            scan_node(value, f"{path}[{index}]", errors)
    elif isinstance(node, str):
        for name, pattern in FORBIDDEN_VALUE_PATTERNS:
            if pattern.search(node):
                errors.append(f"forbidden report value ({name}) at {path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scan delivery acceptance report for forbidden business-data keys and sensitive values.")
    parser.add_argument("--report", type=Path, required=True, help="delivery-acceptance-report.json path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = json.loads(args.report.read_text("utf-8"))
    except Exception as exc:
        print(f"delivery acceptance report scan failed: {exc}", file=sys.stderr)
        return 1
    errors: list[str] = []
    scan_node(report, "", errors)
    if errors:
        print("delivery acceptance report scan failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"delivery acceptance report scan passed: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
