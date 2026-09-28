#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIGMA - Signal Intelligence & Generalized Modulation Analyzer
FastAPI Application Entrypoint
"""

import os
import sys

root_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(root_dir, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from sigma_api import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
