"""Verify digital demodulation: does it recover the ACTUAL transmitted bits?

This is the definitive test. We generate a signal from known random bits,
demodulate it, and count how many bits came back correctly. An estimator that
"locks" but produces wrong bits is worthless, so we check bit accuracy
directly, not just lock status.
"""
import numpy as np
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from sigma_symbol_rate import estimate_symbol_rate
from sigma_demod import demodulate, rrc_filter, format_bitstream_summary

FS = 1_000_000


def make_known_signal(symbol_rate, modulation, alpha=0.35, n_symbols=2000, seed=7):
    """Build a pulse-shaped signal AND return the symbols that made it."""
    rng = np.random.default_rng(seed)
    sps = int(round(FS / symbol_rate))

    if modulation == "BPSK":
        bits = rng.integers(0, 2, n_symbols)
        sym = (bits * 2 - 1).astype(np.complex128)
        expected_bits = bits
    elif modulation == "QPSK":
        # Build symbols from constellation INDEX, matching the demodulator's
        # `const` array order: index 0 -> (0,0), 1 -> (0,1), 2 -> (1,0),
        # 3 -> (1,1). Deriving symbols from independent random bits instead
        # would impose a different labelling convention and make a correct
        # demodulator look wrong.
        const = np.array([1 + 1j, -1 + 1j, -1 - 1j, 1 - 1j]) / np.sqrt(2)
        idx = rng.integers(0, 4, n_symbols)
        sym = const[idx]
        expected_bits = np.empty(n_symbols * 2, dtype=np.uint8)
        expected_bits[0::2] = (idx >> 1) & 1
        expected_bits[1::2] = idx & 1
    else:
        raise ValueError(modulation)

    up = np.zeros(n_symbols * sps, dtype=np.complex128)
    up[::sps] = sym
    h = rrc_filter(sps, alpha)
    shaped = np.convolve(up, h, mode="same")

    t = np.arange(len(shaped)) / FS
    shaped *= np.exp(1j * 2 * np.pi * 60_000 * t)

    rng2 = np.random.default_rng(seed + 1)
    noise = (rng2.normal(0, 1, len(shaped))
             + 1j * rng2.normal(0, 1, len(shaped))) * 0.02
    out = shaped + noise
    out = out / np.max(np.abs(out)) * 0.9
    return out.astype(np.complex64), sps, expected_bits, sym


def best_bit_alignment(recovered, expected, modulation="BPSK"):
    """Compare bit streams allowing for unknown start offset and rotation.

    A demodulator cannot know which symbol is first, and for a symmetric
    constellation (BPSK's 180 degrees, QPSK's 90 degrees) it also cannot know
    the absolute phase. Both are conventionally resolved later by a preamble
    correlator. Here we search the rotation and offset so we score the
    demodulator itself rather than the missing framer.

    For QPSK the rotation applies per-symbol-index (a 2-bit group), not per
    bit, so the search operates on symbol indices for multi-bit modulations.
    """
    if recovered is None or len(recovered) == 0:
        return 0.0, 0, 0

    n = min(len(recovered), len(expected))
    if n < 16:
        return 0.0, 0, 0

    bps = {"BPSK": 1, "QPSK": 2, "8PSK": 3, "16QAM": 4}.get(modulation, 1)
    n_sym = 2 if bps == 1 else (4 if bps == 2 else (8 if bps == 3 else 16))

    rec = recovered[:n].astype(np.int64)
    exp = expected[:n].astype(np.int64)

    # Group into symbol indices so a rotation can be applied coherently.
    n_groups = n // bps
    if n_groups < 8:
        return 0.0, 0, 0

    rec_idx = np.zeros(n_groups, dtype=np.int64)
    exp_idx = np.zeros(n_groups, dtype=np.int64)
    for g in range(n_groups):
        for b in range(bps):
            rec_idx[g] = (rec_idx[g] << 1) | rec[g * bps + b]
            exp_idx[g] = (exp_idx[g] << 1) | exp[g * bps + b]

    best_acc, best_off, best_rot = 0.0, 0, 0
    for rot in range(n_sym):
        rotated = (rec_idx + rot) % n_sym
        for off in range(0, min(64, n_groups - 16)):
            span = n_groups - off
            if span < 16:
                break
            acc = np.mean(rotated[off:off + span] == exp_idx[:span])
            if acc > best_acc:
                best_acc, best_off, best_rot = acc, off, rot
    return best_acc, best_off * bps, best_rot


print("=" * 76)
print("DIGITAL DEMODULATION - BIT RECOVERY VERIFICATION")
print("=" * 76)

CASES = [
    (100_000, "BPSK", 0.35),
    (50_000, "QPSK", 0.35),
    (200_000, "BPSK", 0.35),
    (100_000, "QPSK", 0.35),
    (100_000, "BPSK", 0.20),
]

print(f"{'R_s':>9} {'mod':>5} {'alpha':>6} | {'detected':>10} {'bits':>6} "
      f"{'EVM':>7} {'BER':>8} {'accuracy':>9}")
print("-" * 76)

results = []
for true_rate, mod, alpha in CASES:
    sig, sps, exp_bits, _ = make_known_signal(true_rate, mod, alpha=alpha)

    # Step 1: symbol rate estimate (feeds SPS into the demodulator)
    sr = estimate_symbol_rate(sig, FS)
    detected = sr["symbol_rate_hz"] if sr["locked"] else 0.0

    # Step 2: demodulate using the DETECTED sps, not the true one.
    # This is the honest end-to-end test.
    sps_used = sr["samples_per_symbol"] if sr["locked"] else None
    d = demodulate(sig, FS, modulation=mod, sps=sps_used)

    if not d.locked:
        print(f"{true_rate/1e3:>8.1f}k {mod:>5} {alpha:>6.2f} | "
              f"{detected/1e3:>9.2f}k {'--':>6} {'--':>7} {'--':>8} "
              f"{'NO LOCK: ' + d.reason[:20]:>9}")
        results.append(None)
        continue

    acc, off, inv = best_bit_alignment(d.bits, exp_bits, mod)
    ber = 1.0 - acc
    results.append(acc)

    print(f"{true_rate/1e3:>8.1f}k {mod:>5} {alpha:>6.2f} | "
          f"{detected/1e3:>9.2f}k {len(d.bits):>6} "
          f"{d.evm_percent:>6.1f}% {ber:>8.4f} {acc*100:>8.2f}%")

print("-" * 76)
good = [r for r in results if r is not None]
if good:
    print(f"demodulated: {len(good)}/{len(results)}   "
          f"mean bit accuracy: {np.mean(good)*100:.2f}%   "
          f"best: {np.max(good)*100:.2f}%   worst: {np.min(good)*100:.2f}%")
else:
    print("NOTHING DEMODULATED")
print("=" * 76)

# Show an actual recovered bitstream against the truth
print("\nWorked example - recovered vs transmitted bits:")
sig, sps, exp_bits, _ = make_known_signal(100_000, "BPSK", alpha=0.35, n_symbols=200)
sr = estimate_symbol_rate(sig, FS)
d = demodulate(sig, FS, modulation="BPSK", sps=sr["samples_per_symbol"])
if d.locked:
    acc, off, inv = best_bit_alignment(d.bits, exp_bits, mod)
    n_show = 40
    print(f"  transmitted : {''.join(str(int(b)) for b in exp_bits[:n_show])}")
    print(f"  recovered   : {''.join(str(int(b)) for b in d.bits[off:off+n_show])}"
          f"   (offset {off}, inverted={inv})")
    print(f"  match over {min(len(d.bits)-off, len(exp_bits))} bits: {acc*100:.2f}%")
