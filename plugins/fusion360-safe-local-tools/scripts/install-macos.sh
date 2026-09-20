#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PLUGIN_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
SOURCE_DIR="$PLUGIN_ROOT/assets/FusionSafeLocalTools"
USER_ROOT="${FUSION_SAFE_USER_ROOT:-$HOME}"
ADDINS_DIR="$USER_ROOT/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns"
TARGET_DIR="$ADDINS_DIR/FusionSafeLocalTools"

if [ ! -f "$SOURCE_DIR/FusionSafeLocalTools.manifest" ] || [ ! -f "$SOURCE_DIR/FusionSafeLocalTools.py" ]; then
  echo "Installation stopped: the packaged Fusion add-in is incomplete." >&2
  exit 1
fi

mkdir -p "$ADDINS_DIR"

if ! mkdir "$TARGET_DIR"; then
  echo "Installation stopped: $TARGET_DIR already exists. Nothing was overwritten." >&2
  exit 2
fi

cp "$SOURCE_DIR/"*.py "$SOURCE_DIR/FusionSafeLocalTools.manifest" "$TARGET_DIR/"
echo "Installed FusionSafeLocalTools at:"
echo "$TARGET_DIR"
