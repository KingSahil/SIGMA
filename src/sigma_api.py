#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIGMA - Signal Intelligence & Generalized Modulation Analyzer
Telecom DSP & Advanced Signal Analysis FastAPI Service

Provides RESTful endpoints for:
- Advanced IQ Signal Analysis (/api/analyze_advanced)
- Modulation generation (/api/modulate)
- Demodulation & Slicing (/api/demodulate)
- Carrier, Clock & Frame Synchronization (/api/synchronize)
- De-interleaving (/api/deinterleave)
- Forward Error Correction (FEC) Decoding (/api/fec_decode)
"""

import os
import io
import math
import shutil
import tempfile
import numpy as np
import scipy.signal as signal
from typing import List, Dict, Optional, Any, Union
from pydantic import BaseModel, Field
from fastapi import FastAPI, UploadFile, File, Form, Query, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Avoid importing the heavyweight PyTorch runtime during API startup. The
# legacy API only reports whether it is installed; inference is optional.
import importlib.util

TORCH_AVAILABLE = importlib.util.find_spec("torch") is not None
torch = None

# Initialize FastAPI application
app = FastAPI(
    title="SIGMA RF Intelligence API",
    description="Advanced Telecom DSP & Signal Intelligence Processing API (Modulation, Demodulation, Synchronization, FEC, Interleaving)",
    version="2.0.0",
)

# Enable CORS for Swagger UI, React/Vue/Svelte/Next.js/vanilla GUI clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# The legacy telecom routes below remain available for existing clients. The
# modular signal-analysis API is mounted alongside them for the web frontend.
from backend.api_routes import router as signal_router, analysis_socket
from backend.db import init_db

init_db()
app.include_router(signal_router)


@app.websocket("/ws/analysis/{analysis_id}")
async def analysis_progress_socket(websocket, analysis_id: str):
    """Compatibility path matching the public websocket contract."""
    await analysis_socket(websocket, analysis_id)

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ==============================================================================
# 1. TELECOM DSP CORE: MODULATION
# ==============================================================================

# Standard Constellations
CONSTELLATIONS = {
    "BPSK": np.array([1.0 + 0.0j, -1.0 + 0.0j], dtype=np.complex128),
    "QPSK": np.array([1 + 1j, -1 + 1j, -1 - 1j, 1 - 1j], dtype=np.complex128) / np.sqrt(2.0),
    "8PSK": np.array([np.exp(1j * 2.0 * np.pi * k / 8.0) for k in range(8)], dtype=np.complex128),
    "16QAM": np.array([
        (i + 1j * q) for i in [-3.0, -1.0, 1.0, 3.0] for q in [-3.0, -1.0, 1.0, 3.0]
    ], dtype=np.complex128) / np.sqrt(10.0),
}

BITS_PER_SYMBOL = {
    "BPSK": 1,
    "QPSK": 2,
    "8PSK": 3,
    "16QAM": 4,
    "BFSK": 1,
    "4FSK": 2,
}


def rrc_filter(sps: int, alpha: float = 0.35, span_symbols: int = 8) -> np.ndarray:
    """Root-Raised-Cosine (RRC) impulse response with unit energy."""
    sps = max(1, int(round(sps)))
    if sps < 2:
        return np.array([1.0], dtype=np.float64)
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
            num = (np.sin(np.pi * ti * (1.0 - alpha))
                   + 4.0 * alpha * ti * np.cos(np.pi * (1.0 + alpha) * ti))
            den = np.pi * ti * (1.0 - (4.0 * alpha * ti) ** 2)
            h[i] = num / den
    energy = np.sum(h ** 2)
    if energy > 0:
        h /= np.sqrt(energy)
    return h


def modulate_bitstream(
    bits: List[int],
    mod_type: str = "QPSK",
    sps: int = 4,
    pulse_shape: str = "rrc",
    alpha: float = 0.35,
    cfo_hz: float = 0.0,
    phase_offset_deg: float = 0.0,
    snr_db: Optional[float] = None,
    samp_rate: float = 1e6,
) -> np.ndarray:
    """
    Modulates a binary bitstream into complex baseband IQ samples.
    Supports BPSK, QPSK, 8PSK, 16QAM, BFSK with pulse shaping and channel impairments.
    """
    mod_type = mod_type.upper().replace("-", "")
    k = BITS_PER_SYMBOL.get(mod_type, 1)

    # Pad bits to multiple of bits-per-symbol
    remainder = len(bits) % k
    if remainder != 0:
        bits = bits + [0] * (k - remainder)

    # Symbol mapping
    if mod_type in ["BPSK", "QPSK", "8PSK", "16QAM"]:
        const = CONSTELLATIONS[mod_type]
        num_symbols = len(bits) // k
        symbols = np.zeros(num_symbols, dtype=np.complex128)
        for i in range(num_symbols):
            sym_idx = 0
            for b in range(k):
                sym_idx = (sym_idx << 1) | int(bits[i * k + b])
            sym_idx = sym_idx % len(const)
            symbols[i] = const[sym_idx]

        # Pulse shaping (upsampling + filter)
        if sps > 1:
            upsampled = np.zeros(len(symbols) * sps, dtype=np.complex128)
            upsampled[::sps] = symbols
            if pulse_shape.lower() == "rrc":
                filt = rrc_filter(sps, alpha=alpha)
                tx_samples = np.convolve(upsampled, filt, mode="same")
            else:  # rectangular
                tx_samples = np.repeat(symbols, sps)
        else:
            tx_samples = symbols.copy()

    elif "FSK" in mod_type:
        # FSK modulation
        num_symbols = len(bits) // k
        tx_samples = []
        t = np.arange(sps) / samp_rate
        freq_dev = samp_rate / (4.0 * sps)  # Orthogonal separation
        for i in range(num_symbols):
            val = 0
            for b in range(k):
                val = (val << 1) | int(bits[i * k + b])
            # Map symbol index to frequency offset centered at 0
            M = 2 ** k
            freq = (val - (M - 1) / 2.0) * freq_dev
            tone = np.exp(1j * 2.0 * np.pi * freq * t)
            tx_samples.extend(tone)
        tx_samples = np.array(tx_samples, dtype=np.complex128)
    else:
        raise ValueError(f"Unsupported modulation type '{mod_type}'")

    # Add Carrier Frequency Offset (CFO) & Phase Offset
    total_len = len(tx_samples)
    t_full = np.arange(total_len) / samp_rate
    phase_rad = np.radians(phase_offset_deg)
    tx_samples = tx_samples * np.exp(1j * (2.0 * np.pi * cfo_hz * t_full + phase_rad))

    # Add AWGN if SNR is specified
    if snr_db is not None:
        sig_pwr = np.mean(np.abs(tx_samples) ** 2)
        noise_pwr = sig_pwr / (10.0 ** (snr_db / 10.0))
        noise_std = np.sqrt(noise_pwr / 2.0)
        noise = np.random.normal(0, noise_std, total_len) + 1j * np.random.normal(0, noise_std, total_len)
        tx_samples = tx_samples + noise

    return tx_samples


# ==============================================================================
# 2. TELECOM DSP CORE: SYNCHRONIZATION
# ==============================================================================

def estimate_and_correct_cfo(
    iq_samples: np.ndarray,
    samp_rate: float = 1e6,
    mod_type: str = "QPSK",
) -> tuple[np.ndarray, float]:
    """
    Carrier Frequency Offset (CFO) estimation & removal.
    Uses the M-th power non-linear method (squaring for BPSK, 4th power for QPSK/16QAM)
    to strip data modulation and isolate the carrier tone.
    """
    mod = mod_type.upper().replace("-", "")
    m_power = 2 if mod == "BPSK" else (8 if mod == "8PSK" else 4)

    n = len(iq_samples)
    if n < 64:
        return iq_samples, 0.0

    nfft = 1 << int(np.floor(np.log2(max(512, min(n, 32768)))))
    if nfft > n:
        nfft = 1 << int(np.floor(np.log2(n)))

    seg = iq_samples[:nfft] * np.blackman(nfft)
    m_th_seg = seg ** m_power
    spec = np.abs(np.fft.fftshift(np.fft.fft(m_th_seg)))
    freqs = np.fft.fftshift(np.fft.fftfreq(nfft, 1.0 / samp_rate))

    peak_idx = int(np.argmax(spec))
    estimated_cfo = float(freqs[peak_idx] / m_power)

    # Fold ambiguity to Nyquist span
    span = samp_rate / float(m_power)
    while estimated_cfo > span / 2:
        estimated_cfo -= span
    while estimated_cfo < -span / 2:
        estimated_cfo += span

    # De-rotate samples
    t = np.arange(len(iq_samples), dtype=np.float64) / samp_rate
    corrected_samples = iq_samples * np.exp(-1j * 2.0 * np.pi * estimated_cfo * t)

    return corrected_samples, estimated_cfo


def symbol_timing_sync(
    iq_samples: np.ndarray,
    sps: int = 4,
    mod_type: str = "QPSK",
    alpha: float = 0.35,
) -> tuple[np.ndarray, int]:
    """
    Symbol Timing & Clock Recovery.
    Applies an RRC matched filter, evaluates all sub-symbol sampling phases (0 to sps-1),
    and picks the sampling phase that maximizes the eye opening / minimum Euclidean clustering.
    """
    sps = max(1, int(round(sps)))
    if sps <= 1:
        return iq_samples, 0

    # 1. Matched filtering
    filt = rrc_filter(sps, alpha=alpha)
    if len(filt) >= 3:
        filtered = np.convolve(iq_samples, filt, mode="same")
    else:
        filtered = iq_samples

    mod = mod_type.upper().replace("-", "")
    const = CONSTELLATIONS.get(mod, CONSTELLATIONS["QPSK"])
    ref_rms = np.sqrt(np.mean(np.abs(const) ** 2))

    best_phase = 0
    best_score = float("inf")

    # 2. Optimum eye phase decimation
    for phase in range(sps):
        sliced = filtered[phase::sps]
        if len(sliced) < 16:
            continue
        scale = np.sqrt(np.mean(np.abs(sliced) ** 2))
        if scale <= 1e-12:
            continue
        normalised = (sliced / scale) * ref_rms
        dist = np.min(np.abs(normalised[:, None] - const[None, :]), axis=1)
        score = float(np.sqrt(np.mean(dist ** 2)))
        if score < best_score:
            best_score = score
            best_phase = phase

    recovered_symbols = filtered[best_phase::sps]
    return recovered_symbols, best_phase


def carrier_phase_recovery(
    symbols: np.ndarray,
    mod_type: str = "QPSK",
) -> tuple[np.ndarray, float]:
    """
    Recovers residual constant phase rotation by testing constellation rotational symmetry.
    """
    mod = mod_type.upper().replace("-", "")
    const = CONSTELLATIONS.get(mod, CONSTELLATIONS["QPSK"])
    n_rots = {"BPSK": 2, "QPSK": 4, "8PSK": 8, "16QAM": 4}.get(mod, 4)

    if len(symbols) == 0:
        return symbols, 0.0

    # Normalise scale
    scale = np.sqrt(np.mean(np.abs(symbols) ** 2))
    if scale > 1e-12:
        norm_syms = symbols / scale * np.sqrt(np.mean(np.abs(const) ** 2))
    else:
        norm_syms = symbols

    mean_vec = np.mean(norm_syms ** n_rots)
    coarse = float(np.angle(mean_vec) / n_rots) if np.abs(mean_vec) > 1e-12 else 0.0

    candidates = [coarse + k * (2.0 * np.pi / (4.0 * n_rots)) for k in range(-4, 5)]
    best_rot, best_score = 0.0, float("inf")
    for rot in candidates:
        test = norm_syms * np.exp(-1j * rot)
        dist = np.min(np.abs(test[:, None] - const[None, :]), axis=1)
        score = float(np.mean(dist ** 2))
        if score < best_score:
            best_score = score
            best_rot = rot

    derotated = norm_syms * np.exp(-1j * best_rot)
    return derotated, float(np.degrees(best_rot))


def run_bitstream_correlation(
    bits: List[int],
    marker_name: str = "Barker-11",
) -> Dict[str, Any]:
    """
    Frame & Bitstream Synchronization.
    Correlates bitstream with standard synchronization markers (Barker codes)
    to identify frame boundaries, header, and payload.
    """
    known_markers = {
        "Barker-11": [1, 1, 1, 0, 0, 0, 1, 0, 0, 1, 0],
        "Barker-13": [1, 1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1],
        "Barker-7": [1, 1, 1, 0, 0, 1, 0],
    }
    sync_marker = known_markers.get(marker_name, known_markers["Barker-11"])
    m_len = len(sync_marker)

    if len(bits) < m_len:
        return {
            "sync_marker": marker_name,
            "sync_index_found": -1,
            "correlation_score": 0.0,
            "header_hex": "",
            "payload_bits": "".join(str(b) for b in bits),
        }

    # Bipolar correlation (+1 / -1)
    bipolar_bits = np.array([1 if b == 1 else -1 for b in bits], dtype=np.float32)
    bipolar_marker = np.array([1 if b == 1 else -1 for b in sync_marker], dtype=np.float32)

    corr = np.correlate(bipolar_bits, bipolar_marker, mode="valid")
    best_idx = int(np.argmax(corr))
    max_corr = float(corr[best_idx])
    norm_corr = max_corr / m_len

    payload_start = best_idx + m_len
    header_bits = bits[payload_start : payload_start + 32]
    payload_bits = bits[payload_start + 32 : payload_start + 256]

    # Convert header bits to hex
    header_hex = ""
    for i in range(0, len(header_bits), 4):
        nibble = header_bits[i:i+4]
        val = 0
        for b in nibble:
            val = (val << 1) | int(b)
        header_hex += hex(val)[2:].upper()

    return {
        "sync_marker": marker_name,
        "sync_index_found": best_idx,
        "correlation_score": round(norm_corr, 4),
        "header_hex": header_hex if header_hex else "00000000",
        "payload_bits": "".join(str(b) for b in payload_bits),
        "total_bits_analyzed": len(bits),
    }


# ==============================================================================
# 3. TELECOM DSP CORE: DEMODULATION & SLICING
# ==============================================================================

def soft_demodulate_symbols(
    symbols: np.ndarray,
    mod_type: str = "QPSK",
) -> tuple[List[int], float, List[float]]:
    """
    Demodulates PSK, QAM, or FSK symbols into hard bit arrays and calculates EVM.
    Returns: (bits, evm_percent, soft_llrs)
    """
    mod = mod_type.upper().replace("-", "")
    k = BITS_PER_SYMBOL.get(mod, 2)

    if mod in ["BPSK", "QPSK", "8PSK", "16QAM"]:
        const = CONSTELLATIONS[mod]
        # Distance matrix (symbols x constellation_points)
        diff = symbols[:, None] - const[None, :]
        dists = np.abs(diff)
        nearest_idx = np.argmin(dists, axis=1)

        # Calculate EVM (%)
        min_dists = np.min(dists, axis=1)
        rms_err = float(np.sqrt(np.mean(min_dists ** 2)))
        rms_ref = float(np.sqrt(np.mean(np.abs(const) ** 2)))
        evm_percent = float((rms_err / (rms_ref + 1e-12)) * 100.0)

        # De-map to bits
        bits: List[int] = []
        soft_llrs: List[float] = []
        for i, idx in enumerate(nearest_idx):
            for b in range(k):
                bit = (idx >> (k - 1 - b)) & 1
                bits.append(int(bit))

            # Simplified soft LLR estimate based on I & Q distance
            soft_llrs.append(float(np.real(symbols[i])))
            if k >= 2:
                soft_llrs.append(float(np.imag(symbols[i])))

        return bits, evm_percent, soft_llrs

    else:
        # Fallback slicer for FSK / unknown
        bits = [1 if np.real(s) > 0 else 0 for s in symbols]
        return bits, 0.0, [float(np.real(s)) for s in symbols]


# ==============================================================================
# 4. TELECOM DSP CORE: INTERLEAVING & DE-INTERLEAVING
# ==============================================================================

def run_interleaver(
    bits: List[int],
    scheme: str = "Block",
    matrix_size: int = 4,
    seed: int = 42,
) -> List[int]:
    """
    Interleaves bits using Matrix Block, Convolutional/Diagonal, or Pseudo-Random permutation.
    """
    if len(bits) == 0:
        return []

    scheme = scheme.capitalize()
    if scheme == "Block":
        block_len = matrix_size * matrix_size
        out_bits = []
        for i in range(0, len(bits), block_len):
            chunk = bits[i:i+block_len]
            if len(chunk) < block_len:
                chunk = chunk + [0] * (block_len - len(chunk))
            matrix = np.array(chunk).reshape((matrix_size, matrix_size))
            # Writes by row, reads by column (transpose)
            interleaved = matrix.T.flatten().tolist()
            out_bits.extend(interleaved)
        return out_bits

    elif scheme in ["Pseudorandom", "Pseudo Random", "Random"]:
        rng = np.random.RandomState(seed)
        perm = rng.permutation(len(bits))
        return [bits[p] for p in perm]

    elif scheme in ["Diagonal", "Convolutional"]:
        # Diagonal delay interleaving simulation
        out_bits = []
        for idx, b in enumerate(bits):
            shift = (idx % matrix_size)
            out_bits.append(bits[(idx + shift) % len(bits)])
        return out_bits

    return bits


def run_deinterleaver(
    bits: List[int],
    scheme: str = "Block",
    matrix_size: int = 4,
    seed: int = 42,
) -> List[int]:
    """
    De-interleaves bits (Inverse operation of run_interleaver).
    Restores original temporal order to disperse burst errors.
    """
    if len(bits) == 0:
        return []

    scheme = scheme.capitalize()
    if scheme == "Block":
        block_len = matrix_size * matrix_size
        out_bits = []
        for i in range(0, len(bits), block_len):
            chunk = bits[i:i+block_len]
            if len(chunk) < block_len:
                chunk = chunk + [0] * (block_len - len(chunk))
            matrix = np.array(chunk).reshape((matrix_size, matrix_size))
            # Inverse of transpose is transpose
            deinterleaved = matrix.T.flatten().tolist()
            out_bits.extend(deinterleaved)
        return out_bits

    elif scheme in ["Pseudorandom", "Pseudo Random", "Random"]:
        rng = np.random.RandomState(seed)
        perm = rng.permutation(len(bits))
        inv_perm = np.zeros(len(bits), dtype=int)
        for original_idx, perm_idx in enumerate(perm):
            inv_perm[perm_idx] = original_idx
        return [bits[p] for p in inv_perm]

    elif scheme in ["Diagonal", "Convolutional"]:
        out_bits = []
        for idx in range(len(bits)):
            shift = (idx % matrix_size)
            orig_idx = (idx - shift) % len(bits)
            out_bits.append(bits[orig_idx])
        return out_bits

    return bits


# ==============================================================================
# 5. TELECOM DSP CORE: FORWARD ERROR CORRECTION (FEC)
# ==============================================================================

def run_fec_decoder(
    bits: List[int],
    code_type: str = "Viterbi",
) -> Dict[str, Any]:
    """
    FEC Decoder implementing:
    - Viterbi Decoding (Convolutional code Rate 1/2, K=3 standard trellis)
    - Hamming (7,4) Single Error Correction
    - Parity Check / Repetition
    """
    code_type = code_type.upper()

    if "VITERBI" in code_type or "CONVOLUTIONAL" in code_type:
        # Rate 1/2, K=3 Convolutional Code with generators G1=7 (111_2), G2=5 (101_2)
        num_states = 4  # 2^(K-1)
        # Trellis transitions: for each state s and input bit b (0 or 1):
        # next_state = ((s << 1) | b) & 3
        # out1 = b ^ ((s >> 1) & 1) ^ (s & 1)
        # out2 = b ^ ((s >> 1) & 1)
        trellis = {}
        for s in range(num_states):
            for b in (0, 1):
                next_s = ((s << 1) | b) & 3
                out1 = b ^ ((s >> 1) & 1) ^ (s & 1)
                out2 = b ^ ((s >> 1) & 1)
                trellis[(s, b)] = (next_s, (out1, out2))

        # Pad bits to even length
        if len(bits) % 2 != 0:
            bits = bits + [0]

        num_steps = len(bits) // 2
        # Viterbi state metrics: path_cost[state], path_history[state]
        INF = float("inf")
        path_cost = [0.0] + [INF] * (num_states - 1)
        path_history = [[] for _ in range(num_states)]

        for step in range(num_steps):
            rx_sym = (bits[2 * step], bits[2 * step + 1])
            new_cost = [INF] * num_states
            new_history = [[] for _ in range(num_states)]

            for s in range(num_states):
                if path_cost[s] == INF:
                    continue
                for b in (0, 1):
                    next_s, out_sym = trellis[(s, b)]
                    # Hamming branch metric
                    metric = (rx_sym[0] ^ out_sym[0]) + (rx_sym[1] ^ out_sym[1])
                    total = path_cost[s] + metric
                    if total < new_cost[next_s]:
                        new_cost[next_s] = total
                        new_history[next_s] = path_history[s] + [b]

            path_cost = new_cost
            path_history = new_history

        best_state = int(np.argmin(path_cost))
        decoded_bits = path_history[best_state]
        errors_corrected = int(path_cost[best_state])

        return {
            "fec_type": "Convolutional (Viterbi Rate 1/2, K=3)",
            "decoded_bits": decoded_bits,
            "errors_corrected": errors_corrected,
            "status": "success",
        }

    elif "HAMMING" in code_type:
        # Hamming (7,4) decoder: syndromes H * r^T
        # H = [[1, 0, 1, 0, 1, 0, 1], [0, 1, 1, 0, 0, 1, 1], [0, 0, 0, 1, 1, 1, 1]]
        decoded_bits = []
        errors_corrected = 0
        for i in range(0, len(bits) - 6, 7):
            c = list(bits[i:i+7])
            s0 = c[0] ^ c[2] ^ c[4] ^ c[6]
            s1 = c[1] ^ c[2] ^ c[5] ^ c[6]
            s2 = c[3] ^ c[4] ^ c[5] ^ c[6]
            syndrome = (s2 << 2) | (s1 << 1) | s0
            if syndrome > 0 and syndrome <= 7:
                c[syndrome - 1] ^= 1
                errors_corrected += 1
            # Data bits at positions 2, 4, 5, 6
            decoded_bits.extend([c[2], c[4], c[5], c[6]])

        return {
            "fec_type": "Hamming (7, 4)",
            "decoded_bits": decoded_bits,
            "errors_corrected": errors_corrected,
            "status": "success",
        }

    else:
        # Default pass-through
        return {
            "fec_type": code_type,
            "decoded_bits": bits,
            "errors_corrected": 0,
            "status": "pass_through",
        }


# ==============================================================================
# 6. TELECOM DSP CORE: SPECTRAL & GUI PLOT DATA
# ==============================================================================

def extract_spectral_gui_data(
    iq_samples: np.ndarray,
    fft_size: int = 512,
    waterfall_frames: int = 16,
) -> Dict[str, Any]:
    """
    Generates spectral, waterfall, constellation, and SNR metrics
    explicitly formatted for web GUI visualization (Chart.js / Plotly / Canvas).
    """
    total_len = len(iq_samples)
    if total_len == 0:
        return {
            "spectrum_db": [],
            "frequencies_hz": [],
            "constellation_i": [],
            "constellation_q": [],
            "waterfall_db": [],
            "snr_db": 0.0,
            "rms_power_dbfs": -100.0,
        }

    # 1. Spectrum Line Data
    actual_fft = min(fft_size, total_len)
    # Ensure power of 2 for FFT speed
    actual_fft = 1 << int(np.floor(np.log2(max(16, actual_fft))))
    windowed = iq_samples[:actual_fft] * np.hanning(actual_fft)
    fft_data = np.fft.fftshift(np.fft.fft(windowed))
    spectrum_db = (20.0 * np.log10(np.abs(fft_data) / actual_fft + 1e-12)).tolist()
    freq_bins = np.fft.fftshift(np.fft.fftfreq(actual_fft)).tolist()

    # 2. Constellation Points (uniform downsampling for crisp display)
    max_pts = 400
    if total_len > max_pts:
        step = total_len // max_pts
        sampled = iq_samples[::step][:max_pts]
    else:
        sampled = iq_samples

    constellation_i = np.real(sampled).tolist()
    constellation_q = np.imag(sampled).tolist()

    # 3. Waterfall Spectrogram (Time x Frequency matrix)
    waterfall_matrix = []
    frame_size = actual_fft
    hop_size = max(1, (total_len - frame_size) // max(1, waterfall_frames))
    for f in range(waterfall_frames):
        start = f * hop_size
        if start + frame_size > total_len:
            break
        chunk = iq_samples[start : start + frame_size] * np.hanning(frame_size)
        spec = np.fft.fftshift(np.fft.fft(chunk))
        db_slice = (20.0 * np.log10(np.abs(spec) / frame_size + 1e-12)).tolist()
        waterfall_matrix.append(db_slice)

    # 4. Signal metrics (RMS, Peak, Estimated SNR)
    sig_mag = np.abs(iq_samples)
    rms = float(np.sqrt(np.mean(sig_mag ** 2)))
    rms_dbfs = float(20.0 * np.log10(rms + 1e-12))
    sorted_spec = np.sort(np.array(spectrum_db))
    noise_est = float(np.mean(sorted_spec[: max(1, len(sorted_spec) // 4)]))
    peak_est = float(np.max(sorted_spec))
    snr_est = max(0.0, float(peak_est - noise_est))

    return {
        "spectrum_db": spectrum_db,
        "frequencies_norm": freq_bins,
        "constellation_i": constellation_i,
        "constellation_q": constellation_q,
        "waterfall_db": waterfall_matrix,
        "snr_db": round(snr_est, 2),
        "rms_power_dbfs": round(rms_dbfs, 2),
    }


# ==============================================================================
# 7. PYDANTIC REQUEST / RESPONSE SCHEMAS
# ==============================================================================

class ModulateRequest(BaseModel):
    bits: Optional[List[int]] = Field(default=None, description="Bit sequence [0, 1, ...]. If omitted, text or random bits are generated")
    text: Optional[str] = Field(default=None, description="Optional ASCII text to encode into bits")
    modulation: str = Field(default="QPSK", description="Modulation scheme: BPSK, QPSK, 8PSK, 16QAM, BFSK, 4FSK")
    sps: int = Field(default=4, ge=1, le=32, description="Samples per symbol")
    pulse_shape: str = Field(default="rrc", description="Pulse shape: 'rrc' or 'rect'")
    alpha: float = Field(default=0.35, ge=0.0, le=1.0, description="RRC excess bandwidth factor")
    cfo_hz: float = Field(default=0.0, description="Carrier Frequency Offset to inject in Hz")
    phase_offset_deg: float = Field(default=0.0, description="Initial carrier phase offset in degrees")
    snr_db: Optional[float] = Field(default=None, description="Additive White Gaussian Noise (SNR in dB)")
    samp_rate: float = Field(default=1e6, gt=0, description="Sample rate in Hz")


class SynchronizeRequest(BaseModel):
    samples_i: List[float] = Field(..., description="In-phase real components")
    samples_q: List[float] = Field(..., description="Quadrature imaginary components")
    samp_rate: float = Field(default=1e6, gt=0, description="Sample rate in Hz")
    sps: int = Field(default=4, ge=1, description="Samples per symbol")
    modulation: str = Field(default="QPSK", description="Modulation type")
    sync_marker: str = Field(default="Barker-11", description="Sync marker: Barker-7, Barker-11, Barker-13")


class DemodulateRequest(BaseModel):
    samples_i: List[float] = Field(..., description="In-phase real components")
    samples_q: List[float] = Field(..., description="Quadrature imaginary components")
    modulation: str = Field(default="QPSK", description="Modulation type")
    sps: int = Field(default=4, ge=1, description="Samples per symbol")
    apply_sync: bool = Field(default=True, description="Whether to apply CFO and symbol timing sync before slicing")


class FECRequest(BaseModel):
    bits: List[int] = Field(..., description="Encoded bitstream")
    code_type: str = Field(default="Viterbi", description="FEC code type: Viterbi, Hamming")


class InterleaveRequest(BaseModel):
    bits: List[int] = Field(..., description="Bitstream")
    scheme: str = Field(default="Block", description="Scheme: Block, Pseudorandom, Diagonal")
    matrix_size: int = Field(default=4, ge=2, description="Block matrix dimension (e.g. 4x4)")
    seed: int = Field(default=42, description="Random seed for Pseudorandom scheme")


# ==============================================================================
# 8. API ENDPOINTS
# ==============================================================================

@app.get("/", summary="API Root & Status")
async def root():
    return {
        "service": "SIGMA RF Intelligence API",
        "version": "2.0.0",
        "status": "online",
        "torch_accelerated": TORCH_AVAILABLE,
        "capabilities": {
            "modulations": list(CONSTELLATIONS.keys()) + ["BFSK", "4FSK"],
            "synchronization": ["CFO 4th-power / Squaring", "RRC Matched Filter + Eye Timing", "Barker Frame Correlation"],
            "interleaving": ["Matrix Block (NxN)", "Convolutional / Diagonal", "Pseudo-Random"],
            "fec_decoders": ["Convolutional (Viterbi Rate 1/2 K=3)", "Hamming (7, 4)"],
        },
        "endpoints": {
            "swagger_docs": "/docs",
            "redoc": "/redoc",
            "analyze_signal": "POST /api/analyze_advanced",
            "modulate": "POST /api/modulate",
            "synchronize": "POST /api/synchronize",
            "demodulate": "POST /api/demodulate",
            "deinterleave": "POST /api/deinterleave",
            "fec_decode": "POST /api/fec_decode",
        }
    }


@app.get("/health", summary="Health Check")
async def health_check():
    return {
        "status": "healthy",
        "torch_available": TORCH_AVAILABLE,
        "numpy_version": np.__version__,
        "scipy_version": signal.__package__,
    }


@app.post("/api/analyze_advanced", summary="Comprehensive Signal Intelligence Analysis Pipeline")
async def analyze_advanced_signal(
    file: UploadFile = File(...),
    samp_rate: float = Form(1e6),
    modulation: Optional[str] = Form(None),
    sps: int = Form(4),
    fec_scheme: str = Form("Viterbi"),
    interleaving_type: str = Form("Block"),
):
    """
    Processes an uploaded raw IQ binary file through the entire SIGMA pipeline:
    1. Spectral & GUI visualization extraction (Spectrum dB, Constellation, Waterfall)
    2. Carrier Frequency Offset (CFO) compensation & Carrier Recovery
    3. Symbol Timing Synchronization & Clock Recovery
    4. Demodulation into bitstream with EVM assessment
    5. De-interleaving (Matrix Block / Pseudorandom / Diagonal)
    6. Forward Error Correction (FEC) decoding (Viterbi / Hamming)
    7. Frame Synchronization & Header/Payload correlation
    """
    temp_filename = f"upload_{os.urandom(8).hex()}_{file.filename}"
    file_path = os.path.join(UPLOAD_FOLDER, temp_filename)
    try:
        # Save uploaded file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Parse raw bytes to complex64 / float32 IQ samples
        raw_data = np.fromfile(file_path, dtype=np.float32)
        if len(raw_data) < 2:
            raise HTTPException(status_code=400, detail="Uploaded file is empty or has fewer than 2 float32 values.")

        # Real and Imag interleaved (I0, Q0, I1, Q1, ...)
        iq_samples = raw_data[0::2] + 1j * raw_data[1::2]
        total_samples = len(iq_samples)

        # 1. EXTRACT SPECTRUM, WATERFALL & CONSTELLATION GRAPHS
        spectral_data = extract_spectral_gui_data(iq_samples, fft_size=512, waterfall_frames=16)

        # 2. AUTO-DETECT OR USE SPECIFIED MODULATION
        detected_mod = modulation.upper() if modulation else "QPSK"
        if detected_mod not in CONSTELLATIONS and "FSK" not in detected_mod:
            detected_mod = "QPSK"

        # 3. CARRIER & CLOCK SYNCHRONIZATION
        cfo_corrected, estimated_cfo = estimate_and_correct_cfo(
            iq_samples[:min(total_samples, 16384)],
            samp_rate=samp_rate,
            mod_type=detected_mod,
        )
        recovered_symbols, best_phase = symbol_timing_sync(
            cfo_corrected,
            sps=sps,
            mod_type=detected_mod,
        )
        derotated_symbols, phase_correction = carrier_phase_recovery(
            recovered_symbols,
            mod_type=detected_mod,
        )

        # 4. DEMODULATION (Symbols -> Bits + EVM)
        demod_bits, evm_percent, _ = soft_demodulate_symbols(derotated_symbols, detected_mod)

        # 5. DE-INTERLEAVING
        cleaned_bits = run_deinterleaver(demod_bits, scheme=interleaving_type, matrix_size=4)

        # 6. FORWARD ERROR CORRECTION (FEC)
        fec_result = run_fec_decoder(cleaned_bits, code_type=fec_scheme)
        final_bits = fec_result.get("decoded_bits", cleaned_bits)

        # 7. BITSTREAM CORRELATION (Barker code sync marker, Header & Payload)
        correlation_results = run_bitstream_correlation(final_bits, marker_name="Barker-11")

        # Cleanup temporary uploaded file
        if os.path.exists(file_path):
            os.remove(file_path)

        return {
            "status": "success",
            "file_info": {
                "filename": file.filename,
                "total_iq_samples": total_samples,
                "duration_seconds": round(total_samples / samp_rate, 4),
            },
            "extracted_parameters": {
                "estimated_sampling_rate": f"{samp_rate / 1e6:.2f} Msps",
                "modulation": detected_mod,
                "samples_per_symbol": sps,
                "estimated_cfo_hz": round(estimated_cfo, 2),
                "phase_correction_deg": round(phase_correction, 2),
                "evm_percent": round(evm_percent, 2),
                "snr_estimate_db": spectral_data["snr_db"],
                "fec_scheme": fec_result.get("fec_type", fec_scheme),
                "fec_errors_corrected": fec_result.get("errors_corrected", 0),
                "interleaving_type": interleaving_type,
            },
            "gui_plots": {
                "spectrum_db": spectral_data["spectrum_db"],
                "frequencies_norm": spectral_data["frequencies_norm"],
                "constellation_i": spectral_data["constellation_i"],
                "constellation_q": spectral_data["constellation_q"],
                "waterfall_db": spectral_data["waterfall_db"],
                "rms_power_dbfs": spectral_data["rms_power_dbfs"],
            },
            "bitstream_extraction": correlation_results,
        }

    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/modulate", summary="Modulate Bits into Baseband IQ Samples")
async def api_modulate(req: ModulateRequest):
    """
    Generates a modulated IQ signal from input bits or text string.
    Applies pulse shaping (RRC), optional CFO, phase offset, and AWGN noise.
    """
    try:
        # Determine bit source
        if req.bits is not None and len(req.bits) > 0:
            bits = req.bits
        elif req.text:
            bits = []
            for char in req.text:
                val = ord(char)
                for b in range(7, -1, -1):
                    bits.append((val >> b) & 1)
        else:
            # Default test sequence with Barker 11 preamble
            barker11 = [1, 1, 1, 0, 0, 0, 1, 0, 0, 1, 0]
            payload = [int(b) for b in np.random.randint(0, 2, size=128)]
            bits = barker11 + payload

        iq_samples = modulate_bitstream(
            bits=bits,
            mod_type=req.modulation,
            sps=req.sps,
            pulse_shape=req.pulse_shape,
            alpha=req.alpha,
            cfo_hz=req.cfo_hz,
            phase_offset_deg=req.phase_offset_deg,
            snr_db=req.snr_db,
            samp_rate=req.samp_rate,
        )

        spectral = extract_spectral_gui_data(iq_samples, fft_size=512)

        return {
            "status": "success",
            "modulation": req.modulation,
            "total_bits": len(bits),
            "total_samples": len(iq_samples),
            "sps": req.sps,
            "samples_i": np.real(iq_samples[:500]).tolist(),
            "samples_q": np.imag(iq_samples[:500]).tolist(),
            "gui_plots": spectral,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/synchronize", summary="Apply Carrier, Clock, and Frame Synchronization")
async def api_synchronize(req: SynchronizeRequest):
    """
    Applies telecom synchronization to raw IQ samples:
    - Carrier Frequency Offset estimation and de-rotation
    - Matched RRC filter & Optimum eye-sampling phase decimation
    - Residual phase correction
    - Barker code frame boundary synchronization
    """
    try:
        iq_samples = np.array(req.samples_i, dtype=np.float32) + 1j * np.array(req.samples_q, dtype=np.float32)
        if len(iq_samples) == 0:
            raise HTTPException(status_code=400, detail="Empty IQ sample arrays.")

        # 1. Carrier Frequency Sync
        cfo_corrected, estimated_cfo = estimate_and_correct_cfo(
            iq_samples, samp_rate=req.samp_rate, mod_type=req.modulation
        )

        # 2. Symbol Timing Recovery (Decimation to 1 SPS at optimum phase)
        recovered_symbols, best_phase = symbol_timing_sync(
            cfo_corrected, sps=req.sps, mod_type=req.modulation
        )

        # 3. Residual Phase Recovery
        derotated_symbols, phase_deg = carrier_phase_recovery(
            recovered_symbols, mod_type=req.modulation
        )

        # 4. Slicing & Frame Sync
        bits, evm, _ = soft_demodulate_symbols(derotated_symbols, req.modulation)
        corr_results = run_bitstream_correlation(bits, marker_name=req.sync_marker)

        return {
            "status": "success",
            "synchronization_results": {
                "estimated_cfo_hz": round(estimated_cfo, 2),
                "optimal_sampling_phase": best_phase,
                "residual_phase_deg": round(phase_deg, 2),
                "evm_percent": round(evm, 2),
                "frame_sync": corr_results,
            },
            "recovered_symbols": {
                "count": len(derotated_symbols),
                "symbols_i": np.real(derotated_symbols[:200]).tolist(),
                "symbols_q": np.imag(derotated_symbols[:200]).tolist(),
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/demodulate", summary="Demodulate Baseband IQ into Hard/Soft Bits")
async def api_demodulate(req: DemodulateRequest):
    """
    Demodulates IQ samples with optional synchronization.
    Computes Error Vector Magnitude (EVM) and returns bits.
    """
    try:
        iq_samples = np.array(req.samples_i, dtype=np.float32) + 1j * np.array(req.samples_q, dtype=np.float32)
        if len(iq_samples) == 0:
            raise HTTPException(status_code=400, detail="Empty IQ sample arrays.")

        if req.apply_sync and req.sps > 1:
            cfo_corr, _ = estimate_and_correct_cfo(iq_samples, mod_type=req.modulation)
            syms, _ = symbol_timing_sync(cfo_corr, sps=req.sps, mod_type=req.modulation)
            derotated, _ = carrier_phase_recovery(syms, mod_type=req.modulation)
        else:
            derotated = iq_samples

        bits, evm_percent, soft_llrs = soft_demodulate_symbols(derotated, req.modulation)

        return {
            "status": "success",
            "modulation": req.modulation,
            "evm_percent": round(evm_percent, 2),
            "num_symbols": len(derotated),
            "num_bits": len(bits),
            "bits": bits[:256],
            "soft_llrs": soft_llrs[:128],
            "bits_string": "".join(str(b) for b in bits[:128]),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/deinterleave", summary="De-interleave a Bitstream")
async def api_deinterleave(req: InterleaveRequest):
    """
    De-interleaves a bit sequence to disperse burst errors.
    Supports 'Block', 'Pseudorandom', and 'Diagonal'.
    """
    try:
        cleaned = run_deinterleaver(
            req.bits,
            scheme=req.scheme,
            matrix_size=req.matrix_size,
            seed=req.seed,
        )
        return {
            "status": "success",
            "scheme": req.scheme,
            "matrix_size": req.matrix_size,
            "input_bits_count": len(req.bits),
            "output_bits": cleaned,
            "output_bits_string": "".join(str(b) for b in cleaned),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/fec_decode", summary="Decode Bitstream with Forward Error Correction")
async def api_fec_decode(req: FECRequest):
    """
    Decodes bitstreams using Viterbi (Convolutional Rate 1/2) or Hamming (7, 4).
    """
    try:
        result = run_fec_decoder(req.bits, code_type=req.code_type)
        return {
            "status": "success",
            "fec_type": result.get("fec_type"),
            "errors_corrected": result.get("errors_corrected", 0),
            "decoded_bits": result.get("decoded_bits", []),
            "decoded_bits_string": "".join(str(b) for b in result.get("decoded_bits", [])),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==============================================================================
# 5. NEW SIH RECOVERY & INTELLIGENCE API ENDPOINTS
# ==============================================================================

# In-memory storage for analysis results
ANALYSIS_CACHE: Dict[str, Any] = {}


class DemodulateRequest(BaseModel):
    samples_i: Optional[List[float]] = None
    samples_q: Optional[List[float]] = None
    sample_rate: float = 1000000.0
    modulation: str = "BPSK"
    symbol_rate: Optional[float] = None
    sps: Optional[float] = None


class DeinterleaveRequest(BaseModel):
    bits: List[int]
    mode: str = "block"
    parameters: Optional[Dict[str, Any]] = None


class FECDecodeRequest(BaseModel):
    bits: List[int]
    fec_type: Optional[str] = "convolutional"
    parameters: Optional[Dict[str, Any]] = None


class CorrelateRequest(BaseModel):
    bits_a: List[int]
    bits_b: Optional[List[int]] = None
    sync_patterns: Optional[Dict[str, Any]] = None


class RecoverRequest(BaseModel):
    filepath: Optional[str] = None
    sample_rate: Optional[float] = 1000000.0
    center_freq: float = 0.0
    forced_modulation: Optional[str] = None
    interleave_mode: Optional[str] = None
    fec_type: Optional[str] = None


@app.post("/analyze", summary="Analyze IQ or WAV Signal File")
async def post_analyze(
    file: Optional[UploadFile] = File(None),
    filepath: Optional[str] = Form(None),
    sample_rate: float = Form(1000000.0),
    center_freq: float = Form(0.0)
):
    import uuid
    from sigma_analyzer_core import SignalMetadata

    target_path = filepath
    if file is not None:
        save_name = f"{uuid.uuid4().hex}_{file.filename}"
        target_path = os.path.join(UPLOAD_FOLDER, save_name)
        with open(target_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

    if not target_path or not os.path.exists(target_path):
        raise HTTPException(status_code=400, detail="Valid file or filepath is required")

    meta = SignalMetadata(filepath=target_path, samp_rate=sample_rate, center_freq=center_freq)
    aid = uuid.uuid4().hex[:12]
    res_dict = {
        "analysis_id": aid,
        "filename": meta.filename,
        "sample_rate": meta.samp_rate,
        "center_freq": meta.center_freq,
        "snr": meta.snr,
        "noise_floor": meta.noise_floor,
        "signal_power": meta.signal_power_dbfs,
        "peak_frequency": meta.peak_frequency,
        "symbol_rate": meta.symbol_rate,
        "samples_per_symbol": meta.samples_per_symbol,
        "modulation_class": meta.modulation_class,
        "modulation_source": meta.modulation_source,
    }
    ANALYSIS_CACHE[aid] = res_dict
    return res_dict


@app.post("/demodulate", summary="Demodulate Signal Samples")
async def post_demodulate(req: DemodulateRequest):
    from recovery.demodulators import demodulate

    if not req.samples_i or not req.samples_q:
        raise HTTPException(status_code=400, detail="samples_i and samples_q are required")

    i_arr = np.asarray(req.samples_i, dtype=np.float32)
    q_arr = np.asarray(req.samples_q, dtype=np.float32)
    iq_signal = (i_arr + 1j * q_arr).astype(np.complex64)

    out = demodulate(
        iq_signal,
        modulation=req.modulation,
        sample_rate=req.sample_rate,
        symbol_rate=req.symbol_rate,
        sps=req.sps,
    )
    return out


@app.post("/deinterleave", summary="De-interleave Bitstream")
async def post_deinterleave(req: DeinterleaveRequest):
    from deinterleaving.dispatcher import deinterleave

    out = deinterleave(req.bits, mode=req.mode, parameters=req.parameters)
    return out


@app.post("/fec/decode", summary="Decode Bitstream with Forward Error Correction")
async def post_fec_decode(req: FECDecodeRequest):
    from fec.dispatcher import decode_fec

    out = decode_fec(req.bits, fec_type=req.fec_type, parameters=req.parameters)
    return out


@app.post("/correlate", summary="Correlate Bitstream & Find Headers")
async def post_correlate(req: CorrelateRequest):
    from correlation.scoring import correlate_bitstreams

    out = correlate_bitstreams(
        req.bits_a,
        stream_b=req.bits_b,
        sync_patterns=req.sync_patterns
    )
    return out


@app.post("/recover", summary="Run Full End-to-End Recovery Pipeline")
async def post_recover(
    file: Optional[UploadFile] = File(None),
    filepath: Optional[str] = Form(None),
    sample_rate: float = Form(1000000.0),
    center_freq: float = Form(0.0),
    modulation: Optional[str] = Form(None),
    interleave_mode: Optional[str] = Form(None),
    fec_type: Optional[str] = Form(None),
):
    import uuid
    from sigma_recovery import orchestrate_signal_recovery

    target_path = filepath
    if file is not None:
        save_name = f"{uuid.uuid4().hex}_{file.filename}"
        target_path = os.path.join(UPLOAD_FOLDER, save_name)
        with open(target_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

    if not target_path or not os.path.exists(target_path):
        # Default fallback to demo file if none provided
        demo_candidate = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "iq", "demo_bpsk_100ksps_1msps.iq")
        if os.path.exists(demo_candidate):
            target_path = demo_candidate
        else:
            raise HTTPException(status_code=400, detail="File or valid filepath required")

    result = orchestrate_signal_recovery(
        input_path=target_path,
        user_sample_rate=sample_rate,
        user_center_freq=center_freq,
        forced_modulation=modulation,
        interleave_mode=interleave_mode,
        fec_type=fec_type,
    )

    aid = uuid.uuid4().hex[:12]
    out_dict = result.to_dict()
    out_dict["analysis_id"] = aid
    ANALYSIS_CACHE[aid] = out_dict
    return out_dict


@app.get("/analysis/{analysis_id}", summary="Get Stored Analysis Result")
async def get_analysis(analysis_id: str):
    if analysis_id not in ANALYSIS_CACHE:
        raise HTTPException(status_code=404, detail="Analysis result not found")
    return ANALYSIS_CACHE[analysis_id]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
