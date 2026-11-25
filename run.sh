#!/bin/sh
# Serves the page locally. Sample data only; nothing is sent anywhere.
cd "$(dirname "$0")" || exit 1
python3 pipeline.py serve 8765
