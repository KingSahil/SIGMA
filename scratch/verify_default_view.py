"""Confirm the app's DEFAULT view (no file loaded by the user) shows a
complete pipeline, and capture it."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from PyQt5 import QtWidgets
from sigma_main_window import SigmaMainWindow
from sigma_main_window import resolve_sample_path

app = QtWidgets.QApplication(sys.argv)

print("default file resolved to:", os.path.basename(resolve_sample_path()))

w = SigmaMainWindow()
w.show()
for _ in range(6):
    app.processEvents()

print(f"window          : {w.width()}x{w.height()}")
print(f"input file      : {w.metadata.filename}")
print(f"symbol rate     : {w.m_symbol_rate[1].text()}")
print(f"samples/symbol  : {w.m_sps[1].text()}")
print(f"lock            : {w.m_symrate_conf[1].text()}")
print(f"modulation      : {w.lbl_mod_class.text()} / {w.lbl_mod_conf.text()}")
print(f"step 4 DEMOD    : {w.lbl_demod.text()}")
print(f"step 5 BITS     : {w.lbl_bits.text()}")
print(f"bits recovered  : {w.lbl_bits.toolTip()}")
w.grab().save(r"C:/Users/sahil/Downloads/gnu/scratch/sigma_default_view.png")
print("saved sigma_default_view.png")
