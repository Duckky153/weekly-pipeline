#!/bin/sh
# Runs every test. Sample data; no network, no model, no key needed.
cd "$(dirname "$0")" || exit 1
env -u TYPESAFE_API_KEY python3 -m unittest discover -s tests -p "test_*.py" -q && env -u TYPESAFE_API_KEY python3 lock.py check
