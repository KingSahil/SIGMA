"""
SIGMA verification harness -- symbol rate estimation and digital demodulation.

Run all three checks with:

    <python> scratch/run_all.py

Requires: numpy.  Does NOT require GNU Radio / Radioconda, since the DSP
modules under test are pure numpy.

These scripts generate signals with KNOWN symbol rates, because without a
ground-truth reference there is no way to tell a correct estimate from a
plausible-looking wrong one.

Files
-----
make_ground_truth.py    generates RRC-pulse-shaped signals with known rates
verify_symbol_rate.py   scores the estimator against those known rates
verify_demod.py         scores recovered bits against the transmitted bits
verify_wide.py          sweeps many configurations (rates x alpha x seeds)
diag_qpsk_err.py        proves the QPSK constellation-index mapping is correct
diag_score_select.py    evidence that ISI-null scoring is WORSE than taking
                        the strongest spectral bin -- keep as a record of a
                        rejected approach, do not "re-fix" this

Added for the four-constellation work (BPSK/QPSK/8PSK/16QAM):
verify_demod_all_mods.py      demodulation scored per modulation over a sweep
verify_modclass_parsimony.py  the constellation classifier, 144 cases
verify_no_symbols_guard.py    proves CW and ASK are refused, not fitted
verify_analogue_refused.py    proves real FM/RDS, AM, ASK, audio are refused
verify_demod_gate.py          the GUI gate resolves a label to a constellation
verify_gui_all_mods.py        end-to-end GUI, all four modulations, real widgets

Added for the coding layer (PS section 3 iii / iv):
fec_ground_truth.py           convolutional encode/decode + the four
                              interleaver modes, with invertibility and
                              burst-error proofs. Also asserts the trellis
                              invariant that a reverse-from-bit traceback is
                              impossible -- see the note in the file.

The last three need PyQt5 (they set QT_QPA_PLATFORM=offscreen themselves).
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = [
    "verify_symbol_rate.py",
    "verify_demod.py",
    "verify_wide.py",
    "verify_demod_all_mods.py",
    "verify_modclass_parsimony.py",
    "verify_no_symbols_guard.py",
    "verify_analogue_refused.py",
    "verify_demod_gate.py",
    "verify_gui_all_mods.py",
    "fec_ground_truth.py",
]


def main():
    failed = []
    for name in SCRIPTS:
        path = os.path.join(HERE, name)
        print("\n" + "=" * 78)
        print(f"RUNNING {name}")
        print("=" * 78)
        r = subprocess.run([sys.executable, path], cwd=HERE)
        if r.returncode != 0:
            print(f"!! {name} exited with code {r.returncode}")
            failed.append(name)

    print("\n" + "=" * 78)
    if failed:
        print(f"{len(failed)} SUITE(S) FAILED: {', '.join(failed)}")
    else:
        print(f"ALL {len(SCRIPTS)} SUITES PASSED")
    print("=" * 78)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
