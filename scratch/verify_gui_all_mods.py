"""End-to-end GUI verification across all four modulations.

Reads the REAL widgets after running the REAL pipeline, rather than eyeballing a
screenshot: a screenshot proves pixels were painted, not that the values are
right. For each modulation it writes a capture with a known symbol rate, loads
it through SigmaMainWindow, lets the whole pipeline run, and asserts the DEMOD
card reports the right constellation.

It also checks the refusal path still works, and that the panel shows the
measured values (EVM, carrier offset, residual, SPS) rather than just a tick.

Geometry is NOT asserted here: the offscreen dummy screen is 800x600, which
distorts sizeHint() badly. Only widget TEXT is asserted.
"""
import os
import sys

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from PyQt5 import QtWidgets
from sigma_main_window import SigmaMainWindow
from verify_demod_all_mods import make_known, FS

OUT = os.path.join(ROOT, "data", "iq")
os.makedirs(OUT, exist_ok=True)

app = QtWidgets.QApplication(sys.argv)
fails = []

print("=" * 84)
print("END-TO-END GUI CHECK - real pipeline, real widgets")
print("=" * 84)

for mod in ("BPSK", "QPSK", "8PSK", "16QAM"):
    fname = f"gui_test_{mod.lower()}_100ksps_1msps.iq"
    path = os.path.join(OUT, fname)
    sig, sps, idx, const = make_known(mod, 100_000, seed=11, n_symbols=2000)
    sig.tofile(path)

    w = SigmaMainWindow(initial_file=path)
    w._update_all_displays()
    app.processEvents()

    state = w.lbl_demod_state.text()
    method = w.lbl_demod_method.text()
    stats = w.lbl_demod_stats.text()
    reason = w.lbl_demod_reason.text()
    tooltip = w.lbl_demod.toolTip()

    ok = (state == "LOCKED") and (mod in method)
    if not ok:
        fails.append((mod, state, method, reason))
    print(f"\n{mod}:")
    print(f"  file          : {fname}")
    print(f"  DEMOD state   : {state}")
    print(f"  method        : {method}")
    print(f"  reason        : {reason if reason else '(hidden - success)'}")
    print(f"  stats         : {stats.replace(chr(10), ' | ')}")
    print(f"  tooltip       : {tooltip}")
    print(f"  => {'ok' if ok else 'FAIL'}")

    # The measured values must actually be on screen, not just a tick mark.
    for token in ("EVM:", "Carrier offset:", "Residual tracked:", "SPS used:"):
        if token not in stats:
            fails.append((mod, "missing stat", token, ""))
            print(f"  MISSING STAT: {token}")
    w.close()

# ---------------------------------------------------------------------------
print()
print("=" * 84)
print("REFUSAL PATH - the gate must still decline what it cannot slice")
print("=" * 84)
# Use a genuine unmodulated carrier. Testing this with a modulated file and a
# forced "CW" label would only prove the label was ignored -- the classifier
# would read the real constellation out of the samples, which is the point.
cw_path = os.path.join(OUT, "gui_test_cw_unmodulated.iq")
t = np.arange(40_000) / FS
rng = np.random.default_rng(5)
ph = rng.uniform(0, 2 * np.pi)
(0.9 * np.exp(1j * (2 * np.pi * 60_000 * t + ph))).astype(np.complex64).tofile(cw_path)
print(f"  (file is a genuine unmodulated carrier: "
      f"{os.path.basename(cw_path)})")

w = SigmaMainWindow(initial_file=cw_path)
for forced, want in (("CW / Unmodulated", "UNSUPPORTED"),
                     ("AM / ASK", "UNSUPPORTED"),
                     ("FM / RDS", "UNSUPPORTED")):
    w.metadata.modulation_class = forced
    w.metadata.modulation_confidence = "measured"
    w._run_demod_stage()
    got = w.lbl_demod_state.text()
    ok = got == want
    if not ok:
        fails.append((forced, got, want, ""))
    print(f"  {'ok  ' if ok else 'FAIL'} {forced:20s} -> {got:12s} "
          f"({w.lbl_demod_reason.text()[:52]})")
w.close()

print()
print("=" * 84)
if fails:
    print(f"{len(fails)} FAILURE(S):")
    for f in fails:
        print(f"  {f}")
else:
    print("ALL PASSED - all four modulations lock end to end, refusals hold.")
print("=" * 84)
sys.exit(1 if fails else 0)
