"""
Drive the real SigmaMainWindow and report what it displays, without a GUI.

This is the strongest way to verify a UI wiring change: it constructs the
actual window, runs the real display-update path, and reads back the text of
each widget. A screenshot only proves pixels were painted; this proves the
values are correct.

Run with Radioconda:
    C:\\Users\\<user>\\radioconda\\python.exe scratch/ui_probe.py

Why offscreen: no display is needed, so this works over SSH or in CI. Set
QT_QPA_PLATFORM=offscreen, then call w.grab() if you also want a PNG.
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
sys.path.insert(0, HERE)

# The geometry check needs the real display, so it only runs when the caller
# has NOT forced the offscreen platform (the offscreen dummy screen is only
# 800x600 and would report a misleading result).
_REAL_DISPLAY = os.environ.get("QT_QPA_PLATFORM") != "offscreen"


def dump(w, title):
    print(f"\n--- {title} ---")
    print(f"  symbol rate   : {w.m_symbol_rate[1].text()}")
    print(f"  samples/symbol: {w.m_sps[1].text()}")
    print(f"  sr lock       : {w.m_symrate_conf[1].text()}")
    print(f"  modulation    : {w.lbl_mod_class.text()} / {w.lbl_mod_conf.text()}")
    print(f"  step 4 DEMOD  : {w.lbl_demod.text()}")
    print(f"  step 5 BITS   : {w.lbl_bits.text()}")
    tip = w.lbl_bits.toolTip() or w.lbl_demod.toolTip()
    print(f"  note          : {tip}")


def check_geometry(w):
    """Confirm the window opens large enough to show the metrics and stepper.

    A reviewer looks at the default window. If the Symbol Rate row or the
    pipeline stepper fall below the fold, the feature may as well not exist.
    """
    frame = w.m_symbol_rate[0]
    metric_bottom = frame.mapTo(w, frame.rect().bottomLeft()).y()
    stepper_bottom = w.lbl_demod.mapTo(w, w.lbl_demod.rect().bottomLeft()).y()
    print(f"\n--- geometry ---")
    if not _REAL_DISPLAY:
        print("  skipped (offscreen platform; rerun without QT_QPA_PLATFORM")
        print("  set to measure against the real screen)")
        return
    print(f"  available screen : "
          f"{QtWidgets.QApplication.primaryScreen().availableGeometry().width()}x"
          f"{QtWidgets.QApplication.primaryScreen().availableGeometry().height()}")
    print(f"  window opened    : {w.width()}x{w.height()}")
    print(f"  metric row bottom: y={metric_bottom}  "
          f"{'visible' if metric_bottom < w.height() else 'BELOW FOLD'}")
    print(f"  stepper bottom   : y={stepper_bottom}  "
          f"{'visible' if stepper_bottom < w.height() else 'BELOW FOLD'}")


def main():
    from PyQt5 import QtWidgets
    from sigma_main_window import SigmaMainWindow
    from make_ground_truth import make_signal, FS

    app = QtWidgets.QApplication(sys.argv)

    # Case 1: a clean, properly pulse-shaped capture -> pipeline must complete.
    sig, _ = make_signal(100_000, "qpsk", alpha=0.35, n_symbols=4000, seed=11)
    good = os.path.join(HERE, "_probe_good.iq")
    sig.tofile(good)
    w = SigmaMainWindow()
    w.current_file = good
    w.samp_rate = FS
    w.metadata = type(w.metadata)(good, FS, 0.0)
    w._update_all_displays()
    app.processEvents()
    dump(w, "clean QPSK 100 ksps (expect steps 4+5 completed)")
    check_geometry(w)
    os.remove(good)

    # Case 2: the project's own synthetic file -> must decline, not fake it.
    real = os.path.join(HERE, "..", "data", "iq", "signal.iq")
    if os.path.exists(real):
        w2 = SigmaMainWindow()
        w2.current_file = os.path.abspath(real)
        w2.metadata = type(w2.metadata)(os.path.abspath(real), 1_000_000, 0.0)
        w2._update_all_displays()
        app.processEvents()
        dump(w2, "project signal.iq (expect steps 4+5 pending, with reason)")

    print("\nA completed step must mean bits were really recovered.")
    print("A pending step with a reason is correct behaviour, not a failure.")


if __name__ == "__main__":
    main()
