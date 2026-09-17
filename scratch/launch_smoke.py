"""Launch the REAL app (no offscreen) for a few seconds, confirm no exception
and that it is actually on screen, then close it cleanly."""
import sys, os, traceback
_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))
sys.path.insert(0, os.path.join(_ROOT, "src"))
os.chdir(_ROOT)

from PyQt5 import QtWidgets, QtCore
error = []
try:
    import sigma_iq_analyzer as entry
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    from sigma_main_window import SigmaMainWindow
    w = SigmaMainWindow()
    w.show()
    app.processEvents()
    QtCore.QTimer.singleShot(4000, app.quit)
    app.exec_()
    print("LAUNCH OK, no exception")
    print("final geometry :", w.width(), "x", w.height(), "visible:", w.isVisible())
    print("file           :", os.path.basename(w.metadata.filename))
    print("step 4 DEMOD   :", w.lbl_demod.text())
    print("step 5 BITS    :", w.lbl_bits.text())
except Exception:
    error.append(traceback.format_exc())
if error:
    print("LAUNCH FAILED")
    print(error[0])
    sys.exit(1)
