#!/usr/bin/env bash
# Runs on the configured Apple Silicon SSH builder.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT="${1:?usage: run-macos.sh OUTPUT_DIRECTORY}"
OUT="$(mkdir -p "$OUT" && cd "$OUT" && pwd)"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/local/go/bin:$PATH"

test "$(uname -s)" = Darwin || { echo "the MAC SSH entry must reach macOS" >&2; exit 1; }
test "$(uname -m)" = arm64 || {
  echo "the macOS builder must be Apple Silicon" >&2
  exit 1
}
arch -x86_64 /usr/bin/true >/dev/null 2>&1 || {
  echo "Rosetta 2 is required for the Intel build" >&2
  exit 1
}
for command in clang clang++ go make python3; do
  command -v "$command" >/dev/null 2>&1 || { echo "missing macOS build prerequisite: $command" >&2; exit 1; }
done

VERSION="$(sed -n 's/^VERSION[[:space:]]*=[[:space:]]*//p' "$ROOT/version.mk" | tr -d '\r\n')"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/exbasic-macos-arches.XXXXXX")"
cleanup() {
  case "$WORK" in "${TMPDIR:-/tmp}"/exbasic-macos-arches.*) rm -rf -- "$WORK" ;; esac
}
trap cleanup EXIT

build_arch() {
  ARCH="$1"
  SRC="$WORK/$ARCH"
  mkdir -p "$SRC"
  (cd "$ROOT" && tar -cf - .) | (cd "$SRC" && tar -xf -)
  cd "$SRC"
  rm -rf build

  if [ "$ARCH" = amd64 ]; then
    arch -x86_64 make -j"$(sysctl -n hw.logicalcpu 2>/dev/null || echo 2)" \
      CXX='clang++ -arch x86_64' CC='clang -arch x86_64' \
      GO='env GOARCH=amd64 go' compiler
  else
    make -j"$(sysctl -n hw.logicalcpu 2>/dev/null || echo 2)" \
      CXX='clang++ -arch arm64' CC='clang -arch arm64' \
      GO='env GOARCH=arm64 go' compiler
  fi

  python3 scripts/package_release.py \
    --platform macos \
    --arch "$ARCH" \
    --output "$OUT/exbasic-$VERSION-macos-$ARCH.zip"
}

PIDS=()
build_arch amd64 & PIDS+=("$!")
build_arch arm64 & PIDS+=("$!")
STATUS=0
for PID in "${PIDS[@]}"; do
  wait "$PID" || STATUS=1
done
test "$STATUS" -eq 0 || { echo "one or more macOS architecture builds failed" >&2; exit 1; }

echo "macOS Intel and Apple Silicon artifacts: $OUT"
