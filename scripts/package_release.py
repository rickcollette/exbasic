#!/usr/bin/env python3
"""Validate and package one native exBASIC compiler build."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Iterable
import zipfile


ROOT = Path(__file__).resolve().parent.parent


class PackageError(RuntimeError):
    pass


def read_version(root: Path = ROOT) -> str:
    text = (root / "version.mk").read_text(encoding="utf-8")
    match = re.fullmatch(r"\s*VERSION\s*=\s*([^\s#]+)\s*", text)
    if not match:
        raise PackageError("version.mk must contain exactly one VERSION=<value> assignment")
    version = match.group(1)
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?", version):
        raise PackageError(f"VERSION is not semantic-version shaped: {version!r}")
    return version


def validate_compiler(compiler_dir: Path, version: str, platform_name: str) -> None:
    executable = compiler_dir / ("exbasic.exe" if platform_name == "windows" else "exbasic")
    required = [
        executable,
        compiler_dir / ("ca65.exe" if platform_name == "windows" else "ca65"),
        compiler_dir / ("ld65.exe" if platform_name == "windows" else "ld65"),
        compiler_dir / ("ar65.exe" if platform_name == "windows" else "ar65"),
        compiler_dir / ("atr.exe" if platform_name == "windows" else "atr"),
        compiler_dir / "exbasic.lib",
        compiler_dir / "exbasic-cart.lib",
        compiler_dir / "USAGE.md",
        compiler_dir / "THIRD_PARTY_LICENSES.md",
    ]
    missing = [path.name for path in required if not path.is_file()]
    if missing:
        raise PackageError(f"compiler build is incomplete; missing {', '.join(missing)}")

    completed = subprocess.run(
        [str(executable.resolve()), "-v"],
        cwd=compiler_dir,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if completed.returncode:
        raise PackageError(f"{executable.name} -v failed with exit code {completed.returncode}")
    if version not in completed.stdout:
        raise PackageError(f"{executable.name} reports the wrong version: {completed.stdout.strip()!r}")

    with tempfile.TemporaryDirectory(prefix="exbasic-package-smoke-") as temporary:
        temporary_path = Path(temporary)
        source = temporary_path / "smoke.bas"
        output = temporary_path / "smoke.xex"
        source.write_text('? "release smoke test"\n', encoding="ascii")
        smoke = subprocess.run(
            [str(executable.resolve()), "-o", str(output), str(source)],
            cwd=compiler_dir,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        if smoke.returncode or not output.is_file() or output.stat().st_size == 0:
            raise PackageError(
                f"{executable.name} package smoke test failed: "
                f"{smoke.stdout.strip() or f'exit code {smoke.returncode}'}"
            )


def create_zip(compiler_dir: Path, destination: Path, archive_root: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in sorted(compiler_dir.rglob("*")):
                if not path.is_file():
                    continue
                relative = path.relative_to(compiler_dir).as_posix()
                archive.write(path, f"{archive_root}/{relative}")
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", required=True, choices=("windows", "linux", "macos"))
    parser.add_argument("--arch", required=True, choices=("amd64", "arm64"))
    parser.add_argument("--compiler-dir", type=Path, default=ROOT / "build" / "compiler")
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        version = read_version()
        compiler_dir = args.compiler_dir.resolve()
        validate_compiler(compiler_dir, version, args.platform)
        archive_root = f"exbasic-{version}-{args.platform}-{args.arch}"
        create_zip(compiler_dir, args.output.resolve(), archive_root)
        print(f"Packaged {args.output}")
        return 0
    except (OSError, PackageError, zipfile.BadZipFile) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
