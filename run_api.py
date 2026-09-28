#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIGMA - Signal Intelligence & Generalized Modulation Analyzer
Root Launcher for FastAPI Service
"""

import os
import sys
import argparse

root_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(root_dir, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from sigma_api import app

def main():
    parser = argparse.ArgumentParser(description="SIGMA RF Intelligence API Server")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port number (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()

    import uvicorn
    print(f"[*] Starting SIGMA RF Intelligence API at http://{args.host}:{args.port}")
    print(f"[*] Interactive API Docs available at http://{args.host}:{args.port}/docs")
    uvicorn.run("sigma_api:app", host=args.host, port=args.port, reload=args.reload)

if __name__ == "__main__":
    main()
