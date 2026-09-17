"""Authoritative geometry check: launch exactly as run.py does, then report
the size the window ACTUALLY has after show(), from inside the process."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from PyQt5 import QtWidgets
from sigma_main_window import SigmaMainWindow

app = QtWidgets.QApplication(sys.argv)

# Same construction order as sigma_iq_analyzer.main()
window = SigmaMainWindow(initial_file="signal.iq")
window.show()
for _ in range(6):
    app.processEvents()

scr = app.primaryScreen().availableGeometry()
print(f"available screen : {scr.width()}x{scr.height()}")
print(f"window after show: {window.width()}x{window.height()}")
print(f"window frame geom: {window.frameGeometry().width()}x{window.frameGeometry().height()}")
print(f"isMaximized={window.isMaximized()}  isVisible={window.isVisible()}")

frame = window.m_symbol_rate[0]
mb = frame.mapTo(window, frame.rect().bottomLeft()).y()
sb = window.lbl_demod.mapTo(window, window.lbl_demod.rect().bottomLeft()).y()
print(f"symbol-rate row bottom y={mb}  -> visible: {mb < window.height()}")
print(f"pipeline stepper bottom y={sb}  -> visible: {sb < window.height()}")
print(f"Symbol Rate cell : {window.m_symbol_rate[1].text()!r}")
window.grab().save(r"C:/Users/sahil/Downloads/gnu/scratch/sigma_live_geometry.png")
print("saved sigma_live_geometry.png")
