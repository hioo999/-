#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import io
import json
import sys
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECK_SCRIPT = ROOT / "scripts" / "check-delivery-package.py"


def load_delivery_checker():
    spec = importlib.util.spec_from_file_location("delivery_package_checker", CHECK_SCRIPT)
    if not spec or not spec.loader:
        raise RuntimeError(f"cannot load delivery checker: {CHECK_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def output_is_under_root(output: Path, root: Path) -> bool:
    try:
        output.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def checksum_path_for(output: Path) -> Path:
    return output.with_name(output.name + ".sha256")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_checksum(output: Path) -> Path:
    checksum_path = checksum_path_for(output)
    checksum_path.write_text(f"{sha256_file(output)}  {output.name}\n", "utf-8")
    return checksum_path


def manifest_payload(checker, manifest) -> dict[str, object]:
    return {
        "schema_version": "m21-delivery-package-archive-v1",
        "generated_at": 0,
        "root": str(manifest.root),
        "included_count": len(manifest.included),
        "excluded_count": manifest.excluded_count,
        "included_files": [checker.repo_path(path, manifest.root) for path in manifest.included],
        "excluded_rules": {
            "dir_names": sorted(checker.EXCLUDED_DIR_NAMES),
            "dir_suffixes": sorted(checker.EXCLUDED_DIR_SUFFIXES),
            "file_names": sorted(checker.EXCLUDED_FILE_NAMES),
            "file_suffixes": sorted(checker.EXCLUDED_SUFFIXES),
            "sensitive_included_suffixes": sorted(checker.SENSITIVE_INCLUDED_SUFFIXES),
        },
    }


def add_json(tar: tarfile.TarFile, arcname: str, payload: dict[str, object]) -> None:
    data = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    info = tarfile.TarInfo(arcname)
    info.size = len(data)
    info.mtime = 0
    info.mode = 0o644
    tar.addfile(info, io.BytesIO(data))


def add_file(tar: tarfile.TarFile, path: Path, arcname: str) -> None:
    data = path.read_bytes()
    info = tarfile.TarInfo(arcname)
    info.size = len(data)
    info.mtime = 0
    info.mode = 0o755 if path.stat().st_mode & 0o111 else 0o644
    tar.addfile(info, io.BytesIO(data))


def export_archive(root: Path, output: Path, include: list[str], prefix: str, allow_output_under_root: bool) -> tuple[int, int]:
    checker = load_delivery_checker()
    root = root.resolve()
    output = output.resolve()
    if output_is_under_root(output, root) and not allow_output_under_root:
        raise ValueError("output path must be outside the project root; use --allow-output-under-root only for tests")

    manifest = checker.build_manifest(root, include)
    errors = checker.validate_manifest(manifest)
    if errors:
        raise ValueError("delivery package boundary failed: " + "; ".join(errors))
    if not manifest.included:
        raise ValueError("delivery package would be empty")

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode="w") as tar:
                payload = manifest_payload(checker, manifest)
                add_json(tar, f"{prefix}/DELIVERY-MANIFEST.json", payload)
                for path in manifest.included:
                    arcname = f"{prefix}/{checker.repo_path(path, root)}"
                    add_file(tar, path, arcname)
    write_checksum(output)
    return len(manifest.included), manifest.excluded_count


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export a reproducible delivery archive from the validated package manifest.")
    parser.add_argument("--root", type=Path, default=ROOT, help="Project root to package")
    parser.add_argument("--include", action="append", help="Top-level file or directory to include. Defaults to checker allowlist.")
    parser.add_argument("--output", type=Path, required=True, help="Output .tar.gz path outside the project root")
    parser.add_argument("--prefix", default="harness-engineering", help="Archive top-level directory name")
    parser.add_argument("--allow-output-under-root", action="store_true", help="Allow output under root for isolated tests only")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    checker = load_delivery_checker()
    include = args.include or checker.DEFAULT_INCLUDE
    try:
        included_count, excluded_count = export_archive(
            root=args.root,
            output=args.output,
            include=include,
            prefix=args.prefix.strip("/") or "harness-engineering",
            allow_output_under_root=args.allow_output_under_root,
        )
    except Exception as exc:
        print(f"delivery package export failed: {exc}", file=sys.stderr)
        return 1

    print(f"delivery package exported: {args.output} ({included_count} included, {excluded_count} excluded)")
    print(f"delivery package checksum: {checksum_path_for(args.output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
