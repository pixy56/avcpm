#!/usr/bin/env python3
"""Standalone test runner for AVCPM integration tests."""
import sys
import subprocess
result = subprocess.run([sys.executable, "test_avcpm_integration.py", "-v"])
sys.exit(result.returncode)
