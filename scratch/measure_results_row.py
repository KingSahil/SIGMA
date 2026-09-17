"""Check whether the 4-card results row overflows at 1400px wide."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt5 import QtWidgets
from sigma_main_window import SigmaMainWindow

app = QtWidgets.QApplication(sys.argv)
w = SigmaMainWindow(initial_file="demo_bpsk_100ksps_1msps.iq")
w.show()
for _ in range(8):
    app.processEvents()

content = w.scroll_area.widget()
print(f"window        : {w.width()}x{w.height()}")
print(f"content actual: {content.width()}x{content.height()}")
print(f"sizeHint      : {content.sizeHint().width()}x{content.sizeHint().height()}")
print(f"h-scrollbar   : {w.scroll_area.horizontalScrollBar().isVisible()}")
print(f"v-scrollbar   : {w.scroll_area.verticalScrollBar().isVisible()}")
print()
# width of each results card
for name, child in (("analysis", w.m_symbol_rate[0].parent()),
                    ("modulation", w.lbl_mod_class.parent()),
                    ("demod", w.lbl_bitstream.parent())):
    p = child.mapTo(content, child.rect().topLeft())
    print(f"{name:12s}: x={p.x():4d} w={child.width():4d} right={p.x()+child.width()}")

print(f"\nviewport width: {w.scroll_area.viewport().width()}")
print("H-SCROLL NEEDED" if content.width() > w.scroll_area.viewport().width() else "NO H-SCROLL")
