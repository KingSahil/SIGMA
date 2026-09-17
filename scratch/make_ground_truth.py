"""
Generate a KNOWN-GOOD test signal so we can verify the symbol rate estimator.

This makes a properly pulse-shaped BPSK signal where we control the exact
symbol rate. Without this, there is no way to tell if the estimator works.

Creates:
  data/iq/test_bpsk_100ksps_1msps.iq   -> R_s = 100 ksps, f_s = 1 Msps (SPS=10)
  data/iq/test_qpsk_50ksps_1msps.iq    -> R_s =  50 ksps, f_s = 1 Msps (SPS=20)
  data/iq/test_bpsk_200ksps_1msps.iq   -> R_s = 200 ksps, f_s = 1 Msps (SPS=5)

Each is a real RRC-pulse-shaped signal with a known symbol rate, so the
estimator can be scored with actual error percentages.
"""
import numpy as np
import os

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "iq")
FS = 1_000_000


def rrc_filter(sps, alpha, span_symbols=8):
    """Root-raised-cosine impulse response, unit energy."""
    n = span_symbols * sps
    t = np.arange(-n // 2, n // 2 + 1, dtype=np.float64) / sps
    h = np.zeros_like(t)
    for i, ti in enumerate(t):
        if abs(ti) < 1e-8:
            h[i] = 1.0 - alpha + 4.0 * alpha / np.pi
        elif alpha > 0 and abs(abs(ti) - 1.0 / (4.0 * alpha)) < 1e-8:
            h[i] = (alpha / np.sqrt(2.0)) * (
                (1.0 + 2.0 / np.pi) * np.sin(np.pi / (4.0 * alpha))
                - (1.0 - 2.0 / np.pi) * np.cos(np.pi / (4.0 * alpha))
            )
        else:
            num = np.sin(np.pi * ti * (1.0 - alpha)) + \
                  4.0 * alpha * ti * np.cos(np.pi * ti * (1.0 + alpha))
            den = np.pi * ti * (1.0 - (4.0 * alpha * ti) ** 2)
            h[i] = num / den
    h /= np.sqrt(np.sum(h ** 2))
    return h


def make_signal(symbol_rate, modulation, alpha=0.35, n_symbols=4000, seed=42):
    """Build a pulse-shaped baseband signal with a known symbol rate."""
    rng = np.random.default_rng(seed)
    sps = FS / symbol_rate

    if modulation == "bpsk":
        sym = rng.integers(0, 2, n_symbols) * 2 - 1
        sym = sym.astype(np.complex128)
    elif modulation == "qpsk":
        bits_i = rng.integers(0, 2, n_symbols) * 2 - 1
        bits_q = rng.integers(0, 2, n_symbols) * 2 - 1
        sym = (bits_i + 1j * bits_q) / np.sqrt(2)
    else:
        raise ValueError(modulation)

    # Upsample by inserting zeros: one symbol every `sps` samples.
    sps_int = int(round(sps))
    if abs(sps - sps_int) > 1e-9:
        raise ValueError(f"SPS must be integer, got {sps}")
    up = np.zeros(n_symbols * sps_int, dtype=np.complex128)
    up[::sps_int] = sym

    # Apply RRC pulse shaping -- this is what creates a recoverable clock.
    h = rrc_filter(sps_int, alpha)
    shaped = np.convolve(up, h, mode="same")

    # Small carrier offset, like a real capture (kept well inside the band).
    t = np.arange(len(shaped)) / FS
    f_off = 60_000.0
    shaped = shaped * np.exp(1j * 2 * np.pi * f_off * t)

    # Add noise so it is not a noise-free ideal case.
    noise = (rng.normal(0, 1, len(shaped)) +
             1j * rng.normal(0, 1, len(shaped))) * 0.02
    out = shaped + noise

    # Normalise to unit-ish peak, complex64 like the rest of the project.
    out = out / np.max(np.abs(out)) * 0.9
    return out.astype(np.complex64), sps_int


def main():
    os.makedirs(OUT, exist_ok=True)
    cases = [
        ("test_bpsk_100ksps_1msps.iq", 100_000, "bpsk"),
        ("test_qpsk_50ksps_1msps.iq", 50_000, "qpsk"),
        ("test_bpsk_200ksps_1msps.iq", 200_000, "bpsk"),
    ]
    manifest = []
    for fname, rate, mod in cases:
        sig, sps = make_signal(rate, mod)
        path = os.path.join(OUT, fname)
        sig.tofile(path)
        manifest.append((fname, rate, sps, len(sig)))
        print(f"wrote {fname}: R_s={rate/1e3:.1f} ksps  SPS={sps}  "
              f"n={len(sig)}  ({len(sig)/FS*1e3:.1f} ms)")

    print("\nGround truth for verification:")
    print(f"{'file':<34}{'R_s (ksps)':>12}{'SPS':>6}")
    for fname, rate, sps, n in manifest:
        print(f"{fname:<34}{rate/1e3:>12.1f}{sps:>6}")


if __name__ == "__main__":
    main()
