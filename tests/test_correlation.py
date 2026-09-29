"""
Unit tests for Bitstream Correlation and Candidate Header/Payload Detection.
"""

import os
import sys
import unittest
import numpy as np

src_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from correlation.alignment import align_bitstreams
from correlation.header_detection import chance_threshold, detect_candidate_headers, KNOWN_SYNC_WORDS
from correlation.payload_detection import extract_candidate_payloads
from correlation.scoring import correlate_bitstreams


class TestCorrelation(unittest.TestCase):

    def setUp(self):
        self.rng = np.random.default_rng(404)
        self.payload = self.rng.integers(0, 2, 128, dtype=np.uint8)

    def test_bitstream_alignment(self):
        a = self.rng.integers(0, 2, 200, dtype=np.uint8)
        lag = 15
        # Delayed version
        b = np.concatenate([self.rng.integers(0, 2, lag, dtype=np.uint8), a[:180]])

        best_lag, is_inv, sim, sub_a, sub_b = align_bitstreams(a, b)
        self.assertEqual(best_lag, -lag)
        self.assertFalse(is_inv)
        self.assertGreaterEqual(sim, 0.95)

    def test_ccsds_header_detection(self):
        ccsds_sync = KNOWN_SYNC_WORDS["CCSDS 32-bit (0x1ACFFC1D)"]
        rx_stream = np.concatenate([
            self.rng.integers(0, 2, 20, dtype=np.uint8),
            ccsds_sync,
            self.payload,
            ccsds_sync,
            self.payload,
        ])

        headers = detect_candidate_headers(rx_stream)
        self.assertGreaterEqual(len(headers), 1)
        top = headers[0]
        self.assertIn("CCSDS", top["pattern_name"])
        self.assertEqual(top["first_offset"], 20)

    def test_short_pattern_can_decline_false_alarm_budget(self):
        self.assertEqual(chance_threshold(n_bits=10_000, pattern_len=7), -1)

    def test_candidate_payload_extraction(self):
        ccsds_sync = KNOWN_SYNC_WORDS["CCSDS 32-bit (0x1ACFFC1D)"]
        rx_stream = np.concatenate([ccsds_sync, self.payload])
        headers = detect_candidate_headers(rx_stream)
        payloads = extract_candidate_payloads(rx_stream, headers, default_payload_bits=len(self.payload))

        self.assertGreaterEqual(len(payloads), 1)
        extracted = np.asarray(payloads[0]["bits"], dtype=np.uint8)
        np.testing.assert_array_equal(extracted, self.payload)

    def test_correlate_bitstreams_full(self):
        out = correlate_bitstreams(self.payload)
        self.assertIn("status", out)
        self.assertIn("score", out)
        self.assertIn("candidate_headers", out)
        self.assertIn("candidate_payload_regions", out)


if __name__ == "__main__":
    unittest.main()
