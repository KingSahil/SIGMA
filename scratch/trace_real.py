"""Trace the REAL demodulate() function step by step, no reimplementation."""
import numpy as np, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))
import sigma_demod as sd
from verify_demod import make_known_signal, FS

# monkeypatch to trace internals
sig, sps, exp, sym = make_known_signal(50_000, "QPSK", alpha=0.35, n_symbols=400)
print("true sps:", sps)

# call the real function with the TRUE sps first (isolate sps error from the rest)
res = sd.demodulate(sig, FS, modulation="QPSK", sps=float(sps))
print("\nwith TRUE sps:")
print("  locked:", res.locked, " reason:", res.reason)
print("  EVM:", res.evm_percent, " n_sym:", res.n_symbols)
print("  carrier off:", res.carrier_offset_hz)

if res.symbols is not None:
    a = np.degrees(np.angle(res.symbols[:16]))
    print("  symbol angles:", np.round(a,1))
    print("  distinct 45-deg buckets:", len(np.unique(np.round(a/45))))

# now with detected sps
from sigma_symbol_rate import estimate_symbol_rate
sr = estimate_symbol_rate(sig, FS)
print(f"\ndetected sps: {sr['samples_per_symbol']:.4f}")
res2 = sd.demodulate(sig, FS, modulation="QPSK", sps=sr["samples_per_symbol"])
print("with DETECTED sps:")
print("  locked:", res2.locked, " reason:", res2.reason)
print("  EVM:", res2.evm_percent)
if res2.symbols is not None:
    a2 = np.degrees(np.angle(res2.symbols[:16]))
    print("  symbol angles:", np.round(a2,1))
