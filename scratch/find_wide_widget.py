"""Find which widget is forcing the minimum width."""
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
print(f"content minSizeHint : {content.minimumSizeHint().width()}")
print(f"content sizeHint    : {content.sizeHint().width()}")
print()

def walk(widget, depth=0):
    mw = widget.minimumSizeHint().width()
    if mw > 400:
        name = widget.objectName() or widget.__class__.__name__
        txt = ""
        if hasattr(widget, "text"):
            try:
                txt = widget.text()[:45].replace("\n", " ")
            except Exception:
                pass
        print(f"{'  '*depth}{name:22s} minW={mw:5d} w={widget.width():5d}  '{txt}'")
    for c in widget.children():
        if isinstance(c, QtWidgets.QWidget):
            walk(c, depth + 1)

walk(content)
