#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SIGMA - Signal Intelligence & Generalized Modulation Analyzer
Root Launcher Script
Delegates execution to src.sigma_iq_analyzer
"""

import os
import sys

# Ensure src directory is in sys.path
root_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(root_dir, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from sigma_iq_analyzer import main

if __name__ == '__main__':
    sys.exit(main())
