#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INCLUDE = [
    "README.md",
    "agent-modules",
    "apps",
    "deploy",
    "docs",
    "packages",
    "scripts",
    "services",
    "tests",
]

EXCLUDED_DIR_NAMES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    ".venv-agent-api",
    "__pycache__",
    "build",
    "data",
    "diagnostics",
    "dist",
    "htmlcov",
    "node_modules",
}

EXCLUDED_DIR_SUFFIXES = (".egg-info", ".dist-info")

EXCLUDED_FILE_NAMES = {
    ".DS_Store",
    ".env",
    "env.agent",
    "env.platform",
    "env.local",
}

EXCLUDED_SUFFIXES = {
    ".db",
    ".log",
    ".pyc",
    ".pyo",
    ".gz",
    ".sha256",
    ".sqlite",
    ".sqlite3",
    ".tar",
    ".tgz",
    ".zip",
}

SENSITIVE_INCLUDED_SUFFIXES = {".env", ".key", ".pem", ".p12", ".pfx"}


@dataclass(frozen=True)
class Manifest:
    root: Path
    included: list[Path]
    excluded_count: int


def repo_path(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def is_excluded_dir(path: Path) -> bool:
    return path.name in EXCLUDED_DIR_NAMES or path.name.endswith(EXCLUDED_DIR_SUFFIXES)


def is_excluded_file(path: Path) -> bool:
    return path.name in EXCLUDED_FILE_NAMES or path.suffix in EXCLUDED_SUFFIXES


def is_sensitive_included_file(path: Path) -> bool:
    if path.name.endswith(".example"):
        return False
    return path.suffix in SENSITIVE_INCLUDED_SUFFIXES


def iter_candidate_files(root: Path, include: list[str]) -> tuple[list[Path], int]:
    included: list[Path] = []
    excluded_count = 0
    for entry in include:
        base = (root / entry).resolve()
        if not base.exists():
            continue
        if base.is_file():
            if is_excluded_file(base) or is_sensitive_included_file(base):
                excluded_count += 1
            else:
                included.append(base)
            continue

        for candidate in base.rglob("*"):
            if any(is_excluded_dir(Path(part)) for part in candidate.relative_to(root).parts[:-1]):
                excluded_count += 1
                continue
            if candidate.is_dir():
                if is_excluded_dir(candidate):
                    excluded_count += 1
                continue
            if is_excluded_file(candidate) or is_sensitive_included_file(candidate):
                excluded_count += 1
                continue
            included.append(candidate.resolve())
    return sorted(set(included)), excluded_count


def build_manifest(root: Path, include: list[str]) -> Manifest:
    included, excluded_count = iter_candidate_files(root, include)
    return Manifest(root=root, included=included, excluded_count=excluded_count)


def validate_manifest(manifest: Manifest) -> list[str]:
    errors: list[str] = []
    for path in manifest.included:
        relative_parts = path.relative_to(manifest.root).parts
        if any(part in EXCLUDED_DIR_NAMES or part.endswith(EXCLUDED_DIR_SUFFIXES) for part in relative_parts):
            errors.append(f"forbidden directory included: {repo_path(path, manifest.root)}")
        if is_excluded_file(path):
            errors.append(f"forbidden file included: {repo_path(path, manifest.root)}")
        if is_sensitive_included_file(path):
            errors.append(f"sensitive file included: {repo_path(path, manifest.root)}")
    return errors


def write_manifest(manifest: Manifest, output: Path) -> None:
    payload = {
        "schema_version": "m21-delivery-package-manifest-v1",
        "root": str(manifest.root),
        "included_count": len(manifest.included),
        "excluded_count": manifest.excluded_count,
        "included_files": [repo_path(path, manifest.root) for path in manifest.included],
        "excluded_rules": {
            "dir_names": sorted(EXCLUDED_DIR_NAMES),
            "dir_suffixes": sorted(EXCLUDED_DIR_SUFFIXES),
            "file_names": sorted(EXCLUDED_FILE_NAMES),
            "file_suffixes": sorted(EXCLUDED_SUFFIXES),
            "sensitive_included_suffixes": sorted(SENSITIVE_INCLUDED_SUFFIXES),
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", "utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate the pre-delivery package boundary and optional file manifest.")
    parser.add_argument("--root", type=Path, default=ROOT, help="Project root to package")
    parser.add_argument("--include", action="append", help="Top-level file or directory to include. Defaults to source/docs/test/deploy roots.")
    parser.add_argument("--output", type=Path, help="Optional JSON manifest output path")
    parser.add_argument("--list", action="store_true", help="Print included files")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    include = args.include or DEFAULT_INCLUDE
    manifest = build_manifest(root, include)
    errors = validate_manifest(manifest)

    if args.output:
        write_manifest(manifest, args.output)
    if args.list:
        for path in manifest.included:
            print(repo_path(path, root))

    if errors:
        print("delivery package boundary check failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"delivery package boundary check passed ({len(manifest.included)} included, {manifest.excluded_count} excluded)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
