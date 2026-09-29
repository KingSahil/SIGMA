"""
Unit tests for De-interleaving modes (Block, Convolutional, Diagonal, Pseudo-Random).
"""

import os
import sys
import unittest
import numpy as np

src_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from deinterleaving.block import block_interleave, block_deinterleave
from deinterleaving.convolutional import convolutional_interleave, convolutional_deinterleave
from deinterleaving.diagonal import diagonal_interleave, diagonal_deinterleave
from deinterleaving.pseudo_random import pseudo_random_interleave, pseudo_random_deinterleave
from deinterleaving.dispatcher import deinterleave


class TestDeinterleaving(unittest.TestCase):

    def setUp(self):
        self.rng = np.random.default_rng(202)
        self.bits = self.rng.integers(0, 2, 256, dtype=np.uint8)

    def test_block_invertibility(self):
        rows, cols = 16, 16
        interleaved = block_interleave(self.bits, rows=rows, cols=cols)
        # Should scramble bits
        self.assertFalse(np.array_equal(interleaved, self.bits))
        deinterleaved = block_deinterleave(interleaved, rows=rows, cols=cols)
        np.testing.assert_array_equal(deinterleaved, self.bits)

    def test_convolutional_invertibility(self):
        S, j = 8, 2
        interleaved = convolutional_interleave(self.bits, S=S, j=j)
        self.assertFalse(np.array_equal(interleaved, self.bits))
        deinterleaved = convolutional_deinterleave(interleaved, S=S, j=j)
        np.testing.assert_array_equal(deinterleaved, self.bits)

    def test_diagonal_invertibility(self):
        rows, cols = 16, 16
        interleaved = diagonal_interleave(self.bits, rows=rows, cols=cols)
        self.assertFalse(np.array_equal(interleaved, self.bits))
        deinterleaved = diagonal_deinterleave(interleaved, rows=rows, cols=cols)
        np.testing.assert_array_equal(deinterleaved, self.bits)

    def test_pseudo_random_invertibility(self):
        seed = 9999
        interleaved = pseudo_random_interleave(self.bits, seed=seed)
        self.assertFalse(np.array_equal(interleaved, self.bits))
        deinterleaved = pseudo_random_deinterleave(interleaved, seed=seed)
        np.testing.assert_array_equal(deinterleaved, self.bits)

    def test_dispatcher_explicit_modes(self):
        for mode in ["block", "convolutional", "diagonal", "pseudo_random"]:
            out = deinterleave(self.bits, mode=mode)
            self.assertEqual(out["status"], "success")
            self.assertEqual(out["mode"], mode)
            self.assertEqual(len(out["output_bits"]), len(self.bits))

    def test_dispatcher_insufficient_data(self):
        short_bits = [1, 0, 1]
        out = deinterleave(short_bits, mode="block")
        self.assertEqual(out["status"], "insufficient_data")

    def test_dispatcher_unknown_mode_does_not_crash(self):
        out = deinterleave(self.bits, mode="unknown")
        self.assertIn(out["status"], {"success", "unknown"})
        self.assertEqual(len(out["output_bits"]), len(self.bits))


if __name__ == "__main__":
    unittest.main()
