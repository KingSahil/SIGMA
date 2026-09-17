"""Screenshot the DECLINED state so the refusal is visibly documented."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
os.environ.pop("QT_QPA_PLATFORM", None)
from PyQt5 import QtWidgets
from sigma_main_window import SigmaMainWindow
app = QtWidgets.QApplication(sys.argv)
w = SigmaMainWindow(initial_file="signal.iq")
w.show()
for _ in range(10): app.processEvents()
print("DEMOD state :", w.lbl_demod_state.text())
print("reason      :", w.lbl_demod_reason.text())
print("bitstream   :", w.lbl_bitstream.text())
w.grab().save(r"C:/Users/sahil/Downloads/gnu/scratch/sigma_declined.png")
print("saved sigma_declined.png")
