"""Isolate the Viterbi bug: check the trellis against brute force."""
import numpy as np
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fec_ground_truth import conv_encode, viterbi_decode, DEFAULT_K, DEFAULT_POLYS

K, polys = DEFAULT_K, DEFAULT_POLYS
sb = K - 1
ns = 1 << sb
n_out = len(polys)


def emit(state, bit):
    return [bin(((bit << sb) | state) & p).count("1") & 1 for p in polys]


def nxt(state, bit):
    return ((state << 1) | bit) & (ns - 1)


print("=" * 70)
print("A. what encoder state actually is")
print("=" * 70)
# Feed a known bit sequence and show the register + outputs
bits = np.array([1, 0, 1, 1, 0, 0, 1], dtype=np.uint8)
enc = conv_encode(bits, K, polys)
print(f"  input bits      : {list(bits)}")
print(f"  encoded (pairs) : {[list(enc[i:i+2]) for i in range(0, len(enc), 2)]}")
print()
print("  Let's hypothesise: output pair t depends on (b[t], b[t-1], b[t-2])")
for t in range(len(bits) + sb):
    win = [bits[t - d] if 0 <= t - d < len(bits) else 0 for d in range(K)]
    exp = [bin(sum(b << (K - 1 - i) for i, b in enumerate(win)) & p).count("1") & 1
           for p in polys]
    got = list(enc[t * 2:t * 2 + 2])
    print(f"   t={t}  window(MSB-first)={win}  expected={exp}  encoder_gave={got}"
          f"  {'ok' if exp == got else 'MISMATCH'}")

print()
print("=" * 70)
print("B. does the decoder's trellis reproduce the encoder's outputs?")
print("=" * 70)
# Encoder state after t inputs = last K-1 bits = bits[t-1], bits[t-2] (MSB-first)
# Test: for every reachable state and both inputs, does emit() match reality?
bad = 0
for step in range(200):
    pass
rng = np.random.default_rng(3)
seq = rng.integers(0, 2, 300).astype(np.uint8)
enc_full = conv_encode(seq, K, polys)
padded = np.concatenate([seq, np.zeros(sb, dtype=np.uint8)])

# Walk the encoder, tracking the register exactly as conv_encode does.
reg = 0
for t in range(len(padded)):
    b = int(padded[t])
    reg = ((reg << 1) | b) & ((1 << sb) - 1) if sb else 0
    window = ((b << sb) | reg) if sb else b
    real_out = [bin(window & p).count("1") & 1 for p in polys]
    got = list(enc_full[t * 2:t * 2 + 2])
    if real_out != got:
        bad += 1
        if bad <= 3:
            print(f"   t={t} encoder_internal={real_out} emitted={got} MISMATCH")
print(f"   encoder self-consistency mismatches: {bad}")

print()
print("=" * 70)
print("C. brute-force decode: does SOME path explain the encoded stream?")
print("=" * 70)
# For the first few steps, enumerate all bit sequences and find one whose
# encoding matches the observed pairs. If none matches, encoder and the
# decoder's model of it disagree.
n_try = 8
observed = enc_full[:n_try * 2]
found = None
for candidate in range(1 << (n_try + sb)):
    b_seq = np.array([(candidate >> (n_try + sb - 1 - i)) & 1 for i in range(n_try + sb)],
                     dtype=np.uint8)
    e = conv_encode(b_seq[:n_try], K, polys)[:n_try * 2]
    if np.array_equal(e, observed):
        found = b_seq[:n_try]
        break
print(f"   observed pairs   : {list(observed)}")
print(f"   matching input   : {list(found) if found is not None else 'NONE FOUND'}")
print(f"   true input       : {list(seq[:n_try])}")

print()
print("=" * 70)
print("D. decoder traceback check on the clean stream")
print("=" * 70)
dec = viterbi_decode(enc_full)
m = min(len(seq), len(dec))
print(f"   decoded : {list(dec[:16])}")
print(f"   true    : {list(seq[:16])}")
print(f"   accuracy: {np.mean(dec[:m] == seq[:m])*100:.2f}%")
# Is it perhaps the COMPLEMENT, or an offset?
print(f"   complement match: {np.mean((1-dec[:m]) == seq[:m])*100:.2f}%")
for shift in range(1, 4):
    if len(dec) > shift:
        a = np.mean(dec[shift:shift + m - shift] == seq[:m - shift]) * 100
        print(f"   shift {shift} match: {a:.2f}%")
