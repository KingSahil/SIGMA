"""Two things the offscreen default-view probe does not prove:
1. The real entry point (src/sigma_iq_analyzer.py) still starts without crashing.
2. Deliberately loading signal.iq still yields the honest refusal (not a silent pass).
"""
import sys, os
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, os.pardir))
sys.path.insert(0, os.path.join(_ROOT, "src"))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt5 import QtWidgets

# --- 1. exercise the real entry point's window construction path ---
import sigma_iq_analyzer as entry
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
from sigma_main_window import SigmaMainWindow, resolve_sample_path

w = SigmaMainWindow()          # exactly what the entry point now does
w.show()
for _ in range(6):
    app.processEvents()
print("entry-point construction OK; opened on:", os.path.basename(w.metadata.filename))
print(f"  step 4 DEMOD : {w.lbl_demod.text()}")
assert "\u2713" in w.lbl_demod.text(), "default view should tick DEMOD"

# --- 2. explicit signal.iq must still be honoured, and must decline ---
w2 = SigmaMainWindow(initial_file="signal.iq")
w2.show()
for _ in range(6):
    app.processEvents()
print("\nexplicit signal.iq honoured:", os.path.basename(w2.metadata.filename))
print(f"  symbol rate  : {w2.m_symbol_rate[1].text()}")
print(f"  lock         : {w2.m_symrate_conf[1].text()}")
print(f"  step 4 DEMOD : {w2.lbl_demod.text()}")
print(f"  reason       : {w2.lbl_demod.toolTip()}")
assert os.path.basename(w2.metadata.filename) == "signal.iq", "explicit path ignored!"
assert "\u2713" not in w2.lbl_demod.text(), "must NOT tick DEMOD on an untrusted clock"
print("\nboth checks passed")
