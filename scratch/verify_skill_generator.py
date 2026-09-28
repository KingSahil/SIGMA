"""Verify the ground-truth generator inside the dsp-ground-truth-verification
skill actually produces samples whose expected bits belong to them.

Runs the skill's REAL code block (extracted from SKILL.md, not retyped), so we
are testing the shipped helper rather than a copy of it.

The property under test: make_known_signal() returns (sig, sps, expected, sym)
where `expected` is the bit sequence that `sig` actually carries. If symbols are
drawn twice from differently-seeded rngs, this fails and every downstream score
comes back ~50%, which reads as a demodulator bug that is not one.
"""
import os
import re
import sys

import numpy as np

SKILL = os.path.join(
    os.path.expanduser("~"),
    ".workbuddy-ai", "skills", "dsp-ground-truth-verification", "SKILL.md")

src = open(SKILL, encoding="utf-8").read()
blocks = re.findall(r"```python\n(.*?)```", src, flags=re.S)
assert blocks, "no python block found in SKILL.md"

ns = {"np": np}
exec(compile(blocks[0], "SKILL.md:block0", "exec"), ns)

make_signal = ns["make_signal"]
make_known_signal = ns["make_known_signal"]
rrc_filter = ns["rrc_filter"]
CONSTELLATIONS = ns["CONSTELLATIONS"]
constellation_index_to_bits = ns["constellation_index_to_bits"]

CARRIER = 60_000.0          # make_known_signal's default offset
SAMP_RATE = 1_000_000


def recover_symbols(sig, sps, alpha, n_symbols, ref, carrier=CARRIER):
    """Undo the known carrier offset, matched-filter, search the symbol phase."""
    t = np.arange(len(sig)) / SAMP_RATE
    x = sig * np.exp(-1j * 2 * np.pi * carrier * t)
    mf = np.convolve(x, rrc_filter(sps, alpha), mode="same")
    best = None
    for off in range(sps):
        cand = mf[off::sps][:n_symbols]
        if len(cand) < n_symbols:
            continue
        # scale-invariant similarity to the transmitted symbols
        score = abs(np.vdot(cand, ref)) / (np.linalg.norm(cand) + 1e-12)
        if best is None or score > best[0]:
            best = (score, cand.copy())
    return best[1]


print("=" * 78)
print("CONSTELLATION TABLE (order = rotational symmetry order, not point count)")
print("=" * 78)
for name, (order, bps, const) in CONSTELLATIONS.items():
    print(f"  {name:6s} points={len(const):3d}  bits/sym={bps}  M-th-power order={order}")

print()
print("=" * 78)
print("GROUND-TRUTH ALIGNMENT  (expected bits must belong to the samples)")
print("=" * 78)

fails = []
for name, (order, bps, const) in CONSTELLATIONS.items():
    n_sym = 400
    for seed in (5, 11):
        sig, sps, expected, sym = make_known_signal(
            100_000, name, alpha=0.35, n_symbols=n_sym,
            seed=seed, samp_rate=SAMP_RATE)

        # length contract
        want = n_sym * bps
        len_ok = len(expected) == want

        # recovered symbols must match the transmitted ones
        rec = recover_symbols(sig, sps, 0.35, n_sym, sym)
        # nearest constellation point -> index -> bits
        idx = np.argmin(np.abs(rec[:, None] - const[None, :]), axis=1)
        rec_sym = const[idx]
        ser = float(np.mean(rec_sym != sym))
        # rotate away the constellation-symmetry ambiguity for a fair SER
        best_ser = ser
        for k in range(1, order):
            rot = np.exp(1j * 2 * np.pi * k / order)
            alt = const[np.argmin(np.abs((rec * rot)[:, None] - const[None, :]), axis=1)]
            best_ser = min(best_ser, float(np.mean(alt != sym)))

        # expected bits must equal the bits of `sym`
        sym_idx = np.argmin(np.abs(sym[:, None] - const[None, :]), axis=1)
        from_sym = np.array([b for i in sym_idx
                             for b in constellation_index_to_bits(int(i), bps)],
                            dtype=np.uint8)
        bits_match = np.array_equal(from_sym, expected)

        ok = len_ok and bits_match and best_ser < 0.01
        if not ok:
            fails.append((name, seed))
        print(f"  {name:6s} seed={seed:<3d} sps={sps:<3d} "
              f"expected_len={len(expected):5d}/{want:<5d} "
              f"{'ok' if len_ok else 'BAD'}  "
              f"bits_from_sym={'match' if bits_match else 'MISMATCH'}  "
              f"symbol_err={best_ser * 100:6.2f}%  "
              f"=> {'ok' if ok else 'FAIL'}")

print()
print("=" * 78)
if fails:
    print(f"FAILED: {len(fails)} case(s): {fails}")
else:
    print("ALL PASSED - every constellation's expected bits belong to its samples.")
print("=" * 78)

# ---------------------------------------------------------------------------
# Counterfactual: was the bug we fixed real, or cosmetic?
# Reproduce the old behaviour (symbols drawn from rng(seed + 1000) while the
# samples were built from rng(seed)) and score its ground truth against the
# symbols the signal actually carries.
# ---------------------------------------------------------------------------
print()
print("=" * 78)
print("COUNTERFACTUAL - the OLD generator (symbols from a second rng draw)")
print("=" * 78)
for name in ("BPSK", "QPSK", "8PSK", "16QAM"):
    order, bps, const = CONSTELLATIONS[name]
    n_sym, seed = 400, 5
    sig, sps, expected, sym = make_known_signal(
        100_000, name, alpha=0.35, n_symbols=n_sym, seed=seed, samp_rate=SAMP_RATE)

    # what the OLD code believed it had transmitted
    old_rng = np.random.default_rng(seed + 1000)
    old_idx = old_rng.integers(0, len(const), n_sym)
    old_sym = const[old_idx]
    old_expected = np.array([b for i in old_idx
                             for b in constellation_index_to_bits(int(i), bps)],
                            dtype=np.uint8)

    same = float(np.mean(old_sym == sym)) * 100.0
    n = min(len(old_expected), len(expected))
    bit_acc = float(np.mean(old_expected[:n] == expected[:n])) * 100.0
    print(f"  {name:6s} old symbols identical to real ones: {same:5.1f}%   "
          f"old ground truth vs real bits: {bit_acc:5.1f}%")
print("  -> a ground truth drawn independently matches by chance only, which is")
print("     exactly what a broken demodulator looks like. This is why the")
print("     generator must build the samples from the symbols it returns.")
print("=" * 78)
