#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BUILD_ROOT="$PROJECT_ROOT/build/lambda"
PACKAGE_DIR="$BUILD_ROOT/package"
ZIP_FILE="$BUILD_ROOT/collector-lambda.zip"

rm -rf "$PACKAGE_DIR" "$ZIP_FILE"
mkdir -p "$PACKAGE_DIR"

echo "Installiere schlanke Lambda-Abhängigkeiten..."
python3 -m pip install \
  --requirement "$PROJECT_ROOT/requirements-lambda.txt" \
  --target "$PACKAGE_DIR" \
  --platform manylinux2014_x86_64 \
  --implementation cp \
  --python-version 3.13 \
  --only-binary=:all: \
  --upgrade

echo "Kopiere Collector-Code..."
cp -r "$PROJECT_ROOT/src" "$PACKAGE_DIR/src"

echo "Entferne unnötige Dateien..."
find "$PACKAGE_DIR" -type d -name "__pycache__" -prune -exec rm -rf {} +
find "$PACKAGE_DIR" -type d -name "*.dist-info" -exec sh -c 'rm -rf "$1"/RECORD "$1"/INSTALLER "$1"/REQUESTED 2>/dev/null || true' _ {} \;

echo "Erstelle ZIP-Paket..."
python3 - "$PACKAGE_DIR" "$ZIP_FILE" <<'PY'
from pathlib import Path
import sys
import zipfile

package_dir = Path(sys.argv[1])
zip_file = Path(sys.argv[2])

with zipfile.ZipFile(zip_file, "w", zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(package_dir.rglob("*")):
        if path.is_file():
            archive.write(path, path.relative_to(package_dir))

print(zip_file)
PY

echo
echo "Lambda-Paket:"
ls -lh "$ZIP_FILE"
echo
echo "Ungepackte Größe:"
du -sh "$PACKAGE_DIR"
