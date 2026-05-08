#!/bin/bash
set -e

PERSISTENT_DIR="/app/.cognee_system"
mkdir -p "$PERSISTENT_DIR"

COGNEE_PKG=$(python3 -c "import os, cognee; print(os.path.dirname(cognee.__file__))")
COGNEE_DATA_DIR="$COGNEE_PKG/.cognee_system"
COGNEE_STORAGE_DIR="$COGNEE_PKG/.data_storage"

if [ -d "$COGNEE_DATA_DIR" ] && [ ! -L "$COGNEE_DATA_DIR" ]; then
    mv "$COGNEE_DATA_DIR"/* "$PERSISTENT_DIR"/ 2>/dev/null || true
    rm -rf "$COGNEE_DATA_DIR"
fi
ln -sf "$PERSISTENT_DIR" "$COGNEE_DATA_DIR"

if [ -d "$COGNEE_STORAGE_DIR" ] && [ ! -L "$COGNEE_STORAGE_DIR" ]; then
    mv "$COGNEE_STORAGE_DIR"/* "$PERSISTENT_DIR"/data_storage/ 2>/dev/null || true
    rmdir "$COGNEE_STORAGE_DIR" 2>/dev/null || rm -rf "$COGNEE_STORAGE_DIR"
fi
mkdir -p "$PERSISTENT_DIR/data_storage"
ln -sf "$PERSISTENT_DIR/data_storage" "$COGNEE_STORAGE_DIR"

exec uvicorn main:app --host 0.0.0.0 --port 8000
