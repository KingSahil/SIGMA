#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# SIGMA - Signal Intelligence & Generalized Modulation Analyzer
# SIH 2026 Engineering Prototype
#

import sys
import signal
from PyQt5 import Qt, QtWidgets

from sigma_main_window import SigmaMainWindow
# Backwards compatibility alias for the legacy top_block class
try:
    from sigma_iq_analyzer_original import sigma_iq_analyzer as legacy_flowgraph
except ImportError:
    legacy_flowgraph = None


def main():
    qapp = QtWidgets.QApplication.instance()
    if not qapp:
        qapp = QtWidgets.QApplication(sys.argv)

    # Instantiate the SIGMA RF Intelligence Workstation
    window = SigmaMainWindow(initial_file="signal.iq")
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
