"""Does the GUI gate decode a real 2-FSK capture, and what blocks it if not?

WHAT THIS FOUND
---------------
The gate does NOT reach the FSK estimator for a real 2-FSK capture. It stops
earlier, at "NO CLOCK", because the SYMBOL RATE estimator returns no lock.

The reason is structural and now measured. `estimate_symbol_rate` looks for a
periodic feature in the signal ENVELOPE (`env = np.abs(x) ** 2`, per its own
comment: "Pulse shaping modulates this slightly once per symbol"). 2-FSK is
CONSTANT-ENVELOPE, so there is no envelope periodicity for it to find. Measured:

    2-FSK 100 ksps  ->  symbol_rate_hz 0.0    locked False   confidence NONE
    BPSK  100 ksps  ->  symbol_rate_hz 99997  locked True    confidence HIGH (31.3 dB)

So the FSK demodulator cannot be reached through the GUI until the symbol rate
is obtainable for a constant-envelope signal. That is a real, unmeasured gap
that this test surfaced -- and it is recorded rather than worked around,
because faking a symbol rate would put a fabricated number in the pipeline.

WHAT IS STILL WORTH ASSERTING
-----------------------------
1. The module-level FSK path works (scored in scratch/verify_fsk_demod.py).
2. The gate does not NOT crash and gives an honest, stated reason for a 2-FSK
   capture -- a lock it cannot justify is the failure mode to prevent.
3. A BPSK capture carrying an FSK label is still decoded as BPSK and NOT as
   2-FSK. This is the false-positive control, and it passes today.
4. The block is the SYMBOL RATE stage, not the FSK estimator. This is asserted
   explicitly so that when the symbol-rate gap is fixed, this test FAILS and
   points at the change rather than silently passing forever.

Run with the interpreter the app uses (Radioconda):
    <radioconda>/python.exe scratch/verify_fsk_gui.py
"""
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, HERE)

from PyQt5 import QtWidgets
from sigma_main_window import SigmaMainWindow
from sigma_symbol_rate import estimate_symbol_rate

app = QtWidgets.QApplication(sys.argv)

# Anchored to the repo root, NOT the current directory. run_all.py executes each
# suite with cwd=scratch/, so a cwd-relative "data/..." resolves to
# scratch/data/... and the file is not found. That made this suite pass when run
# by hand from the repo root and fail inside the runner -- the same script
# behaving differently in two invocation styles is a bug in the test, not in the
# code under test.
FSK = os.path.join(ROOT, "data", "iq", "gui_test_2fsk_100ksps_1msps.iq")
FSK_NARROW = os.path.join(ROOT, "data", "iq",
                          "gui_test_2fsk_narrow_100ksps_1msps.iq")
BPSK = os.path.join(ROOT, "data", "iq", "demo_bpsk_100ksps_1msps.iq")
FS = 1_000_000

fails = []


def read_capture(path):
    import numpy as np
    return np.fromfile(path, dtype=np.complex64)


print("=" * 100)
print("FSK THROUGH THE REAL GUI GATE")
print("=" * 100)
print()

# ---------------------------------------------------------------------------
print("1. THE ACTUAL BLOCKER, measured at the module boundary")
print("-" * 100)
fsk_samples = read_capture(FSK)
bpsk_samples = read_capture(BPSK)

sr_fsk = estimate_symbol_rate(fsk_samples, FS)
sr_bpsk = estimate_symbol_rate(bpsk_samples, FS)
print(f"  symbol rate on 2-FSK : locked={sr_fsk['locked']}  "
      f"R_s={sr_fsk['symbol_rate_hz']:.0f}  "
      f"confidence={sr_fsk['confidence_label']}")
print(f"  symbol rate on BPSK  : locked={sr_bpsk['locked']}  "
      f"R_s={sr_bpsk['symbol_rate_hz']:.0f}  "
      f"confidence={sr_bpsk['confidence_label']} "
      f"({sr_bpsk['prominence_db']:.1f} dB)")
print()
if sr_fsk["locked"]:
    print("  The symbol rate estimator NOW locks 2-FSK. The gap this test was")
    print("  written to record has been closed -- update this test and the docs.")
    fails.append(("symbol-rate-gap-closed", "R_s locked on 2-FSK", "", "", ""))
else:
    print("  CONFIRMED BLOCKER: the symbol rate estimator cannot clock a")
    print("  constant-envelope signal, so the gate stops at NO CLOCK before the")
    print("  FSK estimator is ever reached. Structural, not a tuning issue:")
    print("  the estimator reads the ENVELOPE, and 2-FSK's envelope is flat.")

# ---------------------------------------------------------------------------
print()
print("2. THE FSK ESTIMATOR ITSELF -- does it see the capture correctly?")
print("-" * 100)
from sigma_demod import estimate_fsk, demodulate_fsk
est = estimate_fsk(fsk_samples)
print(f"  estimate_fsk: is_two_tone={est['is_two_tone']}  "
      f"separation={est['separation']:.4f}  "
      f"unexplained={est['unexplained']:.4f}")
print(f"    {est['reason']}")
if not est["is_two_tone"]:
    fails.append(("estimator-missed-real-2fsk", FSK, "not two-tone", "two-tone", ""))
    print("  FAIL the estimator did not recognise a real 2-FSK capture")
else:
    print("  ok   the estimator recognises it; only the CLOCK is missing")

# With the true sps supplied, the demodulator should work -- proving the
# block is upstream and the demodulator itself is sound.
res = demodulate_fsk(fsk_samples, FS, fsk=est, sps=10)
print(f"  demodulate_fsk with the TRUE sps=10: "
      f"{'LOCKED' if res.locked else 'DECLINED'} "
      f"({res.n_symbols if res.locked else 0} symbols)")
if not res.locked:
    fails.append(("demod-failed-with-true-sps", FSK, res.reason, "locked", ""))
    print(f"  FAIL demodulator declined even with the correct clock: {res.reason}")
else:
    print("  ok   the demodulator works when given a clock -- so the block is")
    print("       entirely the symbol-rate stage, not the FSK path")

# ---------------------------------------------------------------------------
print()
print("3. THROUGH THE REAL GUI GATE -- honest reasons, no unjustified locks")
print("-" * 100)


def probe(path, label, expect_not_locked_as):
    w = SigmaMainWindow(initial_file=path)
    w.metadata.modulation_class = label
    w.metadata.modulation_source = "measured"
    w._run_demod_stage()
    state = w.lbl_demod_state.text()
    detail = (w.lbl_demod_method.text() if state == "LOCKED"
              else w.lbl_demod_reason.text())
    bad = False
    if state == "LOCKED" and expect_not_locked_as in detail:
        bad = True
        fails.append((label, os.path.basename(path), state,
                      f"not {expect_not_locked_as}", detail))
    elif not detail.strip():
        bad = True
        fails.append((label, os.path.basename(path), state, "a stated reason", ""))
    print(f"  {'FAIL' if bad else 'ok  '} {label:18s} -> {state:10s} {detail[:52]}")
    w.close()
    return state, detail


probe(FSK, "BPSK / 2-FSK", "2-FSK")
probe(FSK, "Digital PSK/FSK", "2-FSK")
probe(FSK_NARROW, "BPSK / 2-FSK", "2-FSK")

print()
print("  False-positive control -- an FSK label on a BPSK capture:")
state, detail = probe(BPSK, "BPSK / 2-FSK", "2-FSK")
if state == "LOCKED" and "BPSK" in detail:
    print("    ok   decoded as BPSK, NOT as 2-FSK -- the estimator refused it")
else:
    print(f"    note state={state} detail={detail[:60]}")

print()
print("=" * 100)
if fails:
    print(f"{len(fails)} CHECK(S) DID NOT HOLD:")
    for f in fails:
        print(f"  {f}")
else:
    print("ALL FSK GUI CHECKS PASSED")
print()
print("STATUS: FSK demodulation works at the module level (scratch/verify_fsk_demod.py,")
print("99.99% mean bit accuracy) but is NOT reachable through the GUI, because the")
print("symbol rate estimator cannot clock a constant-envelope signal. That is the")
print("next blocker, and it is upstream of everything FSK-related.")
print("=" * 100)
sys.exit(1 if fails else 0)

