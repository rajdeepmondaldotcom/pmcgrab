#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python}"
WHEEL_PATH="${1:-}"

if [[ -z "$WHEEL_PATH" ]]; then
  WHEEL_PATH="$(find "$ROOT_DIR/dist" -maxdepth 1 -type f -name "pmcgrab-*.whl" | sort | tail -n 1)"
fi

if [[ ! -f "$WHEEL_PATH" ]]; then
  echo "Wheel not found: $WHEEL_PATH" >&2
  echo "Run 'uv build' first, or pass a wheel path." >&2
  exit 1
fi

EXPECTED_VERSION="$(
  cd "$ROOT_DIR"
  "$PYTHON_BIN" - <<'PY'
import tomllib
from pathlib import Path

data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
print(data["project"]["version"])
PY
)"

TMP_DIR="$(mktemp -d)"
cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

"$PYTHON_BIN" -m venv "$TMP_DIR/venv"
# shellcheck disable=SC1091
. "$TMP_DIR/venv/bin/activate"

python -m pip install --upgrade pip >/dev/null
python -m pip install "$WHEEL_PATH" >/dev/null

python - <<PY
from importlib import metadata

import pmcgrab

expected = "$EXPECTED_VERSION"
assert pmcgrab.__version__ == expected, pmcgrab.__version__
assert metadata.version("pmcgrab") == expected
print(f"pmcgrab {expected} imports from the built wheel")
PY

python -m pmcgrab --version | grep -Fx "pmcgrab $EXPECTED_VERSION" >/dev/null
python -m pmcgrab --help | grep -F -- "--from-file" >/dev/null
