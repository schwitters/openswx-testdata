#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 openswx contributors
"""Compatibility entry point for the original cylinder-only export driver."""
import sys

from run_case import main as run_case_main


def main():
    return run_case_main("part-cylinder-001", legacy_exporter=True)


if __name__ == "__main__":
    sys.exit(main())
