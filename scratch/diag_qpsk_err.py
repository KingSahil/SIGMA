"""Which QPSK bit is wrong, I or Q?"""
import numpy as np, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))
import sigma_demod as sd
from verify_demod import make_known_signal, FS

sig, sps, exp, sym = make_known_signal(50_000, "QPSK", alpha=0.35, n_symbols=300)
const = np.array([1+1j,-1+1j,-1-1j,1-1j])/np.sqrt(2)
d = sd.demodulate(sig, FS, modulation="QPSK", sps=float(sps))
print("locked:", d.locked, "EVM:", d.evm_percent)

# tx symbol indices
tx = np.argmin(np.abs(np.array(sym[:d.n_symbols])[:,None]-const[None,:]),axis=1)
# demod symbol indices
rx = np.argmin(np.abs(d.symbols[:,None]-const[None,:]),axis=1)
print("\nconstellation index mapping (tx -> rx):")
for t in range(4):
    m = tx==t
    if m.sum():
        vals, cnts = np.unique(rx[m], return_counts=True)
        print(f"  tx idx {t} -> " + ", ".join(f"{v}({c})" for v,c in zip(vals,cnts)))
# is it a constant permutation?
print("\nfirst 20 tx idx:", tx[:20])
print("first 20 rx idx:", rx[:20])
