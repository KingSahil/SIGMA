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
verify_interleaver_detect.py  NAMES the interleaver blind, using the
                              decode -> re-encode residual as a codeword test.
                              4/4 clean, 4/4 to 10% channel errors, 0/4 on
                              random bits, with the failure boundary measured
                              and reported. Also records two dead ends (a
                              hand-fitted statistic, and a syndrome that
                              wrongly assumed the code was systematic).
verify_coding_module.py       scores the SHIPPED module (src/sigma_coding.py)
                              rather than a scratch copy. Includes the safety
                              property -- uncoded input must be REFUSED -- and
                              the geometry-blind detection check that exposed
                              a single-guess factorisation bug scoring 2/4.
verify_coding_gui.py          the coding layer through the real window, with
                              widget text read back rather than screenshotted.

Added for PS section 3 (v), bitstream correlation / header detection:
header_ground_truth.py        the sync-word search and the CHANCE THRESHOLD
                              that decides whether a correlation peak means
                              anything. Records that detection is a property
                              of (pattern length, stream length): a 16-bit word
                              is decidable in 400 bits but NOT in 20,000, and
                              that an earlier gate requiring "better than
                              chance" was unsatisfiable and detected nothing.

verify_provenance_label.py    the modulation card must report a SOURCE, not a
                              confidence. Reads the label text back for all
                              four provenance strings and confirms the genuine
                              confidence figure (EVM) is still shown in the
                              demod card.

Added for PS section 3 (i), blind FEC-scheme identification:
fec_scheme_search.py          the ground-truth experiment. Recovers five
                              standard rate-1/2 codes from their own encodings,
                              establishes the margin over the runner-up, and
                              -- crucially -- measures that a BARE argmin claims
                              a scheme for 12/12 random streams while the
                              thresholded search claims 0/12.
verify_scheme_search.py       the same properties against the SHIPPED module and
                              the GUI, plus the fast path's blind spot
                              (non-default code + interleaver = 0/16) and the
                              deep search that closes it (16/16 for K<=7).

NOTE: verify_scheme_search.py section 4 runs a joint code x interleaver search
and takes ~80 s on its own. That is deliberate -- it is the measurement that
justifies the deep search existing.

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
    "header_ground_truth.py",
    "verify_interleaver_detect.py",
    "verify_coding_module.py",
    "verify_coding_gui.py",
    "verify_provenance_label.py",
    "fec_scheme_search.py",
    "verify_scheme_search.py",
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
