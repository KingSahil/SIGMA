"""Is there ANY absolute frequency reference in the signal?

Key question for sample-rate estimation: every frequency we measure from the
samples is in *normalised* units (cycles/sample). Multiply by an assumed f_s
and you get Hz. So without a known reference, f_s and R_s are inseparable
from the data alone -- UNLESS there is a known absolute feature.

Candidates for an absolute reference:
  a) A known protocol's symbol rate (GSM 270.833 ksps, DVB 27.5 Msps...)
  b) A known pilot tone / carrier standard
  c) The data itself declaring the rate

What we CAN do without a reference: report SPS exactly (normalised, needs no
f_s), and report R_s in "cycles/sample" -- then convert only when told f_s.

Let's measure how precisely SPS is known, since that is the f_s-free quantity.
"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
from make_ground_truth import make_signal
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from sigma_symbol_rate import estimate_symbol_rate as est

FS = 1_000_000.0
print(f"{'true Rs':>8} {'true SPS':>9} | {'meas SPS':>9} {'SPS err':>8} | {'normalised R_s':>15}")
print("-" * 62)
sps_errs = []
for rs in (25_000, 50_000, 100_000, 200_000, 250_000):
    for alpha in (0.35, 0.50):
        sig, true_sps = make_signal(rs, "bpsk", alpha=alpha, n_symbols=6000, seed=7)
        r = est(sig, FS)
        if not r.get("locked"):
            print(f"{rs/1e3:7.0f}k {true_sps:9.0f} |   (no lock)")
            continue
        m = r["samples_per_symbol"]
        e = (m - true_sps) / true_sps * 100
        sps_errs.append(abs(e))
        print(f"{rs/1e3:7.0f}k {true_sps:9.0f} | {m:9.3f} {e:+7.2f}% | "
              f"{1.0/m:15.6f}")
print("-" * 62)
if sps_errs:
    print(f"cases {len(sps_errs)}  mean |SPS error| {np.mean(sps_errs):.3f}%  "
          f"max {np.max(sps_errs):.3f}%")
