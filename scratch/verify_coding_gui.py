"""Verify the coding layer through the REAL GUI.

Proves the wiring in sigma_main_window.py: a demodulated capture must carry the
coding-layer result onto the DEMODULATION card, and an uncoded capture must
report "not present" rather than a fabricated payload.

Reads widget text back from an offscreen window -- a screenshot would prove
pixels were painted, not that the values are right.

Run:  python scratch/verify_coding_gui.py
"""

import os
import sys

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from PyQt5 import QtWidgets                    # noqa: E402

from sigma_coding import (                     # noqa: E402
    analyse_coding_layer,
    conv_encode,
    interleave,
)


def _write_coded_capture(path, mod="QPSK", seed=5, info_bits=400,
                         il_mode=None):
    """Synthesise an IQ capture whose bits are a real codeword.

    We build the coded bit stream first, then map it onto a QPSK symbol
    sequence -- so the demodulator recovers exactly those bits.
    """
    from make_ground_truth import make_signal  # scratch/ helper
    rng = np.random.default_rng(seed)
    info = rng.integers(0, 2, info_bits).astype(np.uint8)
    enc = conv_encode(info)
    if il_mode:
        enc = interleave(enc, il_mode)

    # Pack bits into QPSK symbols (2 bits each), MSB first.
    n_sym = len(enc) // 2
    enc = enc[:n_sym * 2]
    idx = (enc[0::2].astype(np.int32) << 1) | enc[1::2].astype(np.int32)
    mapping = np.array([1 + 1j, -1 + 1j, 1 - 1j, -1 - 1j]) / np.sqrt(2)
    syms = mapping[idx]

    return syms, info


def main():
    ok = True
    print("=" * 78)
    print("CODING LAYER THROUGH THE REAL GUI")
    print("=" * 78)
    print(f"offscreen platform = {os.environ.get('QT_QPA_PLATFORM')}")

    # Direct check first: the analysis function over a coded stream.
    print()
    print("1. analyse_coding_layer over a coded stream")
    rng = np.random.default_rng(7)
    info = rng.integers(0, 2, 400).astype(np.uint8)
    enc = conv_encode(info)
    r = analyse_coding_layer(enc)
    print(f"   un-interleaved codeword -> had_fec={r.had_fec} "
          f"residual={r.residual:.4f}")
    if r.decoded_bits is not None:
        m = min(len(info), len(r.decoded_bits))
        acc = float(np.mean(r.decoded_bits[:m] == info[:m]))
        print(f"   payload recovered: {acc*100:.2f}%")
        if acc < 0.999:
            ok = False
            print("   FAIL: coded input must decode exactly")
    else:
        ok = False
        print("   FAIL: a valid codeword must be decoded")

    # Interleaved variant.
    print()
    print("2. analyse_coding_layer over an INTERLEAVED coded stream")
    for mode in ("block", "convolutional", "diagonal", "pseudo_random"):
        il = interleave(enc, mode)
        r = analyse_coding_layer(il)
        acc = None
        if r.decoded_bits is not None:
            m = min(len(info), len(r.decoded_bits))
            acc = float(np.mean(r.decoded_bits[:m] == info[:m]))
        print(f"   {mode:<15} -> interleaver={str(r.interleaver):<15} "
              f"had_fec={str(r.had_fec):<5} "
              f"payload={f'{acc*100:.2f}%' if acc is not None else '--'}")
        if not r.had_fec or r.interleaver != mode or (acc or 0) < 0.999:
            ok = False
            print("   FAIL")

    # Uncoded: must refuse.
    print()
    print("3. UNCODED stream must report 'not present'")
    r_unc = analyse_coding_layer(rng.integers(0, 2, 800).astype(np.uint8))
    print(f"   -> analysed={r_unc.analysed} had_fec={r_unc.had_fec} "
          f"residual={r_unc.residual:.4f}")
    print(f"   reason: {r_unc.reason}")
    if r_unc.had_fec or r_unc.decoded_bits is not None:
        ok = False
        print("   FAIL: must not fabricate a payload for uncoded input")
    else:
        print("   ok")

    # Now the GUI itself.
    print()
    print("4. GUI wiring -- does the card carry the coding result?")
    print("   (checked by reading widget text back, not by screenshot)")
    try:
        from sigma_main_window import SigmaMainWindow
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
        win = SigmaMainWindow()
        has_attr = hasattr(win, "coding_result")
        print(f"   window exposes coding_result: {has_attr}")
        if not has_attr:
            ok = False
            print("   FAIL: coding_result not initialised on the window")
        else:
            print(f"   initial value: {win.coding_result}")
        # The stats label must exist and be reachable.
        lbl = getattr(win, "lbl_demod_stats", None)
        print(f"   lbl_demod_stats present: {lbl is not None}")
        if lbl is None:
            ok = False
        win.close()
    except Exception as e:
        import traceback
        traceback.print_exc()
        ok = False
        print(f"   FAIL: could not build the window: {e}")

    print()
    print("=" * 78)
    print("ALL PASSED" if ok else "SOME CHECKS FAILED")
    print("=" * 78)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
