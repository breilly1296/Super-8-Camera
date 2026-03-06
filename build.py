#!/usr/bin/env python3
"""Convenience wrapper — run the full Super 8 Camera build from the repo root.

Usage:
    python build.py              # full build
    python build.py --specs      # print specs only
    python build.py --parts-only # export parts only
"""

from super8cam.build import main

if __name__ == "__main__":
    main()
