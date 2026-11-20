# Release process

Release tooling creates native Windows, Linux, Intel macOS, and Apple Silicon
macOS compiler packages. It is dry-run-first: building does not publish, and
publishing defaults to a GitHub draft release.

## Builder configuration

Create `.private/.secrets` with SSH commands for the remote builders:

```text
LINUX: ssh linux-builder
MAC: ssh mac-builder
```

Put the matching private key in `.private/.privkey`. Both paths are ignored by
Git. You may keep these files elsewhere and pass `--private-dir`, or set the
`EXBASIC_PRIVATE_DIR` environment variable. Host names and secret values are
not printed by the build helper.

The Windows lane requires GNU Make, GCC/G++, Go, and Python. The Linux host
requires GNU Make, GCC/G++, Go, and Python 3. The macOS host must be Apple
Silicon with Xcode command-line tools, Go, Python 3, and Rosetta 2.

## Build and verify

Validate the local tools and private configuration without connecting:

```console
python scripts/remote_build.py --check
```

Build all platforms:

```console
python scripts/remote_build.py
```

Use `--target windows`, `--target linux`, or `--target mac` to run one lane.
Compiler ZIP files and `SHA256SUMS.txt` are written to `DIST/`.

## Publish

Update `version.mk` and add a matching section to `CHANGELOG.md`, then inspect
the publishing preflight:

```console
python scripts/publish_release.py
```

After committing the release changes, create or update a draft GitHub release:

```console
python scripts/publish_release.py --execute
```

Add `--publish-release` only when the draft has been reviewed and should become
public. `--commit-all` is an explicit convenience for committing every current
worktree change as the release commit.
