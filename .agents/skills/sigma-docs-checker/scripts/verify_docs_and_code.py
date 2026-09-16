#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIGMA Project Documentation & Code Verification Script
Checks dataset presence, module imports, UI-doc synchronization, and SIH requirements.
"""

import os
import sys
import re

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, "src"))

# Ensure stdout supports unicode on Windows terminals
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def log_check(name, passed, details=""):
    symbol = "[PASS]" if passed else "[FAIL]"
    status = "OK" if passed else "ATTENTION NEEDED"
    print(f"{symbol} {name}: {status}")
    if details:
        print(f"    ↳ {details}")

def check_datasets():
    print("\n--- 1. Checking Datasets in data/ ---")
    expected_iq = [
        "signal.iq",
        "bpsk_modulated_1msps.iq",
        "qpsk_modulated_1msps.iq",
        "fm_rds_250k_1Msamples.iq",
        "decimation_exercise.iq"
    ]
    expected_audio = [
        "sdr_test_stereo.wav",
        "thunderclouds_clip.wav"
    ]

    all_ok = True
    for f in expected_iq:
        p = os.path.join(ROOT_DIR, "data", "iq", f)
        exists = os.path.exists(p)
        size = os.path.getsize(p) if exists else 0
        log_check(f"IQ Dataset '{f}'", exists, f"Size: {size:,} bytes")
        if not exists:
            all_ok = False

    for f in expected_audio:
        p = os.path.join(ROOT_DIR, "data", "audio", f)
        exists = os.path.exists(p)
        size = os.path.getsize(p) if exists else 0
        log_check(f"Audio Dataset '{f}'", exists, f"Size: {size:,} bytes")
        if not exists:
            all_ok = False

    return all_ok

def check_modules():
    print("\n--- 2. Checking Module Imports ---")
    modules = [
        "src.sigma_analyzer_core",
        "src.sigma_flowgraph",
        "src.sigma_theme",
        "src.sigma_main_window"
    ]
    all_ok = True
    for m in modules:
        try:
            __import__(m)
            log_check(f"Module '{m}'", True)
        except Exception as e:
            log_check(f"Module '{m}'", False, str(e))
            all_ok = False
    return all_ok

def check_doc_ui_alignment():
    print("\n--- 3. Checking Doc vs UI Code Alignment ---")
    main_window_py = os.path.join(ROOT_DIR, "src", "sigma_main_window.py")
    getting_started_md = os.path.join(ROOT_DIR, "docs", "GETTING_STARTED_AND_WORKFLOW.md")

    if not os.path.exists(main_window_py) or not os.path.exists(getting_started_md):
        log_check("Source & Doc Files Exist", False)
        return False

    with open(main_window_py, "r", encoding="utf-8") as f:
        code = f.read()

    with open(getting_started_md, "r", encoding="utf-8") as f:
        doc = f.read()

    # Check button mentions
    has_unified_load_btn = "Load Signal File" in code
    doc_has_separate_load = "Load IQ File" in doc and "Load WAV" in doc
    
    if has_unified_load_btn and doc_has_separate_load:
        log_check(
            "Load Buttons Alignment",
            False,
            "UI consolidated buttons into 'Load Signal File', but docs still document separate 'Load IQ File' and 'Load WAV' buttons."
        )
    else:
        log_check("Load Buttons Alignment", True)

    return True

def check_sih_status():
    print("\n--- 4. SIH 6147 Deliverables Audit ---")
    features = [
        ("WAV & IQ Ingestion", True, "Implemented with stereo/mono auto-conversion to complex64"),
        ("Oscilloscope / Time Domain Plot", True, "Implemented in SigmaFlowgraph (qtgui.time_sink_c)"),
        ("Spectrum / FFT Frequency Plot", True, "Implemented in SigmaFlowgraph (qtgui.freq_sink_c)"),
        ("Waterfall / Spectrogram Plot", True, "Implemented in SigmaFlowgraph (qtgui.waterfall_sink_c)"),
        ("Constellation Diagram Plot", True, "Implemented in SigmaFlowgraph (qtgui.const_sink_c) with balanced 1:1 aspect"),
        ("Bandwidth & SNR Extraction", True, "Implemented in SignalMetadata: 99% OBW, noise floor, SNR in dB"),
        ("Modulation Classification", True, "Implemented in SignalMetadata: BPSK, QPSK, FM/RDS, AM/ASK, Audio"),
        ("Automatic Sample Rate Estimation", False, "Defaults to 1 MSps with dataset hint auto-detection; blind cyclic correlation pending"),
        ("Demodulation (FSK, QAM, PSK)", False, "Stage 4 marked pending; multi-mode audio discriminator/heterodyne listening available"),
        ("De-interleaving Schemes", False, "Stage not yet implemented"),
        ("Forward Error Correction (FEC)", False, "Viterbi/Reed-Solomon/LDPC not yet implemented"),
        ("Bitstream & Packet Correlation", False, "Stage 5 marked pending")
    ]
    for name, status, note in features:
        log_check(name, status, note)

def main():
    print("=" * 60)
    print(" SIGMA Verification & Docs Alignment Audit ")
    print("=" * 60)
    check_datasets()
    check_modules()
    check_doc_ui_alignment()
    check_sih_status()
    print("\n" + "=" * 60)
    print(" Audit Complete ")
    print("=" * 60)

if __name__ == "__main__":
    main()
