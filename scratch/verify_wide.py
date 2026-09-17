"""Wider sweep to check the result holds across many configurations."""
import numpy as np, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))
from sigma_symbol_rate import estimate_symbol_rate
from sigma_demod import demodulate
from verify_demod import make_known_signal, best_bit_alignment, FS

print(f"{'R_s':>8} {'mod':>5} {'alpha':>6} {'seed':>5} | {'detected':>10} {'EVM':>7} {'accuracy':>9}")
print("-"*66)
accs=[]
for mod in ["BPSK","QPSK"]:
    for rate in [25_000, 50_000, 100_000, 200_000, 250_000]:
        for alpha in [0.20, 0.35, 0.50]:
            for seed in [7, 99]:
                sig, sps, exp, sym = make_known_signal(rate, mod, alpha=alpha,
                                                        n_symbols=600, seed=seed)
                sr = estimate_symbol_rate(sig, FS)
                if not sr["locked"]:
                    print(f"{rate/1e3:>7.0f}k {mod:>5} {alpha:>6.2f} {seed:>5} | NO LOCK")
                    continue
                d = demodulate(sig, FS, modulation=mod, sps=sr["samples_per_symbol"])
                if not d.locked:
                    print(f"{rate/1e3:>7.0f}k {mod:>5} {alpha:>6.2f} {seed:>5} | "
                          f"{sr['symbol_rate_hz']/1e3:>9.1f}k {'--':>7}  NO DEMOD")
                    continue
                acc,_,_ = best_bit_alignment(d.bits, exp, mod)
                accs.append(acc)
                flag = "" if acc>0.999 else "  <<<"
                print(f"{rate/1e3:>7.0f}k {mod:>5} {alpha:>6.2f} {seed:>5} | "
                      f"{sr['symbol_rate_hz']/1e3:>9.2f}k {d.evm_percent:>6.1f}% "
                      f"{acc*100:>8.2f}%{flag}")
print("-"*66)
if accs:
    a=np.array(accs)
    print(f"cases: {len(a)}   perfect(100%): {(a>0.999).sum()}   "
          f"mean: {a.mean()*100:.2f}%   min: {a.min()*100:.2f}%")
