"""Measure whether the new DEMODULATION card forces the window taller, and
whether the four-card results row is too cramped at 1400px wide."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt5 import QtWidgets
from sigma_main_window import SigmaMainWindow

app = QtWidgets.QApplication(sys.argv)
w = SigmaMainWindow(initial_file="demo_bpsk_100ksps_1msps.iq")
w.resize(1400, 1100)          # generous, then measure what is actually needed
w.show()
for _ in range(8):
    app.processEvents()

sa = w.scroll_area
content = sa.widget()
print(f"window              : {w.width()}x{w.height()}")
print(f"scroll viewport     : {sa.viewport().width()}x{sa.viewport().height()}")
print(f"content sizeHint    : {content.sizeHint().width()}x{content.sizeHint().height()}")
print(f"content actual      : {content.width()}x{content.height()}")

# Where is the results row and the stepper?
card = w.lbl_bitstream.parent()
for name, widget in (("bitstream label", w.lbl_bitstream),
                     ("demod stats", w.lbl_demod_stats),
                     ("pipeline stepper", w.lbl_demod),
                     ("symbol rate cell", w.m_symbol_rate[0])):
    p = widget.mapTo(content, widget.rect().topLeft())
    print(f"{name:20s}: y={p.y():4d}  h={widget.height():3d}  bottom={p.y()+widget.height()}")

print(f"\ncontent height needed to avoid scrolling: {content.sizeHint().height()}")
print(f"viewport height available               : {sa.viewport().height()}")
print("SCROLL NEEDED" if content.sizeHint().height() > sa.viewport().height() else "FITS")
