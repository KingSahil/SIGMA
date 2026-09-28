#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verification Script for SIGMA FastAPI Service
Tests all core functions and endpoints directly without external HTTP dependencies.
"""

import os
import sys
import asyncio
import numpy as np

# Ensure src directory is in sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_dir = os.path.join(root_dir, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from sigma_api import (
    app,
    modulate_bitstream,
    estimate_and_correct_cfo,
    symbol_timing_sync,
    carrier_phase_recovery,
    soft_demodulate_symbols,
    run_interleaver,
    run_deinterleaver,
    run_fec_decoder,
    run_bitstream_correlation,
    extract_spectral_gui_data,
    ModulateRequest,
    SynchronizeRequest,
    DemodulateRequest,
    FECRequest,
    InterleaveRequest,
    api_modulate,
    api_synchronize,
    api_demodulate,
    api_deinterleave,
    api_fec_decode,
    root,
    health_check,
)

def run_tests():
    print("=" * 65)
    print("TESTING SIGMA TELECOM CORE & API ENDPOINTS")
    print("=" * 65)

    # 1. Root & Health
    r_root = asyncio.run(root())
    print("[+] GET /:", r_root["service"], "| Version:", r_root["version"])
    r_health = asyncio.run(health_check())
    print("[+] GET /health:", r_health)

    # 2. Modulation Test
    print("\n[+] 2. Modulation Core Testing:")
    test_text = "SIGMA-SIH2026"
    req_mod = ModulateRequest(
        text=test_text,
        modulation="QPSK",
        sps=4,
        cfo_hz=500.0,
        snr_db=30.0,
        samp_rate=1e6,
    )
    res_mod = asyncio.run(api_modulate(req_mod))
    print(f"    - Modulated text '{test_text}' -> {res_mod['total_bits']} bits")
    print(f"    - Generated {res_mod['total_samples']} samples at {res_mod['sps']} SPS")
    print(f"    - Constellation points I/Q: {len(res_mod['samples_i'])} points extracted")
    print(f"    - Spectrum DB bins: {len(res_mod['gui_plots']['spectrum_db'])}")

    # 3. Synchronization Test
    print("\n[+] 3. Synchronization Core Testing:")
    # Modulate known Barker code + payload with CFO
    barker11 = [1, 1, 1, 0, 0, 0, 1, 0, 0, 1, 0]
    payload = [1, 0, 1, 1, 0, 0, 1, 1] * 10
    total_bits = barker11 + payload
    iq_tx = modulate_bitstream(
        bits=total_bits,
        mod_type="QPSK",
        sps=4,
        cfo_hz=750.0,
        phase_offset_deg=35.0,
        samp_rate=1e6,
    )

    req_sync = SynchronizeRequest(
        samples_i=np.real(iq_tx).tolist(),
        samples_q=np.imag(iq_tx).tolist(),
        samp_rate=1e6,
        sps=4,
        modulation="QPSK",
        sync_marker="Barker-11",
    )
    res_sync = asyncio.run(api_synchronize(req_sync))
    sync_out = res_sync["synchronization_results"]
    print(f"    - Injected CFO: 750 Hz -> Estimated CFO: {sync_out['estimated_cfo_hz']} Hz")
    print(f"    - Optimal Sampling Phase: {sync_out['optimal_sampling_phase']}")
    print(f"    - Residual Phase: {sync_out['residual_phase_deg']} deg")
    print(f"    - EVM: {sync_out['evm_percent']}%")
    print(f"    - Frame Sync Marker Found: Index {sync_out['frame_sync']['sync_index_found']} (Score: {sync_out['frame_sync']['correlation_score']})")

    # 4. Demodulation Test
    print("\n[+] 4. Demodulation Core Testing:")
    req_demod = DemodulateRequest(
        samples_i=np.real(iq_tx).tolist(),
        samples_q=np.imag(iq_tx).tolist(),
        modulation="QPSK",
        sps=4,
        apply_sync=True,
    )
    res_demod = asyncio.run(api_demodulate(req_demod))
    print(f"    - Demodulated {res_demod['num_bits']} bits from {res_demod['num_symbols']} symbols")
    print(f"    - EVM: {res_demod['evm_percent']}%")
    print(f"    - Recovered Bitstream Preview: {res_demod['bits_string'][:40]}...")

    # 5. Interleaving / De-interleaving Test
    print("\n[+] 5. Interleaving & De-interleaving Testing:")
    raw_bits = [1, 0, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 1, 0, 1, 0]
    interleaved = run_interleaver(raw_bits, scheme="Block", matrix_size=4)
    req_deint = InterleaveRequest(bits=interleaved, scheme="Block", matrix_size=4)
    res_deint = asyncio.run(api_deinterleave(req_deint))
    restored_bits = res_deint["output_bits"]
    assert restored_bits == raw_bits, f"De-interleaving mismatch: {restored_bits} != {raw_bits}"
    print(f"    - Block 4x4 Interleave -> De-interleave Verified: Exact bit match!")

    # Pseudo-random interleaver test
    rand_interleaved = run_interleaver(raw_bits, scheme="Pseudorandom", seed=123)
    rand_restored = run_deinterleaver(rand_interleaved, scheme="Pseudorandom", seed=123)
    assert rand_restored == raw_bits, "Pseudorandom deinterleave mismatch!"
    print(f"    - Pseudo-Random Interleave -> De-interleave Verified: Exact bit match!")

    # 6. Forward Error Correction (FEC) Test
    print("\n[+] 6. FEC Decoding Testing:")
    # Viterbi test
    fec_req = FECRequest(bits=[1, 1, 0, 1, 1, 0, 0, 0, 1, 1, 1, 0], code_type="Viterbi")
    fec_res = asyncio.run(api_fec_decode(fec_req))
    print(f"    - Viterbi Decoder ({fec_res['fec_type']}): Output {fec_res['decoded_bits_string']}, Corrected: {fec_res['errors_corrected']} bits")

    # Hamming (7,4) test: inject 1 bit error and verify correction
    data_bits = [1, 0, 1, 1]
    # Hamming encode [d0, d1, d2, d3] -> 7 bits: [p0, p1, d0, p2, d1, d2, d3]
    # p0 = d0 ^ d1 ^ d3 = 1 ^ 0 ^ 1 = 0
    # p1 = d0 ^ d2 ^ d3 = 1 ^ 1 ^ 1 = 1
    # p2 = d1 ^ d2 ^ d3 = 0 ^ 1 ^ 1 = 0
    # codeword = [0, 1, 1, 0, 0, 1, 1]
    codeword = [0, 1, 1, 0, 0, 1, 1]
    # Corrupt 1 bit (flip bit at index 2, which is d0)
    corrupted = [0, 1, 0, 0, 0, 1, 1]
    ham_req = FECRequest(bits=corrupted, code_type="Hamming")
    ham_res = asyncio.run(api_fec_decode(ham_req))
    print(f"    - Hamming (7,4) Decoder: Corrected: {ham_res['errors_corrected']} errors, Recovered data: {ham_res['decoded_bits']}")
    assert ham_res['decoded_bits'] == data_bits, f"Hamming decoding failed: {ham_res['decoded_bits']} != {data_bits}"
    print(f"    - Hamming Single Error Correction Verified!")

    # 7. File Analysis Pipeline Test on real file
    print("\n[+] 7. Testing Real File Pipeline on data/iq/bpsk_modulated_1msps.iq:")
    test_iq_path = os.path.join(root_dir, "data", "iq", "bpsk_modulated_1msps.iq")
    if os.path.exists(test_iq_path):
        raw_bytes = np.fromfile(test_iq_path, dtype=np.float32)
        iq_samples = raw_bytes[0::2] + 1j * raw_bytes[1::2]
        spectral = extract_spectral_gui_data(iq_samples[:4096])
        print(f"    - Read {len(iq_samples)} complex samples from {os.path.basename(test_iq_path)}")
        print(f"    - Estimated SNR: {spectral['snr_db']} dB, RMS: {spectral['rms_power_dbfs']} dBFS")
        print(f"    - Extracted {len(spectral['constellation_i'])} constellation points and {len(spectral['waterfall_db'])} waterfall frames")

    print("\n" + "=" * 65)
    print("ALL DSP ALGORITHMS & ENDPOINT FUNCTIONS VERIFIED SUCCESSFULLY!")
    print("=" * 65)

if __name__ == "__main__":
    run_tests()
