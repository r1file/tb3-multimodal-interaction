#!/usr/bin/env python3
"""Fail on repository content that must not be published."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


MAX_BYTES = 10 * 1024 * 1024
FORBIDDEN_SUFFIXES = {
    ".bin", ".csv", ".gguf", ".jsonl", ".key", ".mkv", ".mp3",
    ".mp4", ".onnx", ".p12", ".pem", ".pt", ".safetensors", ".wav",
}
SECRET_PATTERNS = {
    "private-key": re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
    "github-token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    "aws-access-key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
}
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def repository_files() -> list[Path]:
    raw = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"]
    )
    return [Path(value.decode()) for value in raw.split(b"\0") if value]


def main() -> int:
    failures: list[tuple[Path, str]] = []
    for path in repository_files():
        if not path.is_file():
            continue
        if path.name == ".env":
            failures.append((path, "private environment file"))
        if path.parent == Path(".") and (
            path.name == "host-manifest.toml"
            or (path.name.startswith("host-manifest.") and path.suffix == ".toml")
        ):
            failures.append((path, "populated deployment manifest"))
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            failures.append((path, f"forbidden artifact suffix {path.suffix}"))
        if path.stat().st_size > MAX_BYTES:
            failures.append((path, f"file exceeds {MAX_BYTES} bytes"))
        data = path.read_bytes()
        if b"\0" in data:
            continue
        text = data.decode("utf-8", errors="ignore")
        for rule, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                failures.append((path, rule))
        if path.suffix.lower() == ".md":
            for target in MARKDOWN_LINK.findall(text):
                target = target.strip().split("#", 1)[0]
                if not target or "://" in target or target.startswith(("mailto:", "#")):
                    continue
                linked = (path.parent / target).resolve()
                if not linked.exists():
                    failures.append((path, f"broken local link {target}"))

    if failures:
        for path, rule in failures:
            print(f"FAIL {path}: {rule}")
        return 1
    print(f"REPOSITORY_AUDIT_PASS files={len(repository_files())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
