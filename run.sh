#!/bin/bash
# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Use venv python if available, otherwise system python
if [ -f ./venv/bin/python ]; then
    ./venv/bin/python main.py
else
    python3 main.py
fi
