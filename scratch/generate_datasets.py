"""
SIGMA - Synthetic Dataset & Test Vector Generator
Generates structured sample recordings and test vectors clearly marked as:
SYNTHETIC TEST DATA
"""

import os
import json
import numpy as np
import scipy.io.wavfile as wavfile

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")


def rrc_pulse(sps=4, alpha=0.35, span=8):
    n = span * sps
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
            num = (np.sin(np.pi * ti * (1.0 - alpha))
                   + 4.0 * alpha * ti * np.cos(np.pi * (1.0 + alpha) * ti))
            den = np.pi * ti * (1.0 - (4.0 * alpha * ti) ** 2)
            h[i] = num / den
    h /= np.sqrt(np.sum(h ** 2))
    return h


def make_psk_iq(mod="BPSK", num_symbols=2000, sps=4, samp_rate=1000000.0, snr_db=25.0, freq_off=5000.0):
    rng = np.random.default_rng(123)
    if mod == "BPSK":
        bits = rng.integers(0, 2, num_symbols)
        syms = (2 * bits - 1).astype(np.complex64)
    elif mod == "QPSK":
        bits = rng.integers(0, 2, num_symbols * 2)
        pairs = bits.reshape(-1, 2)
        lut = {(0,0): 1+1j, (0,1): -1+1j, (1,1): -1-1j, (1,0): 1-1j}
        syms = np.array([lut[tuple(p)] for p in pairs], dtype=np.complex64) / np.sqrt(2.0)
    elif mod == "16QAM":
        bits = rng.integers(0, 2, num_symbols * 4)
        quads = bits.reshape(-1, 4)
        levels = np.array([-3, -1, 1, 3], dtype=np.float32) / np.sqrt(10.0)
        syms = np.array([levels[q[0]*2 + q[1]] + 1j * levels[q[2]*2 + q[3]] for q in quads], dtype=np.complex64)
    else:
        syms = (rng.normal(size=num_symbols) + 1j * rng.normal(size=num_symbols)).astype(np.complex64)

    # Upsample
    upsampled = np.zeros(num_symbols * sps, dtype=np.complex64)
    upsampled[::sps] = syms

    # Pulse shaping
    h = rrc_pulse(sps=sps, alpha=0.35)
    tx = np.convolve(upsampled, h, mode="same")

    # Carrier offset
    t = np.arange(len(tx)) / samp_rate
    tx = tx * np.exp(1j * 2.0 * np.pi * freq_off * t)

    # Additive white Gaussian noise
    p_sig = np.mean(np.abs(tx) ** 2)
    p_noise = p_sig / (10.0 ** (snr_db / 10.0))
    noise = (rng.normal(0, np.sqrt(p_noise / 2.0), len(tx)) +
             1j * rng.normal(0, np.sqrt(p_noise / 2.0), len(tx)))
    rx = (tx + noise).astype(np.complex64)
    return rx, bits if 'bits' in locals() else None


def make_fsk_iq(num_symbols=2000, sps=8, samp_rate=1000000.0, deviation_hz=25000.0, snr_db=25.0):
    rng = np.random.default_rng(456)
    bits = rng.integers(0, 2, num_symbols)
    syms = np.where(bits == 1, deviation_hz, -deviation_hz)
    
    # Repeat across sps
    freq_inst = np.repeat(syms, sps)
    phase = 2.0 * np.pi * np.cumsum(freq_inst) / samp_rate
    tx = np.exp(1j * phase).astype(np.complex64)

    # Noise
    p_noise = 1.0 / (10.0 ** (snr_db / 10.0))
    noise = (rng.normal(0, np.sqrt(p_noise / 2.0), len(tx)) +
             1j * rng.normal(0, np.sqrt(p_noise / 2.0), len(tx)))
    rx = (tx + noise).astype(np.complex64)
    return rx, bits


def save_wav_stereo(filepath, iq_samples, samp_rate=48000):
    i_ch = np.real(iq_samples)
    q_ch = np.imag(iq_samples)
    max_val = max(1e-6, np.max(np.abs(iq_samples)))
    i_16 = np.clip(i_ch / max_val * 32767, -32768, 32767).astype(np.int16)
    q_16 = np.clip(q_ch / max_val * 32767, -32768, 32767).astype(np.int16)
    stereo = np.column_stack([i_16, q_16])
    wavfile.write(filepath, int(samp_rate), stereo)


def main():
    dirs = [
        "iq/bpsk", "iq/qpsk", "iq/fsk", "iq/qam", "iq/unknown",
        "wav/bpsk", "wav/qpsk", "wav/fsk", "wav/qam", "wav/unknown",
        "test_vectors/demodulation", "test_vectors/deinterleaving",
        "test_vectors/fec", "test_vectors/correlation"
    ]
    for d in dirs:
        os.makedirs(os.path.join(DATA_DIR, d), exist_ok=True)

    # 1. BPSK
    bpsk_iq, bpsk_bits = make_psk_iq("BPSK", num_symbols=3000, sps=4, samp_rate=1000000.0)
    bpsk_path = os.path.join(DATA_DIR, "iq", "bpsk", "synthetic_bpsk_250ksps_1msps.iq")
    bpsk_iq.tofile(bpsk_path)
    save_wav_stereo(os.path.join(DATA_DIR, "wav", "bpsk", "synthetic_bpsk.wav"), bpsk_iq[:16000], samp_rate=48000)

    with open(bpsk_path + "_meta.json", "w") as f:
        json.dump({
            "source_type": "SYNTHETIC TEST DATA",
            "modulation": "BPSK",
            "symbol_rate": 250000.0,
            "sample_rate": 1000000.0,
            "sps": 4,
            "snr_db": 25.0,
            "description": "Synthetic BPSK test recording with known ground truth"
        }, f, indent=2)

    # 2. QPSK
    qpsk_iq, qpsk_bits = make_psk_iq("QPSK", num_symbols=3000, sps=4, samp_rate=1000000.0)
    qpsk_path = os.path.join(DATA_DIR, "iq", "qpsk", "synthetic_qpsk_250ksps_1msps.iq")
    qpsk_iq.tofile(qpsk_path)
    save_wav_stereo(os.path.join(DATA_DIR, "wav", "qpsk", "synthetic_qpsk.wav"), qpsk_iq[:16000], samp_rate=48000)

    # 3. FSK
    fsk_iq, fsk_bits = make_fsk_iq(num_symbols=2000, sps=8, samp_rate=1000000.0)
    fsk_path = os.path.join(DATA_DIR, "iq", "fsk", "synthetic_fsk_125ksps_1msps.iq")
    fsk_iq.tofile(fsk_path)
    save_wav_stereo(os.path.join(DATA_DIR, "wav", "fsk", "synthetic_fsk.wav"), fsk_iq[:16000], samp_rate=48000)

    # 4. QAM
    qam_iq, qam_bits = make_psk_iq("16QAM", num_symbols=2000, sps=4, samp_rate=1000000.0)
    qam_path = os.path.join(DATA_DIR, "iq", "qam", "synthetic_16qam_250ksps_1msps.iq")
    qam_iq.tofile(qam_path)
    save_wav_stereo(os.path.join(DATA_DIR, "wav", "qam", "synthetic_qam.wav"), qam_iq[:16000], samp_rate=48000)

    # 5. Test vectors: Demodulation, De-interleaving, FEC, Correlation
    np.save(os.path.join(DATA_DIR, "test_vectors", "demodulation", "bpsk_tx_bits.npy"), bpsk_bits)
    np.save(os.path.join(DATA_DIR, "test_vectors", "demodulation", "qpsk_tx_bits.npy"), qpsk_bits)

    # Deinterleaving test vector
    raw_bits = np.random.default_rng(42).integers(0, 2, 256, dtype=np.uint8)
    np.save(os.path.join(DATA_DIR, "test_vectors", "deinterleaving", "raw_bits_256.npy"), raw_bits)

    # FEC test vector
    np.save(os.path.join(DATA_DIR, "test_vectors", "fec", "info_bits_128.npy"), raw_bits[:128])

    # Correlation test vector (known CCSDS sync prefix + payload)
    sync = np.unpackbits(np.frombuffer(bytes.fromhex("1ACFFC1D"), dtype=np.uint8))
    frame = np.concatenate([sync, raw_bits[:128]])
    np.save(os.path.join(DATA_DIR, "test_vectors", "correlation", "ccsds_frame.npy"), frame)

    print("[*] Successfully generated all structured test datasets and vectors.")


if __name__ == "__main__":
    main()
