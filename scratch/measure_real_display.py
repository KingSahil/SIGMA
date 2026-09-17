"""Measure on the REAL screen (not the offscreen dummy) whether the window
and its content fit without scrollbars."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
os.environ.pop("QT_QPA_PLATFORM", None)     # use the real display
from PyQt5 import QtWidgets
from sigma_main_window import SigmaMainWindow

app = QtWidgets.QApplication(sys.argv)
scr = app.primaryScreen()
print("screen      :", scr.geometry().width(), "x", scr.geometry().height(),
      " available:", scr.availableGeometry().width(), "x", scr.availableGeometry().height(),
      " dpr:", scr.devicePixelRatio())

w = SigmaMainWindow(initial_file="demo_bpsk_100ksps_1msps.iq")
w.show()
for _ in range(10):
    app.processEvents()

sa = w.scroll_area
content = sa.widget()
print(f"\nwindow            : {w.width()}x{w.height()}")
print(f"viewport          : {sa.viewport().width()}x{sa.viewport().height()}")
print(f"content needed    : {content.sizeHint().width()}x{content.sizeHint().height()}")
print(f"h-scrollbar       : {sa.horizontalScrollBar().isVisible()}")
print(f"v-scrollbar       : {sa.verticalScrollBar().isVisible()}")
print()
for name, widget in (("symbol rate cell", w.m_symbol_rate[0]),
                     ("DEMOD state", w.lbl_demod_state),
                     ("bitstream", w.lbl_bitstream),
                     ("pipeline stepper", w.lbl_demod)):
    p = widget.mapTo(content, widget.rect().topLeft())
    vis = "VISIBLE" if p.y() < sa.viewport().height() else "BELOW FOLD"
    print(f"{name:18s}: y={p.y():4d} bottom={p.y()+widget.height():4d}  {vis}")
w.grab().save(r"C:/Users/sahil/Downloads/gnu/scratch/sigma_real_display.png")
print("\nsaved sigma_real_display.png")
