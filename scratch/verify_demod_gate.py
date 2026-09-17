"""Verify the demod gate picks the right demodulator per classification, and
still refuses what it genuinely cannot slice."""
import os, sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from PyQt5 import QtWidgets
from sigma_main_window import SigmaMainWindow

app = QtWidgets.QApplication(sys.argv)
DEMO = os.path.join("data", "iq", "demo_bpsk_100ksps_1msps.iq")
fails = 0

def probe(label, want_state):
    """Force a classification, run the real gate, report the DEMOD card state."""
    global fails
    w = SigmaMainWindow(initial_file=DEMO)
    w.metadata.modulation_class = label
    w.metadata.modulation_confidence = "measured"
    w._run_demod_stage()
    got = w.lbl_demod_state.text()
    ok = got == want_state
    if not ok:
        fails += 1
    detail = w.lbl_demod_method.text() if got == "LOCKED" else w.lbl_demod_reason.text()
    print(f"{'ok  ' if ok else 'FAIL'} {label:20s} -> {got:10s} want={want_state:10s} {detail[:56]}")
    w.close()

print("=== demod gate classification matrix ===")
probe("BPSK",           "LOCKED")        # plain
probe("BPSK / 2-FSK",   "LOCKED")        # the ambiguity that used to be refused
probe("QPSK",           "LOCKED")        # plain
probe("QPSK / 8PSK",    "LOCKED")        # QPSK half of a combined label
probe("8PSK",           "UNSUPPORTED")   # genuinely not sliceable
probe("Digital PSK/FSK","UNSUPPORTED")   # indeterminate PSK family
probe("AM / ASK",       "UNSUPPORTED")   # not PSK at all
probe("CW / Unmodulated","UNSUPPORTED")  # no constellation

print(f"\n{'ALL PASSED' if fails == 0 else str(fails) + ' FAILURES'}")
sys.exit(1 if fails else 0)
