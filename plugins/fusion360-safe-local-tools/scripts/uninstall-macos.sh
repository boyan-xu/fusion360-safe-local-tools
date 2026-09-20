#!/bin/sh
set -eu

ADDIN_NAME="FusionSafeLocalTools"
USER_ROOT="${FUSION_SAFE_USER_ROOT:-$HOME}"
TARGET_DIR="$USER_ROOT/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/$ADDIN_NAME"
MANIFEST="$TARGET_DIR/$ADDIN_NAME.manifest"

if [ -L "$TARGET_DIR" ]; then
  echo "Removal stopped: target is a symbolic link." >&2
  exit 1
fi

if [ ! -d "$TARGET_DIR" ]; then
  echo "Nothing to remove: $TARGET_DIR does not exist."
  exit 0
fi

if [ ! -f "$MANIFEST" ] || ! grep -q '"autodeskProduct": "Fusion"' "$MANIFEST" || ! grep -q 'local_xby_fusion_safe_inspect_parameters' "$TARGET_DIR/$ADDIN_NAME.py"; then
  echo "Removal stopped: the target does not match this add-in's manifest." >&2
  exit 1
fi

TRASH_TARGET=$(mktemp -d "$USER_ROOT/.Trash/${ADDIN_NAME}.XXXXXX")
mv "$TARGET_DIR" "$TRASH_TARGET/$ADDIN_NAME"
echo "Moved the add-in to Trash (recoverable):"
echo "$TRASH_TARGET"
