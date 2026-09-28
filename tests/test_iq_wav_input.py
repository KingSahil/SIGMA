"""
Unit tests for IQ and WAV File Ingestion and Format Conversions.
"""

import os
import sys
import unittest
import numpy as np

src_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from sigma_analyzer_core import SignalMetadata, load_and_convert_wav


class TestIQWAVInput(unittest.TestCase):

    def setUp(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.scratch_dir = os.path.join(self.base_dir, "scratch")
        os.makedirs(self.scratch_dir, exist_ok=True)

    def test_raw_iq_loading(self):
        # Create a small complex64 IQ file
        iq_file = os.path.join(self.scratch_dir, "test_input.iq")
        samples = (np.random.normal(size=1000) + 1j * np.random.normal(size=1000)).astype(np.complex64)
        samples.tofile(iq_file)

        meta = SignalMetadata(filepath=iq_file, samp_rate=1000000.0)
        self.assertTrue(meta.file_exists)
        self.assertEqual(meta.num_samples, 1000)
        self.assertEqual(meta.format_name, "Raw IQ Binary")

    def test_wav_conversion(self):
        import scipy.io.wavfile as wavfile
        wav_file = os.path.join(self.scratch_dir, "test_stereo.wav")
        fs = 48000
        # 16-bit stereo IQ
        i_data = np.int16(np.sin(2 * np.pi * 1000 * np.arange(4800) / fs) * 16000)
        q_data = np.int16(np.cos(2 * np.pi * 1000 * np.arange(4800) / fs) * 16000)
        stereo = np.column_stack([i_data, q_data])
        wavfile.write(wav_file, fs, stereo)

        out_iq, sr, num_smp, is_stereo = load_and_convert_wav(wav_file)
        self.assertTrue(os.path.exists(out_iq))
        self.assertEqual(sr, 48000)
        self.assertEqual(num_smp, 4800)
        self.assertTrue(is_stereo)


if __name__ == "__main__":
    unittest.main()
