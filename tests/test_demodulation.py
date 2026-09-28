"""
Unit tests for Demodulation (FSK, BPSK, QPSK, 16QAM).
"""

import os
import sys
import unittest
import numpy as np

src_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from recovery.demodulators import demodulate, demodulate_fsk, demodulate_psk, demodulate_qam
from recovery.bit_mapper import symbols_to_bits, bits_to_symbols, CONSTELLATIONS


class TestDemodulation(unittest.TestCase):

    def setUp(self):
        self.rng = np.random.default_rng(42)
        self.samp_rate = 1000000.0

    def test_bit_mapper_invertibility(self):
        for mod in ["BPSK", "QPSK", "8PSK", "16QAM", "BFSK"]:
            bits_tx = self.rng.integers(0, 2, 240, dtype=np.uint8)
            syms = bits_to_symbols(bits_tx, modulation=mod)
            bits_rx, _, evm = symbols_to_bits(syms, modulation=mod)
            self.assertEqual(len(bits_rx), len(bits_tx))
            np.testing.assert_array_equal(bits_rx, bits_tx, f"Mismatch in {mod} bit mapper")
            self.assertLess(evm, 1e-4)

    def test_bpsk_demodulation(self):
        num_symbols = 500
        bits = self.rng.integers(0, 2, num_symbols, dtype=np.uint8)
        sps = 4
        syms = (2 * bits - 1).astype(np.complex64)
        upsampled = np.zeros(num_symbols * sps, dtype=np.complex64)
        upsampled[::sps] = syms

        # Light noise
        noise = (self.rng.normal(0, 0.05, len(upsampled)) + 1j * self.rng.normal(0, 0.05, len(upsampled)))
        rx = upsampled + noise

        out = demodulate(rx, modulation="BPSK", sample_rate=self.samp_rate, sps=sps)
        diag = out.get("diagnostics", {})
        self.assertTrue(diag.get("locked"))
        self.assertEqual(out.get("modulation"), "BPSK")
        self.assertGreater(len(out.get("bits", [])), 100)

    def test_qpsk_demodulation(self):
        num_symbols = 400
        bits = self.rng.integers(0, 2, num_symbols * 2, dtype=np.uint8)
        sps = 4
        syms = bits_to_symbols(bits, modulation="QPSK")
        upsampled = np.zeros(num_symbols * sps, dtype=np.complex64)
        upsampled[::sps] = syms

        noise = (self.rng.normal(0, 0.05, len(upsampled)) + 1j * self.rng.normal(0, 0.05, len(upsampled)))
        rx = upsampled + noise

        out = demodulate(rx, modulation="QPSK", sample_rate=self.samp_rate, sps=sps)
        diag = out.get("diagnostics", {})
        self.assertTrue(diag.get("locked"))
        self.assertEqual(out.get("modulation"), "QPSK")
        self.assertGreater(len(out.get("bits", [])), 100)

    def test_fsk_demodulation(self):
        num_symbols = 300
        bits = self.rng.integers(0, 2, num_symbols, dtype=np.uint8)
        sps = 8
        dev_hz = 25000.0
        freqs = np.where(bits == 1, dev_hz, -dev_hz)
        inst_f = np.repeat(freqs, sps)
        phase = 2.0 * np.pi * np.cumsum(inst_f) / self.samp_rate
        rx = np.exp(1j * phase).astype(np.complex64)

        out = demodulate(rx, modulation="BFSK", sample_rate=self.samp_rate, sps=sps)
        diag = out.get("diagnostics", {})
        self.assertTrue(diag.get("locked"))
        self.assertIn("FSK", out.get("modulation"))
        self.assertGreater(len(out.get("bits", [])), 100)

    def test_qam_demodulation(self):
        num_symbols = 300
        bits = self.rng.integers(0, 2, num_symbols * 4, dtype=np.uint8)
        sps = 4
        syms = bits_to_symbols(bits, modulation="16QAM")
        upsampled = np.zeros(num_symbols * sps, dtype=np.complex64)
        upsampled[::sps] = syms

        noise = (self.rng.normal(0, 0.02, len(upsampled)) + 1j * self.rng.normal(0, 0.02, len(upsampled)))
        rx = upsampled + noise

        out = demodulate(rx, modulation="16QAM", sample_rate=self.samp_rate, sps=sps)
        diag = out.get("diagnostics", {})
        self.assertTrue(diag.get("locked"))
        self.assertEqual(out.get("modulation"), "16QAM")
        self.assertGreater(len(out.get("bits", [])), 100)


if __name__ == "__main__":
    unittest.main()
