"""
Integration tests for the complete SIGMA Recovery Orchestrator Pipeline.
"""

import os
import sys
import unittest
import numpy as np

src_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from sigma_recovery import orchestrate_signal_recovery
from models.signal_result import SignalResult
from export.json_export import export_to_json
from export.csv_export import export_to_csv
from export.report_export import generate_markdown_report


class TestPipeline(unittest.TestCase):

    def setUp(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.demo_iq = os.path.join(self.base_dir, "data", "iq", "demo_bpsk_100ksps_1msps.iq")
        self.synthetic_bpsk = os.path.join(self.base_dir, "data", "iq", "bpsk", "synthetic_bpsk_250ksps_1msps.iq")

    def test_complete_pipeline_on_demo_file(self):
        if not os.path.exists(self.demo_iq):
            self.skipTest(f"Demo file {self.demo_iq} not found")

        result = orchestrate_signal_recovery(
            input_path=self.demo_iq,
            user_sample_rate=1000000.0,
            user_center_freq=0.0
        )

        self.assertIsInstance(result, SignalResult)
        self.assertEqual(result.input_metadata.sample_rate, 1000000.0)
        self.assertEqual(result.recovery.demodulation_status, "LOCKED")
        self.assertGreater(len(result.recovery.bits), 0)
        self.assertIn(result.deinterleaving.status, ["SUCCESS", "UNKNOWN", "NOT DETECTED", "SKIPPED"])
        self.assertIn(result.fec.status, ["SUPPORTED", "NOT DETECTED", "UNKNOWN", "DECODING FAILED"])
        self.assertIsNotNone(result.correlation.status)

        # Test exports
        temp_json = os.path.join(self.base_dir, "scratch", "test_result.json")
        temp_csv = os.path.join(self.base_dir, "scratch", "test_result.csv")
        export_to_json(result, temp_json)
        export_to_csv(result, temp_csv)
        self.assertTrue(os.path.exists(temp_json))
        self.assertTrue(os.path.exists(temp_csv))

        report_md = generate_markdown_report(result)
        self.assertIn("SIGMA RF Intelligence Report", report_md)

    def test_gated_refusal_on_signal_without_clock(self):
        # signal.iq is synthetic noise with no recoverable clock
        signal_iq = os.path.join(self.base_dir, "data", "iq", "signal.iq")
        if not os.path.exists(signal_iq):
            self.skipTest("data/iq/signal.iq not found")

        result = orchestrate_signal_recovery(
            input_path=signal_iq,
            user_sample_rate=1000000.0
        )
        # Should decline demodulation rather than guess
        self.assertIn(result.recovery.demodulation_status, ["DECLINED", "NO CLOCK", "FAILED"])


if __name__ == "__main__":
    unittest.main()
