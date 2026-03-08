#!/usr/bin/env python3
"""Verify interference fixes by running only the interference checks.

Requires CadQuery installed.  No STEP export — runs in under 10 seconds.

Usage:
    python VERIFY_INTERFERENCE.py
"""

import sys
import time

sys.path.insert(0, ".")

from super8cam.assemblies.full_camera import (
    build,
    check_interference,
    print_interference_report,
)

start = time.time()

print("Building assembly (no export)...")
assy = build()
build_t = time.time() - start
print(f"  Assembly built in {build_t:.1f}s")

print("Running interference checks...")
result = check_interference(assy)
check_t = time.time() - start - build_t
print(f"  Checks completed in {check_t:.1f}s")

passed = print_interference_report(result)

elapsed = time.time() - start
print(f"\nTotal time: {elapsed:.1f}s")

sys.exit(0 if passed else 1)
