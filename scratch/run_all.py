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

Added for PS section 3 (ii), FSK -- these are PROBES, not verification suites.
They are in this list because they run and exit 0, and because the negative
results they record are the reason no classifier change was made. Read them
before proposing a feature for BPSK/2-FSK:

probe_fsk_vs_bpsk.py          the FIRST attempt, and the record of its own
                              invalidity. Claimed BPSK and 2-FSK share the
                              classifier's branch signature; REFUTED -- a
                              properly built BPSK has amp_std 0.40-0.51, far
                              from the 0.12 gate.
probe_fsk_feature_space.py    rate x modulation-index x seed sweep. Found the
                              real problem: f_std ranges OVERLAP completely
                              (BPSK 0.47..1.38, 2-FSK 0.05..1.26) because f_std
                              is monotone in the modulation index.
probe_fsk_phase_shape.py      two-tone separation vs phase noise floor. FAILED
                              twice over: overlap at every rate/noise, and the
                              statistic was QUANTISED to the histogram bin
                              width (reported pi/20, pi/10, pi/5 exactly).
probe_fsk_tone_fit.py         two-tone goodness-of-fit. Failed at the NOISE
                              LEVELS IT TESTED (0.10/0.25 are 12-60 dB above
                              this project's operating point) and its controls
                              called QPSK two-tone.
probe_fsk_snr_realistic.py    the retest at the project's ACTUAL operating
                              point (~26-29 dB SNR). This one WORKS: 2-FSK
                              unexplained share 0.0000..0.2008, every control
                              0.3488..1.0000, and the measured tone spacing
                              tracks the true spacing across the whole sweep.
                              Establishes the candidate threshold and the
                              reference implementation the classifier would use.

probe_phase_clock.py          WHY the phase-domain clock fallback fails.
                              2-FSK built as an exact two-tone sequence has
                              |d_phase| std = 0.0000 -- an INVARIANT number,
                              the fingerprint of a structural bug, not a
                              statistical one. Its mean-subtracted square is
                              identically zero, so the fallback measures
                              floating-point noise.
probe_phase_clock2.py         the two CPFSK constructions side by side, and the
                              WRONG LOCKS they produce. Half-sps construction,
                              h=2, locks at the SECOND HARMONIC (199999 Hz for a
                              true 100000 Hz) at 191.5 dB. A wrong lock is
                              worse than a refusal, so this alone disqualified
                              the fallback.
probe_phase_clock3.py         where the phase-domain peak actually sits. It is
                              NOT at R_s: measured at 3*R_s, 5*R_s and 15*R_s
                              across the sweep, surviving the 3 dB
                              sub-harmonic test only when a divisor happens to
                              fall inside it. This is the measurement that
                              decided the REVERT, documented so nobody tries
                              this statistic again without reading it first.

Added for PS section 3 (ii), FSK -- the SHIPPED demodulator:

verify_fsk_demod.py           scores src/sigma_demod.py: estimate_fsk() and
                              demodulate_fsk() against KNOWN transmitted bits.
                              15/15 2-FSK accepted, 6/6 controls refused,
                              19/19 demodulated at 99.99% mean bit accuracy,
                              and the reported tone spacing checked against the
                              true spacing (mean error 0.00692 rad/sample).
                              Also contains the BPSK-vs-2-FSK feature table that
                              refutes the "the rule cannot separate them" claim.
verify_fsk_gui.py             the FSK path through the REAL GUI gate. Asserts
                              the CURRENT, honest state: the FSK label is
                              produced, but the symbol rate estimator cannot
                              clock a constant-envelope signal, so the gate
                              stops at NO CLOCK before the FSK estimator runs.
                              It FAILS LOUDLY if that gap ever closes without
                              this file being updated, so it records a real
                              limitation rather than quietly passing forever.

Added for PS section 3 (ii), FSK -- these are PROBES, not verification suites.
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
    "probe_fsk_vs_bpsk.py",
    "probe_fsk_feature_space.py",
    "probe_fsk_phase_shape.py",
    "probe_fsk_tone_fit.py",
    "probe_fsk_snr_realistic.py",
    "verify_fsk_demod.py",
    "verify_fsk_gui.py",
    "probe_phase_clock.py",
    "probe_phase_clock2.py",
    "probe_phase_clock3.py",
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
