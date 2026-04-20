#!/usr/bin/env python3
"""Test runner for review analysis"""
import subprocess
import sys

print("Running manual deps test...")
result = subprocess.run([sys.executable, "test_manual_deps.py"], capture_output=True, text=True)
print(result.stdout)
if result.returncode != 0:
    print("STDERR:", result.stderr)
    sys.exit(1)
print("Tests passed!")
