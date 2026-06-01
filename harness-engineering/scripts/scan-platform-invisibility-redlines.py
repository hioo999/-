#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_TARGETS = [
    ROOT / "docs" / "platform-invisibility-report.json",
    ROOT / "docs" / "delivery-acceptance-report.json",
    ROOT / "docs" / "delivery-bundle-manifest.json",
]

SCANNED_SUFFIXES = {".json", ".md", ".txt", ".yaml", ".yml", ".log"}
IGNORED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    ".venv-agent-api",
    "__pycache__",
    "data",
    "diagnostics",
    "dist",
    "node_modules",
}

FORBIDDEN_JSON_KEYS = {
    "answer",
    "api_key",
    "case_name",
    "case_no",
    "case_title",
    "chunk_text",
    "database_password",
    "db_password",
    "document_text",
    "embedding",
    "file_name",
    "file_path",
    "model_api_key",
    "password",
    "prompt",
    "question",
    "raw_text",
    "text_content",
    "vector",
}

SECRET_ASSIGNMENT_RE = re.compile(
    r"^\s*(?:-\s*)?(?P<key>[A-Z0-9_]*(?:PASSWORD|SECRET|TOKEN|API_KEY|PRIVATE_KEY)[A-Z0-9_]*)\s*[:=]\s*(?P<value>[^\s#]+)",
    re.I,
)
DATABASE_URL_RE = re.compile(r"(?:postgresql|postgres|mysql|mongodb)://[^\s:@]+:(?P<password>[^@\s]+)@", re.I)

VALUE_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("private key block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("OpenAI-style API key", re.compile(r"\bsk-[A-Za-z0-9][A-Za-z0-9_-]{16,}\b")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("personal macOS path", re.compile(r"/Users/(?!shared(?:/|\b)|Shared(?:/|\b))[A-Za-z0-9._-]+/[^\s'\")]+")),
    ("personal Windows path", re.compile(r"[A-Za-z]:\\\\Users\\\\[^\\\s]+\\\\[^\s'\")]+")),
    ("seeded sensitive case text", re.compile(r"Secret Case Name|secret-contract|乙方已经付款|乙方是否付款")),
    ("example real-person marker", re.compile(r"张三|李四|王五|赵六")),
]

SAFE_VALUE_PREFIXES = ("replace-with-", "${", "$", "<")
SAFE_LITERAL_VALUES = {"", "true", "false", "none", "null", "info", "debug", "warning", "error"}


@dataclass(frozen=True)
class Finding:
    path: Path
    location: str
    rule: str
    snippet: str


def repo_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def is_scannable(path: Path) -> bool:
    return path.is_file() and path.suffix in SCANNED_SUFFIXES


def iter_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if not resolved.exists():
            continue
        if resolved.is_file():
            if is_scannable(resolved):
                files.append(resolved)
            continue
        for candidate in resolved.rglob("*"):
            if any(part in IGNORED_DIRS for part in candidate.parts):
                continue
            if is_scannable(candidate):
                files.append(candidate)
    return sorted(set(files))


def redact(snippet: str) -> str:
    cleaned = snippet.strip()
    if len(cleaned) <= 140:
        return cleaned
    return cleaned[:137] + "..."


def is_safe_secret_value(value: str) -> bool:
    cleaned = value.strip().strip('"\'')
    lowered = cleaned.lower()
    url_match = DATABASE_URL_RE.search(cleaned)
    if url_match:
        return is_safe_secret_value(url_match.group("password"))
    return lowered in SAFE_LITERAL_VALUES or cleaned.startswith(SAFE_VALUE_PREFIXES)


def scan_string_value(path: Path, location: str, value: str) -> list[Finding]:
    findings: list[Finding] = []
    for rule, pattern in VALUE_RULES:
        if pattern.search(value):
            findings.append(Finding(path, location, rule, redact(value)))
    return findings


def scan_json_node(path: Path, node: Any, location: str = "$") -> list[Finding]:
    findings: list[Finding] = []
    if isinstance(node, dict):
        for key, value in node.items():
            current = f"{location}.{key}"
            if key in FORBIDDEN_JSON_KEYS:
                findings.append(Finding(path, current, "forbidden business-data key", key))
            findings.extend(scan_json_node(path, value, current))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            findings.extend(scan_json_node(path, value, f"{location}[{index}]"))
    elif isinstance(node, str):
        findings.extend(scan_string_value(path, location, node))
    return findings


def scan_text(path: Path, text: str, *, strict_text_keys: bool) -> list[Finding]:
    findings: list[Finding] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        location = f"line {line_number}"
        findings.extend(scan_string_value(path, location, line))

        for match in SECRET_ASSIGNMENT_RE.finditer(line):
            value = match.group("value")
            if not is_safe_secret_value(value):
                findings.append(Finding(path, location, "concrete secret assignment", redact(line)))

        for match in DATABASE_URL_RE.finditer(line):
            password = match.group("password")
            if not is_safe_secret_value(password):
                findings.append(Finding(path, location, "database URL contains concrete password", redact(line)))

        if strict_text_keys:
            for key in FORBIDDEN_JSON_KEYS:
                if re.search(rf"\b{re.escape(key)}\b\s*[:=]", line):
                    findings.append(Finding(path, location, "forbidden business-data text key", redact(line)))
    return findings


def scan_file(path: Path, *, strict_text_keys: bool) -> list[Finding]:
    try:
        text = path.read_text("utf-8")
    except UnicodeDecodeError:
        return [Finding(path, "file", "non-utf8 redline artifact", "file is not UTF-8 text")]

    if path.suffix == ".json":
        try:
            return scan_json_node(path, json.loads(text))
        except json.JSONDecodeError as exc:
            return [Finding(path, f"line {exc.lineno}", "invalid JSON artifact", exc.msg)]
    return scan_text(path, text, strict_text_keys=strict_text_keys)


def scan_files(files: list[Path], *, strict_text_keys: bool) -> list[Finding]:
    findings: list[Finding] = []
    for path in files:
        findings.extend(scan_file(path, strict_text_keys=strict_text_keys))
    return findings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scan platform-invisibility and delivery artifacts for business-data redlines.")
    parser.add_argument("--path", action="append", type=Path, help="File or directory to scan. Defaults to generated acceptance artifacts under docs/.")
    parser.add_argument("--strict-text-keys", action="store_true", help="Also reject forbidden key-like labels in text files. Use for exported artifacts, not explanatory docs.")
    parser.add_argument("--list-files", action="store_true", help="Print scanned files before reporting findings.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    targets = args.path if args.path else DEFAULT_TARGETS
    files = iter_files(targets)
    if args.list_files:
        for path in files:
            print(repo_path(path))

    findings = scan_files(files, strict_text_keys=args.strict_text_keys)
    if findings:
        print("platform invisibility redline scan failed:", file=sys.stderr)
        for finding in findings:
            print(f"- {repo_path(finding.path)}:{finding.location}: {finding.rule}: {finding.snippet}", file=sys.stderr)
        return 1

    print(f"platform invisibility redline scan passed ({len(files)} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
