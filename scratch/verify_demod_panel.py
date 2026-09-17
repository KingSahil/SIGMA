"""Verify the new DEMODULATION card shows real values, and the refusal path
shows a reason instead of a bitstream."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt5 import QtWidgets
from sigma_main_window import SigmaMainWindow

app = QtWidgets.QApplication(sys.argv)

def dump(w, title):
    print(f"--- {title} ---")
    print(f"  pipeline 4    : {w.lbl_demod.text()}")
    print(f"  pipeline 5    : {w.lbl_bits.text()}")
    print(f"  DEMOD state   : {w.lbl_demod_state.text()}")
    print(f"  DEMOD method  : {w.lbl_demod_method.text()}")
    for line in w.lbl_demod_stats.text().split("\n"):
        print(f"  DEMOD stats   : {line}")
    if w.lbl_demod_reason.isVisible():
        print(f"  DEMOD reason  : {w.lbl_demod_reason.text()}")
    print(f"  BITSTREAM     : {w.lbl_bitstream.text()}")
    print(f"  demod_result  : {'present' if w.demod_result else 'None'}")
    print()

for path, title in (("demo_bpsk_100ksps_1msps.iq", "demo (expect LOCKED)"),
                    ("signal.iq", "signal.iq (expect DECLINED)")):
    w = SigmaMainWindow(initial_file=path)
    w.show()
    for _ in range(6):
        app.processEvents()
    print(f"file = {os.path.basename(path)}   window {w.width()}x{w.height()}")
    dump(w, title)

w = SigmaMainWindow(initial_file="demo_bpsk_100ksps_1msps.iq")
w.show()
for _ in range(6):
    app.processEvents()
w.grab().save(r"C:/Users/sahil/Downloads/gnu/scratch/sigma_demod_panel.png")
print("saved sigma_demod_panel.png")
