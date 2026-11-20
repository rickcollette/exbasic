#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT="${1:?usage: run-linux.sh OUTPUT_DIRECTORY}"
OUT="$(mkdir -p "$OUT" && cd "$OUT" && pwd)"

test "$(uname -s)" = Linux || { echo "the LINUX SSH entry must reach Linux" >&2; exit 1; }
for command in g++ gcc go make python3; do
  command -v "$command" >/dev/null 2>&1 || { echo "missing Linux build prerequisite: $command" >&2; exit 1; }
done

ARCH="$(uname -m)"
case "$ARCH" in
  x86_64|amd64) ARCH=amd64 ;;
  aarch64|arm64) ARCH=arm64 ;;
  *) echo "unsupported Linux architecture: $ARCH" >&2; exit 1 ;;
esac
VERSION="$(sed -n 's/^VERSION[[:space:]]*=[[:space:]]*//p' "$ROOT/version.mk" | tr -d '\r\n')"
test -n "$VERSION"

cd "$ROOT"
rm -rf build
make -j"$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 2)" compiler
python3 scripts/package_release.py \
  --platform linux \
  --arch "$ARCH" \
  --output "$OUT/exbasic-$VERSION-linux-$ARCH.zip"

echo "Linux artifact: $OUT/exbasic-$VERSION-linux-$ARCH.zip"
