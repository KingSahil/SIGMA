#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# SIGMA - Signal Intelligence & Generalized Modulation Analyzer
# SIH 2026 Engineering Prototype
#

import os
import sys
import signal

# Ensure src directory is in sys.path
_src_dir = os.path.dirname(os.path.abspath(__file__))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from PyQt5 import Qt, QtWidgets

try:
    from .sigma_main_window import SigmaMainWindow
    from .sigma_theme import create_sigma_icon
except ImportError:
    from sigma_main_window import SigmaMainWindow
    from sigma_theme import create_sigma_icon


# Backwards compatibility alias for the legacy top_block class
try:
    try:
        from .sigma_iq_analyzer_original import sigma_iq_analyzer as legacy_flowgraph
    except ImportError:
        from sigma_iq_analyzer_original import sigma_iq_analyzer as legacy_flowgraph
except ImportError:
    legacy_flowgraph = None


def main():
    # Set explicit Windows AppUserModelID so taskbar displays the custom SIGMA icon
    if sys.platform.startswith("win"):
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("sigma.rf.analyzer")
        except Exception:
            pass

    qapp = QtWidgets.QApplication.instance()
    if not qapp:
        qapp = QtWidgets.QApplication(sys.argv)

    # Enforce pure white text palette globally across all widgets
    from PyQt5 import QtGui
    palette = QtGui.QPalette()
    palette.setColor(QtGui.QPalette.Window, QtGui.QColor("#0b0f17"))
    palette.setColor(QtGui.QPalette.WindowText, QtGui.QColor("#ffffff"))
    palette.setColor(QtGui.QPalette.Base, QtGui.QColor("#131822"))
    palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor("#1a2230"))
    palette.setColor(QtGui.QPalette.ToolTipBase, QtGui.QColor("#131822"))
    palette.setColor(QtGui.QPalette.ToolTipText, QtGui.QColor("#ffffff"))
    palette.setColor(QtGui.QPalette.Text, QtGui.QColor("#ffffff"))
    palette.setColor(QtGui.QPalette.Button, QtGui.QColor("#1a2230"))
    palette.setColor(QtGui.QPalette.ButtonText, QtGui.QColor("#ffffff"))
    palette.setColor(QtGui.QPalette.BrightText, QtGui.QColor("#38bdf8"))
    palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor("#38bdf8"))
    palette.setColor(QtGui.QPalette.HighlightedText, QtGui.QColor("#000000"))
    qapp.setPalette(palette)

    # Apply SIGMA custom icon (removes any default GNU Radio lollipop icon)
    qapp.setWindowIcon(create_sigma_icon())

    # Instantiate the SIGMA RF Intelligence Workstation
    window = SigmaMainWindow(initial_file="signal.iq")
    window.setWindowIcon(create_sigma_icon())
    window.show()

    def sig_handler(sig=None, frame=None):
        try:
            window.close()
        except Exception:
            pass
        QtWidgets.QApplication.quit()

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    # Keep Python interpreter responsive to Ctrl+C
    timer = Qt.QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)

    return qapp.exec_()


if __name__ == '__main__':
    sys.exit(main())
