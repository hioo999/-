#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_TARGETS = [
    ROOT / "README.md",
    ROOT / "deploy",
    ROOT / "docs",
    ROOT / "agent-modules",
    ROOT / "packages",
    ROOT / "apps" / "agent-console" / "README.md",
    ROOT / "apps" / "platform-console" / "README.md",
]

SCANNED_SUFFIXES = {".example", ".json", ".md", ".txt", ".yaml", ".yml"}
IGNORED_DIRS = {
    ".git",
    ".pytest_cache",
    ".venv-agent-api",
    "__pycache__",
    "data",
    "diagnostics",
    "dist",
    "node_modules",
}

SECRET_ASSIGNMENT_RE = re.compile(r"^\s*(?:-\s*)?(?P<key>[A-Z0-9_]*(?:PASSWORD|SECRET|TOKEN|API_KEY|PRIVATE_KEY)[A-Z0-9_]*)\s*[:=]\s*(?P<value>[^\s#]+)", re.I)
DATABASE_URL_RE = re.compile(r"(?:postgresql|postgres|mysql|mongodb)://[^\s:@]+:(?P<password>[^@\s]+)@", re.I)

PATTERN_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("private key block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("OpenAI-style API key", re.compile(r"\bsk-[A-Za-z0-9][A-Za-z0-9_-]{16,}\b")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("personal macOS path", re.compile(r"/Users/(?!shared(?:/|\b)|Shared(?:/|\b))[A-Za-z0-9._-]+/[^\s'\")]+")),
    ("personal Windows path", re.compile(r"[A-Za-z]:\\\\Users\\\\[^\\\s]+\\\\[^\s'\")]+")),
    ("example person name", re.compile(r"张三|李四|王五|赵六")),
    ("seeded sensitive case text", re.compile(r"Secret Case Name|secret-contract|乙方已经付款|乙方是否付款")),
]

SAFE_VALUE_PREFIXES = ("replace-with-", "${", "$", "<")
SAFE_LITERAL_VALUES = {"", "true", "false", "none", "null", "info", "debug", "warning", "error"}


@dataclass(frozen=True)
class Finding:
    path: Path
    line: int
    rule: str
    snippet: str


def repo_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def is_scannable(path: Path) -> bool:
    if path.name.startswith(".") and path.name != ".env.example":
        return False
    if path.suffix in SCANNED_SUFFIXES:
        return True
    return path.name.endswith(".example")


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
            if candidate.is_file() and is_scannable(candidate):
                files.append(candidate)
    return sorted(set(files))


def redact(snippet: str) -> str:
    snippet = snippet.strip()
    if len(snippet) <= 120:
        return snippet
    return snippet[:117] + "..."


def is_safe_secret_value(value: str) -> bool:
    cleaned = value.strip().strip('"\'')
    lowered = cleaned.lower()
    url_match = DATABASE_URL_RE.search(cleaned)
    if url_match:
        return is_safe_secret_value(url_match.group("password"))
    return lowered in SAFE_LITERAL_VALUES or cleaned.startswith(SAFE_VALUE_PREFIXES)


def scan_text(path: Path, text: str) -> list[Finding]:
    findings: list[Finding] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for rule, pattern in PATTERN_RULES:
            if pattern.search(line):
                findings.append(Finding(path, line_number, rule, redact(line)))

        for match in SECRET_ASSIGNMENT_RE.finditer(line):
            value = match.group("value")
            if not is_safe_secret_value(value):
                findings.append(Finding(path, line_number, "concrete secret assignment", redact(line)))

        for match in DATABASE_URL_RE.finditer(line):
            password = match.group("password")
            if not is_safe_secret_value(password):
                findings.append(Finding(path, line_number, "database URL contains concrete password", redact(line)))
    return findings


def scan_files(files: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in files:
        try:
            text = path.read_text("utf-8")
        except UnicodeDecodeError:
            findings.append(Finding(path, 0, "non-utf8 delivery artifact", "file is not UTF-8 text"))
            continue
        findings.extend(scan_text(path, text))
    return findings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scan delivery artifacts for high-confidence local data and secret leaks.")
    parser.add_argument("--path", action="append", type=Path, help="File or directory to scan. Defaults to delivery docs and deploy artifacts.")
    parser.add_argument("--list-files", action="store_true", help="Print scanned files before reporting findings.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    targets = args.path if args.path else DEFAULT_TARGETS
    files = iter_files(targets)
    if args.list_files:
        for path in files:
            print(repo_path(path))

    findings = scan_files(files)
    if findings:
        print("delivery artifact scan failed:", file=sys.stderr)
        for finding in findings:
            location = repo_path(finding.path)
            if finding.line:
                location = f"{location}:{finding.line}"
            print(f"- {location}: {finding.rule}: {finding.snippet}", file=sys.stderr)
        return 1

    print(f"delivery artifact scan passed ({len(files)} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
