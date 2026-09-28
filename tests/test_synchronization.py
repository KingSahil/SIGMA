"""
Unit tests for Synchronization (timing recovery, carrier offset, phase alignment).
"""

import os
import sys
import unittest
import numpy as np

src_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from recovery.synchronizer import (
    estimate_frequency_offset,
    estimate_symbol_timing,
    phase_align,
)
from recovery.bit_mapper import CONSTELLATIONS


class TestSynchronization(unittest.TestCase):

    def setUp(self):
        self.rng = np.random.default_rng(101)
        self.samp_rate = 1000000.0

    def test_frequency_offset_estimation(self):
        # Generate BPSK with +12,500 Hz carrier offset
        true_offset = 12500.0
        n_samples = 4096
        bits = self.rng.integers(0, 2, n_samples)
        bipolar = (2 * bits - 1).astype(np.complex128)
        t = np.arange(n_samples) / self.samp_rate
        rx = bipolar * np.exp(1j * 2.0 * np.pi * true_offset * t)

        est_offset = estimate_frequency_offset(rx, self.samp_rate, symmetry_order=2)
        self.assertAlmostEqual(est_offset, true_offset, delta=200.0)

    def test_symbol_timing_estimation(self):
        n_syms = 200
        sps = 4
        bits = self.rng.integers(0, 2, n_syms)
        upsampled = np.zeros(n_syms * sps, dtype=np.complex128)
        upsampled[::sps] = 2 * bits - 1

        est_sps, phase, diag = estimate_symbol_timing(upsampled, self.samp_rate, sps=sps)
        self.assertEqual(est_sps, 4.0)
        self.assertEqual(phase, 0)

    def test_phase_align(self):
        # 45 degree rotation of QPSK constellation
        qpsk_const = CONSTELLATIONS["QPSK"]
        syms = self.rng.choice(qpsk_const, size=200)
        rot_angle = np.pi / 4.0  # 45 deg
        rotated_syms = syms * np.exp(1j * rot_angle)

        aligned, deg = phase_align(rotated_syms, qpsk_const, symmetry_order=4)
        self.assertIsNotNone(aligned)
        diff = np.min(np.abs(aligned[:, None] - qpsk_const[None, :]), axis=1)
        self.assertLess(float(np.mean(diff)), 0.05)


if __name__ == "__main__":
    unittest.main()
