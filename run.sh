#!/usr/bin/env bash
set -e

if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    echo "Error: Python 3 is not installed or not in PATH."
    exit 1
fi

"$PYTHON_CMD" sync.py "$@"
