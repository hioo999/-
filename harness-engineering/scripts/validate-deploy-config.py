#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ipaddress
import re
import sys
import urllib.parse
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

AGENT_REQUIRED_KEYS = {
    "AGENT_ADMIN_PASSWORD",
    "AGENT_SECRET_KEY",
    "AGENT_ALLOWED_DATA_ROOTS",
    "AGENT_FORBIDDEN_DATA_ROOTS",
    "AGENT_FORBIDDEN_PATH_PARTS",
    "AGENT_OCR_ALLOWED_COMMANDS",
    "AGENT_MODEL_REQUEST_TIMEOUT_SECONDS",
    "AGENT_QDRANT_URL",
    "AGENT_POSTGRES_PASSWORD",
    "AGENT_LOCAL_DATABASE_URL",
}

PLATFORM_REQUIRED_KEYS = {
    "PLATFORM_JWT_SECRET",
    "PLATFORM_LICENSE_SECRET",
    "PLATFORM_ALLOWED_HEALTH_FIELDS",
    "PLATFORM_POSTGRES_PASSWORD",
    "PLATFORM_DATABASE_URL",
}

AGENT_COMPOSE_REQUIRED_KEYS = {
    "AGENT_ADMIN_PASSWORD",
    "AGENT_SECRET_KEY",
    "AGENT_ALLOWED_DATA_ROOTS",
    "AGENT_FORBIDDEN_DATA_ROOTS",
    "AGENT_FORBIDDEN_PATH_PARTS",
}

PLATFORM_COMPOSE_REQUIRED_KEYS = {
    "PLATFORM_JWT_SECRET",
    "PLATFORM_LICENSE_SECRET",
    "PLATFORM_ALLOWED_HEALTH_FIELDS",
}

SENSITIVE_KEY_RE = re.compile(r"(PASSWORD|SECRET|TOKEN|API_KEY|PRIVATE_KEY|DATABASE_URL|REDIS_URL)", re.I)
WEAK_LITERAL_VALUES = {
    "admin",
    "password",
    "secret",
    "changeme",
    "change-me",
    "agent_password",
    "platform_password",
    "postgres_password",
    "test",
    "local",
}

PLATFORM_FORBIDDEN_TOKENS = {
    "agent-api",
    "agent_",
    "qdrant",
    "redis",
    "rag",
    "parser",
    "embedding",
    "worker",
    "model-proxy",
    "file-ingestion",
    "document-parser",
}


@dataclass(frozen=True)
class Finding:
    path: Path
    message: str


def repo_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(path.read_text("utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"{repo_path(path)}:{line_number}: invalid env line")
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            raise ValueError(f"{repo_path(path)}:{line_number}: invalid env key {key!r}")
        values[key] = strip_quotes(value)
    return values


def is_reference(value: str) -> bool:
    return "${" in value or value.startswith("$")


def is_placeholder(value: str) -> bool:
    normalized = value.strip().lower()
    return normalized.startswith("replace-with-") or normalized in {"<required>", "<secret>", "changeme"}


def password_from_url(value: str) -> str | None:
    if "://" not in value:
        return None
    parsed = urllib.parse.urlsplit(value)
    return parsed.password


def secret_values_to_check(key: str, value: str) -> list[str]:
    password = password_from_url(value)
    if password is not None:
        return [password]
    if "://" in value:
        return []
    return [value]


def validate_secret_value(path: Path, key: str, value: str, mode: str) -> list[Finding]:
    findings: list[Finding] = []
    if not SENSITIVE_KEY_RE.search(key) or not value:
        return findings

    for candidate in secret_values_to_check(key, value):
        candidate = candidate.strip()
        if not candidate:
            continue
        lowered = candidate.lower()
        if is_reference(candidate):
            continue
        if is_placeholder(candidate):
            if mode == "production":
                findings.append(Finding(path, f"{key} still uses placeholder value"))
            continue
        if lowered in WEAK_LITERAL_VALUES or "_password" in lowered or lowered.endswith("password"):
            findings.append(Finding(path, f"{key} contains weak plaintext secret value {candidate!r}"))
            continue
        if mode == "example":
            findings.append(Finding(path, f"{key} contains concrete secret material; use replace-with-* or variable references"))
        elif len(candidate) < 16:
            findings.append(Finding(path, f"{key} must be at least 16 characters in production mode"))
    return findings


def validate_required(path: Path, values: dict[str, str], required: set[str]) -> list[Finding]:
    findings: list[Finding] = []
    for key in sorted(required - values.keys()):
        findings.append(Finding(path, f"missing required key {key}"))
    for key in sorted(required & values.keys()):
        if not values[key].strip():
            findings.append(Finding(path, f"required key {key} must not be empty"))
    return findings


def hostname_is_local_private(hostname: str) -> bool:
    normalized = hostname.strip().lower().strip("[]")
    if normalized in {"localhost", "host.docker.internal"} or normalized.endswith(".local"):
        return True
    try:
        address = ipaddress.ip_address(normalized)
    except ValueError:
        return False
    return address.is_loopback or address.is_private or address.is_link_local


def validate_agent_urls(path: Path, values: dict[str, str]) -> list[Finding]:
    findings: list[Finding] = []
    for key in ("AGENT_PLATFORM_BASE_URL", "AGENT_QDRANT_URL"):
        value = values.get(key, "").strip()
        if not value:
            continue
        parsed = urllib.parse.urlsplit(value)
        if parsed.hostname and not hostname_is_local_private(parsed.hostname):
            findings.append(Finding(path, f"{key} must point to localhost, private IP, link-local, or .local host"))
    return findings


def parse_compose(path: Path) -> dict[str, dict[str, object]]:
    services: dict[str, dict[str, object]] = {}
    current_service: str | None = None
    current_section: str | None = None
    in_services = False

    for raw_line in path.read_text("utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        if indent == 0:
            in_services = stripped == "services:"
            current_service = None
            current_section = None
            continue
        if not in_services:
            continue
        if indent == 2 and stripped.endswith(":"):
            current_service = stripped[:-1]
            services[current_service] = {"environment": {}, "env_file": [], "raw": []}
            current_section = None
            continue
        if current_service is None:
            continue
        services[current_service]["raw"].append(stripped)
        if indent == 4 and stripped.endswith(":"):
            current_section = stripped[:-1]
            continue
        if indent == 4:
            current_section = None
        if current_section == "environment" and indent >= 6:
            if stripped.startswith("-"):
                key = stripped[1:].strip().split("=", 1)[0].strip()
                if key:
                    services[current_service]["environment"][key] = ""
            elif ":" in stripped:
                key, value = stripped.split(":", 1)
                services[current_service]["environment"][key.strip()] = strip_quotes(value.strip())
        elif current_section == "env_file" and indent >= 6:
            if stripped.startswith("-"):
                services[current_service]["env_file"].append(strip_quotes(stripped[1:].strip()))
    return services


def env_file_keys(compose_path: Path, env_file_entry: str) -> set[str]:
    env_path = (compose_path.parent / env_file_entry).resolve()
    if not env_path.exists():
        return set()
    return set(parse_env_file(env_path).keys())


def service_available_keys(compose_path: Path, service: dict[str, object]) -> set[str]:
    keys = set((service.get("environment") or {}).keys())
    for entry in service.get("env_file") or []:
        keys.update(env_file_keys(compose_path, str(entry)))
    return keys


def validate_compose(path: Path, mode: str, kind: str) -> list[Finding]:
    findings: list[Finding] = []
    services = parse_compose(path)
    if not services:
        return [Finding(path, "compose file has no services")]

    for service_name, service in services.items():
        environment = service.get("environment") or {}
        for key, value in environment.items():
            findings.extend(validate_secret_value(path, str(key), str(value), mode))

    if kind == "platform":
        raw_text = path.read_text("utf-8").lower()
        for token in sorted(PLATFORM_FORBIDDEN_TOKENS):
            if token in raw_text:
                findings.append(Finding(path, f"platform compose must not include Agent/data-plane token {token!r}"))
        platform_api = services.get("platform-api")
        if platform_api is None:
            findings.append(Finding(path, "missing platform-api service"))
        else:
            missing = PLATFORM_COMPOSE_REQUIRED_KEYS - service_available_keys(path, platform_api)
            for key in sorted(missing):
                findings.append(Finding(path, f"platform-api service does not receive required key {key}"))
    elif kind == "agent":
        for required_service in ("agent-api", "agent-api-fastapi", "redis", "qdrant"):
            if required_service not in services:
                findings.append(Finding(path, f"missing required Agent compose service {required_service}"))
        for service_name in ("agent-api", "agent-api-fastapi"):
            service = services.get(service_name)
            if service is None:
                continue
            missing = AGENT_COMPOSE_REQUIRED_KEYS - service_available_keys(path, service)
            for key in sorted(missing):
                findings.append(Finding(path, f"{service_name} service does not receive required key {key}"))
    else:
        raise ValueError(f"unknown compose kind: {kind}")
    return findings


def validate_env(path: Path, required: set[str], mode: str, kind: str) -> list[Finding]:
    values = parse_env_file(path)
    findings = validate_required(path, values, required)
    for key, value in values.items():
        findings.extend(validate_secret_value(path, key, value, mode))
    if kind == "agent":
        findings.extend(validate_agent_urls(path, values))
    return findings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate deploy env examples and Docker Compose security boundaries.")
    parser.add_argument("--mode", choices=("example", "production"), default="example")
    parser.add_argument("--agent-env", type=Path, default=ROOT / "deploy" / "env.agent.example")
    parser.add_argument("--platform-env", type=Path, default=ROOT / "deploy" / "env.platform.example")
    parser.add_argument("--agent-compose", type=Path, default=ROOT / "deploy" / "docker-compose.agent.yml")
    parser.add_argument("--platform-compose", type=Path, default=ROOT / "deploy" / "docker-compose.platform.yml")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        findings: list[Finding] = []
        findings.extend(validate_env(args.agent_env, AGENT_REQUIRED_KEYS, args.mode, "agent"))
        findings.extend(validate_env(args.platform_env, PLATFORM_REQUIRED_KEYS, args.mode, "platform"))
        findings.extend(validate_compose(args.agent_compose, args.mode, "agent"))
        findings.extend(validate_compose(args.platform_compose, args.mode, "platform"))
    except Exception as exc:  # pragma: no cover - keeps CLI failures actionable.
        print(f"deploy config validation failed: {exc}", file=sys.stderr)
        return 2

    if findings:
        print("deploy config validation failed:", file=sys.stderr)
        for finding in findings:
            print(f"- {repo_path(finding.path)}: {finding.message}", file=sys.stderr)
        return 1
    print(f"deploy config validation passed ({args.mode} mode)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
