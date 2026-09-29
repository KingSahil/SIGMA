"""
Unit tests for Forward Error Correction (Viterbi, Reed-Solomon, Concatenated, LDPC).
"""

import os
import sys
import unittest
import numpy as np

src_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from fec.convolutional import encode_convolutional, decode_viterbi
from fec.reed_solomon import encode_reed_solomon, decode_reed_solomon
from fec.concatenated import encode_concatenated, decode_concatenated
from fec.ldpc import encode_ldpc, decode_ldpc, check_syndrome, make_regular_ldpc_h
from fec.dispatcher import decode_fec


class TestFEC(unittest.TestCase):

    def setUp(self):
        self.rng = np.random.default_rng(303)
        self.info_bits = self.rng.integers(0, 2, 64, dtype=np.uint8)

    def test_viterbi_convolutional(self):
        coded = encode_convolutional(self.info_bits, K=3, polys=(0o7, 0o5))
        # Add 2 bit errors
        corrupted = coded.copy()
        corrupted[10] ^= 1
        corrupted[25] ^= 1

        decoded, res, errs = decode_viterbi(corrupted, K=3, polys=(0o7, 0o5))
        self.assertLessEqual(res, 0.05)
        # Should match original transmitted bits
        np.testing.assert_array_equal(decoded[:len(self.info_bits)], self.info_bits)

    def test_reed_solomon(self):
        coded_bits, coded_bytes = encode_reed_solomon(self.info_bits, n_sym=8)
        # Corrupt 2 bytes
        corrupted_bytes = bytearray(coded_bytes)
        corrupted_bytes[1] ^= 0xFF
        corrupted_bytes[3] ^= 0xAA

        decoded_bits, ok, errs, diag = decode_reed_solomon(corrupted_bytes, n_sym=8)
        self.assertTrue(ok)
        self.assertGreaterEqual(errs, 1)
        np.testing.assert_array_equal(decoded_bits[:len(self.info_bits)], self.info_bits)

    def test_concatenated(self):
        short_info = self.rng.integers(0, 2, 32, dtype=np.uint8)
        coded_bits, _ = encode_concatenated(short_info, rs_nsym=6, conv_k=3)
        # Decode clean
        dec_bits, ok, errs, diag = decode_concatenated(coded_bits, rs_nsym=6, conv_k=3)
        self.assertTrue(ok)
        np.testing.assert_array_equal(dec_bits[:len(short_info)], short_info)

    def test_ldpc(self):
        codeword, H = encode_ldpc(self.info_bits, n=64)
        # Check syndrome of clean codeword
        syn = check_syndrome(codeword, H)
        self.assertEqual(int(np.sum(syn)), 0)

        # Corrupt 1 bit
        corrupted = codeword.copy()
        corrupted[5] ^= 1
        self.assertGreater(int(np.sum(check_syndrome(corrupted, H))), 0)

        # Decode
        info_out, ok, errs, diag = decode_ldpc(corrupted, H=H, n=64)
        self.assertTrue(ok)
        np.testing.assert_array_equal(info_out, codeword[:len(info_out)])

    def test_dispatcher_not_detected_on_random_bits(self):
        rand_bits = self.rng.integers(0, 2, 100, dtype=np.uint8)
        out = decode_fec(rand_bits)
        self.assertEqual(out["status"], "NOT DETECTED")

    def test_dispatcher_supported_on_valid_conv(self):
        coded = encode_convolutional(self.info_bits, K=3, polys=(0o7, 0o5))
        out = decode_fec(coded, fec_type="convolutional")
        self.assertEqual(out["status"], "SUPPORTED")
        self.assertLessEqual(out["residual"], 0.05)


if __name__ == "__main__":
    unittest.main()
