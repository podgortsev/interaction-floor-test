#!/usr/bin/env python3
"""Kept at the root because Paper 3's VALIDATION.md runs the checks from here.
The checks themselves live in tests/test_floor_test.py."""

import os
import runpy

runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "tests", "test_floor_test.py"), run_name="__main__")
