#!/usr/bin/env python3
"""Build Windows, Linux, and macOS exBASIC release artifacts.

Windows is built locally. Linux and macOS are built on SSH hosts configured
in PRIVATE_DIR/.secrets as ``LINUX: ssh ...`` and ``MAC: ssh ...``. The
identity in PRIVATE_DIR/.privkey is always forced for those connections.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
from typing import BinaryIO, Iterable


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PRIVATE = ROOT / ".private"
DIST = ROOT / "DIST"

EXCLUDED_PREFIXES = (
    ".git",
    ".private",
    "DIST",
    "__pycache__",
    "build",
    "scripts/__pycache__",
    "third_party/exoperatingsystem/build",
)


class BuildError(RuntimeError):
    pass


def read_version() -> str:
    text = (ROOT / "version.mk").read_text(encoding="utf-8")
    match = re.fullmatch(r"\s*VERSION\s*=\s*([^\s#]+)\s*", text)
    if not match:
        raise BuildError("version.mk must contain exactly one VERSION=<value> assignment")
    version = match.group(1)
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?", version):
        raise BuildError(f"invalid VERSION value: {version!r}")
    return version


def read_connections(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise BuildError(f"missing SSH configuration: {path}")
    result: dict[str, str] = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise BuildError(f"{path}:{number}: expected LABEL: ssh-command")
        label, command = line.split(":", 1)
        label = label.strip().upper()
        command = command.strip()
        if not label or not command:
            raise BuildError(f"{path}:{number}: empty label or command")
        if label in result:
            raise BuildError(f"{path}:{number}: duplicate {label} entry")
        result[label] = command
    return result


def without_identity_options(arguments: list[str]) -> list[str]:
    result: list[str] = []
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        lowered = argument.lower()
        if argument == "-i":
            index += 2
            continue
        if argument.startswith("-i") and len(argument) > 2:
            index += 1
            continue
        if lowered == "-o" and index + 1 < len(arguments) and arguments[index + 1].lower().startswith("identityfile="):
            index += 2
            continue
        if lowered.startswith("-oidentityfile="):
            index += 1
            continue
        result.append(argument)
        index += 1
    return result


@contextmanager
def protected_private_key(source: Path) -> Iterable[Path]:
    if not source.is_file():
        raise BuildError(f"missing SSH private key: {source}")
    with tempfile.TemporaryDirectory(prefix="exbasic-ssh-key-") as temporary:
        protected = Path(temporary) / "id_release"
        shutil.copyfile(source, protected)
        if os.name == "nt":
            whoami = subprocess.run(["whoami"], text=True, capture_output=True, check=False)
            if whoami.returncode or not whoami.stdout.strip():
                raise BuildError("could not determine the Windows account for SSH key ACLs")
            acl = subprocess.run(
                ["icacls", str(protected), "/inheritance:r", "/grant:r", f"{whoami.stdout.strip()}:(R)"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            if acl.returncode:
                raise BuildError(f"could not protect the temporary SSH key: {acl.stderr.strip()}")
        else:
            protected.chmod(0o600)
        yield protected


def ssh_argv(command: str, key_file: Path) -> list[str]:
    if not key_file.is_file():
        raise BuildError(f"missing SSH private key: {key_file}")
    try:
        argv = shlex.split(command, posix=True)
    except ValueError as exc:
        raise BuildError(f"invalid SSH command syntax: {exc}") from exc
    if len(argv) < 2 or Path(argv[0]).name.lower() not in {"ssh", "ssh.exe"}:
        raise BuildError("each connection must be an ssh command ending in one destination")
    forbidden = {";", "&&", "||", "|", ">", "<"}
    if any(arg in forbidden for arg in argv):
        raise BuildError("shell operators are not allowed in SSH connection commands")
    return [
        argv[0],
        "-i",
        str(key_file.resolve()),
        "-o",
        "BatchMode=yes",
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        "StrictHostKeyChecking=accept-new",
        *without_identity_options(argv[1:]),
    ]


def is_excluded(relative: str) -> bool:
    relative = relative.replace("\\", "/").strip("/")
    return any(relative == prefix or relative.startswith(prefix + "/") for prefix in EXCLUDED_PREFIXES)


def create_source_archive(destination: Path) -> None:
    def archive_filter(info: tarfile.TarInfo) -> tarfile.TarInfo | None:
        relative = info.name.removeprefix("source/")
        if relative and is_excluded(relative):
            return None
        return info

    with tarfile.open(destination, "w:gz", compresslevel=6) as archive:
        archive.add(ROOT, arcname="source", recursive=True, filter=archive_filter)


def run_ssh(
    connection: list[str],
    remote_command: str,
    *,
    stdin: BinaryIO | None = None,
    stdout: BinaryIO | int | None = None,
    capture: bool = False,
) -> subprocess.CompletedProcess[bytes]:
    kwargs: dict[str, object] = {"cwd": ROOT, "check": False}
    if stdin is not None:
        kwargs["stdin"] = stdin
    if capture:
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.PIPE
    elif stdout is not None:
        kwargs["stdout"] = stdout
    completed = subprocess.run([*connection, remote_command], **kwargs)  # type: ignore[arg-type]
    if completed.returncode:
        raise BuildError(f"remote command failed with exit code {completed.returncode}")
    return completed


def validate_bundle_member(member: tarfile.TarInfo) -> None:
    path = PurePosixPath(member.name)
    if path.is_absolute() or ".." in path.parts:
        raise BuildError(f"unsafe path in artifact bundle: {member.name}")
    if member.issym() or member.islnk() or member.isdev():
        raise BuildError(f"unsupported entry in artifact bundle: {member.name}")


def is_macos_metadata(member: tarfile.TarInfo) -> bool:
    return any(part == "__MACOSX" or part.startswith("._") for part in PurePosixPath(member.name).parts)


def extract_bundle(bundle: Path, destination: Path) -> list[Path]:
    extracted: list[Path] = []
    with tarfile.open(bundle, "r:gz") as archive:
        members = archive.getmembers()
        for member in members:
            validate_bundle_member(member)
        members = [member for member in members if not is_macos_metadata(member)]
        archive.extractall(destination, members=members, filter="data")
        for member in members:
            if member.isfile():
                extracted.append(destination / PurePosixPath(member.name))
    return extracted


def local_windows_job(source_archive: Path, version: str) -> list[Path]:
    if os.name != "nt":
        raise BuildError("the Windows release lane must run on Windows")
    for command in ("make", "gcc", "g++", "go"):
        if shutil.which(command) is None:
            raise BuildError(f"missing Windows build prerequisite: {command}")

    print("[WINDOWS] building native amd64 release")
    with tempfile.TemporaryDirectory(prefix="exbasic-windows-build-") as temporary:
        temporary_path = Path(temporary)
        with tarfile.open(source_archive, "r:gz") as archive:
            archive.extractall(temporary_path, filter="data")
        source = temporary_path / "source"
        workers = min(os.cpu_count() or 2, 8)
        environment = os.environ.copy()
        git_sh = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Git" / "bin" / "sh.exe"
        if not git_sh.is_file():
            raise BuildError("Git for Windows sh.exe was not found")
        git_usr_bin = git_sh.parent.parent / "usr" / "bin"
        if not git_usr_bin.is_dir():
            raise BuildError("Git for Windows usr/bin directory was not found")
        environment["SHELL"] = str(git_sh)
        environment["PATH"] = os.pathsep.join(
            (str(git_sh.parent), str(git_usr_bin), environment.get("PATH", ""))
        )
        completed = subprocess.run(
            ["make", f"-j{workers}", "compiler"],
            cwd=source,
            env=environment,
            check=False,
        )
        if completed.returncode:
            raise BuildError(f"Windows build failed with exit code {completed.returncode}")

        DIST.mkdir(parents=True, exist_ok=True)
        artifact = DIST / f"exbasic-{version}-windows-amd64.zip"
        package = subprocess.run(
            [
                sys.executable,
                str(source / "scripts" / "package_release.py"),
                "--platform", "windows",
                "--arch", "amd64",
                "--output", str(artifact),
            ],
            cwd=source,
            check=False,
        )
        if package.returncode:
            raise BuildError(f"Windows packaging failed with exit code {package.returncode}")
    return [artifact]


def remote_job(
    label: str,
    expected_os: str,
    command: str,
    source_archive: Path,
    version: str,
    keep_remote: bool,
    key_file: Path,
) -> list[Path]:
    connection = ssh_argv(command, key_file)
    token = secrets.token_hex(8)
    job_name = f"exbasic-build-{version}-{token}"
    setup = f'job_root="${{TMPDIR:-/tmp}}/{job_name}"; mkdir -p "$job_root"; tar -xzf - -C "$job_root"'

    print(f"[{label}] checking the configured SSH host")
    probe = run_ssh(connection, "uname -s", capture=True)
    actual_os = (probe.stdout or b"").decode("utf-8", errors="replace").strip()
    if actual_os != expected_os:
        raise BuildError(f"{label} entry reached {actual_os or 'an unknown OS'}, expected {expected_os}")

    remote_root = f'"${{TMPDIR:-/tmp}}/{job_name}"'
    bundle: Path | None = None
    uploaded = False
    try:
        print(f"[{label}] uploading source snapshot")
        with source_archive.open("rb") as stream:
            run_ssh(connection, setup, stdin=stream)
        uploaded = True

        runner = "run-linux.sh" if label == "LINUX" else "run-macos.sh"
        print(f"[{label}] building release artifacts")
        build_command = (
            f"set -e; job_root={remote_root}; cd \"$job_root/source\"; "
            f"bash packaging/remote/{runner} \"$job_root/artifacts\"; "
            'tar -C "$job_root/artifacts" -czf "$job_root/artifacts.tar.gz" .'
        )
        run_ssh(connection, build_command)

        with tempfile.NamedTemporaryFile(prefix=f"{label.lower()}-", suffix=".tar.gz", delete=False) as temp:
            bundle = Path(temp.name)
            print(f"[{label}] downloading artifacts")
            run_ssh(connection, f'job_root={remote_root}; cat "$job_root/artifacts.tar.gz"', stdout=temp)

        DIST.mkdir(parents=True, exist_ok=True)
        paths = extract_bundle(bundle, DIST)
    finally:
        if bundle is not None:
            bundle.unlink(missing_ok=True)
        if uploaded and not keep_remote:
            cleanup = (
                f"job_root={remote_root}; "
                'case "$job_root" in "${TMPDIR:-/tmp}"/exbasic-build-*) rm -rf -- "$job_root" ;; *) exit 2 ;; esac'
            )
            run_ssh(connection, cleanup)

    current = [path for path in paths if path.is_file()]
    if not current:
        raise BuildError(f"{label} returned no artifacts")
    print(f"[{label}] retrieved {len(current)} files")
    return current


def checksum_files(version: str) -> list[Path]:
    prefix = f"exbasic-{version}-"
    return sorted(
        path for path in DIST.iterdir()
        if path.is_file() and path.name != "SHA256SUMS.txt" and path.name.startswith(prefix)
    )


def write_checksums(version: str) -> None:
    files = checksum_files(version)
    if not files:
        raise BuildError(f"DIST contains no artifacts for {version}")
    lines: list[str] = []
    for path in files:
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        lines.append(f"{digest}  {path.name}\n")
    (DIST / "SHA256SUMS.txt").write_text("".join(lines), encoding="ascii", newline="\n")


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target", choices=("all", "windows", "linux", "mac"), default="all",
        help="release platform to build (default: all)",
    )
    parser.add_argument(
        "--private-dir", type=Path,
        default=Path(os.environ.get("EXBASIC_PRIVATE_DIR", DEFAULT_PRIVATE)),
        help="directory containing .secrets and .privkey (or set EXBASIC_PRIVATE_DIR)",
    )
    parser.add_argument("--keep-remote", action="store_true", help="leave remote temporary directories for debugging")
    parser.add_argument("--check", action="store_true", help="validate configuration without connecting or building")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        version = read_version()
        targets = ["WINDOWS", "LINUX", "MAC"] if args.target == "all" else [args.target.upper()]
        remote_targets = [target for target in targets if target in {"LINUX", "MAC"}]
        connections: dict[str, str] = {}
        key_file_path = args.private_dir / ".privkey"
        if remote_targets:
            connections = read_connections(args.private_dir / ".secrets")
            missing = [target for target in remote_targets if target not in connections]
            if missing:
                raise BuildError(f"missing {', '.join(missing)} SSH configuration")
            if shutil.which("ssh") is None:
                raise BuildError("ssh was not found on PATH")

        if "WINDOWS" in targets:
            for command in ("make", "gcc", "g++", "go"):
                if shutil.which(command) is None:
                    raise BuildError(f"missing Windows build prerequisite: {command}")

        if remote_targets:
            with protected_private_key(key_file_path) as key_file:
                for target in remote_targets:
                    ssh_argv(connections[target], key_file)
        print(f"Configuration is valid for {', '.join(targets)} (version {version}); secret hosts are redacted.")
        if args.check:
            return 0

        with tempfile.TemporaryDirectory(prefix="exbasic-source-") as temporary:
            archive = Path(temporary) / "source.tar.gz"
            print("Creating source snapshot (private files and generated outputs are excluded)")
            create_source_archive(archive)
            print(f"Source snapshot: {archive.stat().st_size / (1024 * 1024):.1f} MiB")
            if "WINDOWS" in targets:
                local_windows_job(archive, version)
            if remote_targets:
                with protected_private_key(key_file_path) as key_file:
                    for target in remote_targets:
                        remote_job(
                            target,
                            "Linux" if target == "LINUX" else "Darwin",
                            connections[target],
                            archive,
                            version,
                            args.keep_remote,
                            key_file,
                        )
        write_checksums(version)
        print(f"Release artifacts and checksums are in {DIST}")
        return 0
    except (BuildError, OSError, tarfile.TarError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
