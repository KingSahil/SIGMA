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
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = [
    "verify_symbol_rate.py",
    "verify_demod.py",
    "verify_wide.py",
]


def main():
    for name in SCRIPTS:
        path = os.path.join(HERE, name)
        print("\n" + "=" * 78)
        print(f"RUNNING {name}")
        print("=" * 78)
        r = subprocess.run([sys.executable, path], cwd=HERE)
        if r.returncode != 0:
            print(f"!! {name} exited with code {r.returncode}")


if __name__ == "__main__":
    main()
