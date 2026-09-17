"""Verify the sample-rate provenance line is actually rendered in the GUI."""
import os, sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from PyQt5 import QtWidgets
from sigma_main_window import SigmaMainWindow

app = QtWidgets.QApplication(sys.argv)
fails = 0

def show(path, want_txt, want_class):
    global fails
    w = SigmaMainWindow(initial_file=path)
    w._update_all_displays()
    txt = w.lbl_rate_source.text()
    cls = w.lbl_rate_source.property("class")
    ok = want_txt in txt and cls == want_class
    if not ok:
        fails += 1
    print(f"{'ok  ' if ok else 'FAIL'} {os.path.basename(path):32s} "
          f"class={cls:18s} text={txt!r}")
    w.close()

print("=== sample-rate provenance line ===")
p = lambda f: os.path.join("data", "iq", f)
show(p("demo_bpsk_100ksps_1msps.iq"), 'token "1msps"', "RateSourceWarn")
show(p("fm_rds_250k_1Msamples.iq"),  'token "250k"',  "RateSourceWarn")
show(p("signal.iq"),                 "ASSUMED",       "RateSourceIdle")

print(f"\n{'ALL PASSED' if fails == 0 else str(fails) + ' FAILURES'}")
sys.exit(1 if fails else 0)
