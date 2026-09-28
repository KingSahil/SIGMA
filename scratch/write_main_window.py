# -*- coding: utf-8 -*-
"""
!!! SUPERSEDED -- DO NOT RE-RUN !!!

This script was a ONE-SHOT generator: running it overwrites
src/sigma_main_window.py wholesale, discarding every subsequent fix to that
file (the coding-layer card, the header line, the provenance label rename,
the demod gate, ...). The generated source is now maintained directly.
Kept only as a historical record of the first UI layout.
It still emits the OLD "Confidence: measured" label.
"""
code = '''"""
SIGMA - Signal Intelligence & Generalized Modulation Analyzer
Clean, Modern, Fully Responsive RF Intelligence Workstation
High-Contrast Pure White Typography & Verifiable NumPy DSP Metrics
"""

import os
import sys
from datetime import datetime
import numpy as np
import scipy.io.wavfile as wavfile
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt

try:
    import winsound
except ImportError:
    winsound = None

from sigma_theme import COLORS, MAIN_QSS, create_sigma_icon
from sigma_analyzer_core import SignalMetadata, load_and_convert_wav
from sigma_flowgraph import SigmaFlowgraph


def resolve_sample_path(filepath=None):
    """Resolves an IQ or WAV sample file path, checking standard data locations."""
    if filepath and os.path.exists(filepath):
        return os.path.abspath(filepath)

    candidates = []
    if filepath:
        candidates.append(filepath)

    candidates.extend([
        "data/iq/signal.iq",
        "data/signal.iq",
        "signal.iq",
        os.path.join(os.path.dirname(__file__), "..", "data", "iq", "signal.iq"),
        os.path.join(os.path.dirname(__file__), "..", "data", "signal.iq"),
        os.path.join(os.path.dirname(__file__), "..", "signal.iq"),
    ])
    for c in candidates:
        if os.path.exists(c):
            return os.path.abspath(c)
    return filepath if filepath else "signal.iq"


class AudioManager:
    """Handles audio playback of WAV recordings and IQ signal audio previews."""

    def __init__(self):
        self.is_playing = False
        self.current_audio_file = None

    def play(self, filepath, samp_rate=1000000):
        self.stop()
        if not filepath or not os.path.exists(filepath):
            return False
        if winsound is None:
            return False

        if filepath.lower().endswith(".wav"):
            target_wav = self._prepare_wav_for_playback(filepath)
        else:
            target_wav = self._convert_iq_to_audio_wav(filepath, samp_rate)

        if target_wav and os.path.exists(target_wav):
            self.current_audio_file = target_wav
            self.is_playing = True
            flags = winsound.SND_ASYNC | winsound.SND_FILENAME | winsound.SND_LOOP
            winsound.PlaySound(target_wav, flags)
            return True
        return False

    def stop(self):
        if self.is_playing:
            if winsound is not None:
                winsound.PlaySound(None, winsound.SND_PURGE)
            self.is_playing = False

    def _prepare_wav_for_playback(self, wav_path):
        """Ensures WAV file is in standard 16-bit PCM for audio playback."""
        try:
            sr, data = wavfile.read(wav_path)
            if data.dtype == np.int16 and data.ndim == 1:
                return wav_path

            if np.issubdtype(data.dtype, np.floating):
                audio = np.clip(data, -1.0, 1.0)
                audio_int16 = (audio * 32767).astype(np.int16)
            else:
                audio_int16 = data.astype(np.int16)

            out_wav = os.path.splitext(wav_path)[0] + "_playback.wav"
            wavfile.write(out_wav, sr, audio_int16)
            return out_wav
        except Exception as e:
            print(f"[SIGMA Audio] Prepare WAV error: {e}")
            return wav_path

    def _convert_iq_to_audio_wav(self, iq_path, samp_rate):
        """Demodulates raw IQ samples into audible audio via FM discriminator + BFO."""
        try:
            samples = np.fromfile(iq_path, dtype=np.complex64, count=1000000)
            if len(samples) == 0:
                return None

            raw_dur = len(samples) / float(samp_rate) if samp_rate > 0 else 0.05
            if raw_dur < 3.0:
                repeats = int(np.ceil(3.0 / max(raw_dur, 0.001)))
                repeats = min(repeats, 80)
                samples = np.tile(samples, repeats)

            audio_rate = 44100
            decim = max(1, int(samp_rate / audio_rate))
            if decim > 1 and len(samples) >= decim:
                trim_len = (len(samples) // decim) * decim
                sub_samples = samples[:trim_len].reshape(-1, decim).mean(axis=1)
            else:
                sub_samples = samples[::decim]
            actual_fs = samp_rate / decim

            if len(sub_samples) > 1:
                fm_demod = np.angle(sub_samples[1:] * np.conj(sub_samples[:-1]))
                fm_demod = np.append(fm_demod, fm_demod[-1])
                fm_std = np.std(fm_demod)
            else:
                fm_demod = np.zeros(len(sub_samples))
                fm_std = 0.0

            t = np.arange(len(sub_samples)) / float(actual_fs)
            bfo = np.exp(1j * 2 * np.pi * 1200.0 * t)
            heterodyne = np.real(sub_samples * bfo)

            env = np.abs(sub_samples)
            env_ac = env - np.mean(env)

            if fm_std > 0.15:
                audio = (fm_demod - np.mean(fm_demod)) * 0.75 + heterodyne * 0.25
            elif np.std(env_ac) > 0.12:
                audio = env_ac * 0.75 + heterodyne * 0.25
            else:
                audio = heterodyne

            audio = audio - np.mean(audio)
            peak = np.max(np.abs(audio))
            if peak > 1e-6:
                audio = (audio / peak) * 0.88

            if int(actual_fs) != audio_rate and len(audio) > 1:
                target_len = int(len(audio) * (audio_rate / float(actual_fs)))
                audio_44k = np.interp(
                    np.linspace(0, len(audio), target_len, endpoint=False),
                    np.arange(len(audio)),
                    audio
                )
            else:
                audio_44k = audio

            out_wav = os.path.splitext(iq_path)[0] + "_audible.wav"
            audio_int16 = (np.clip(audio_44k, -1.0, 1.0) * 32767).astype(np.int16)
            wavfile.write(out_wav, audio_rate, audio_int16)
            return out_wav
        except Exception as e:
            print(f"[SIGMA Audio] IQ Audio error: {e}")
            return None


class SettingsDialog(QtWidgets.QDialog):
    """Clean settings dialog for RF configuration."""

    def __init__(self, parent=None, samp_rate=1000000, center_freq=0.0):
        super().__init__(parent)
        self.setWindowTitle("SIGMA — Settings")
        self.setMinimumWidth(380)
        self.setStyleSheet(MAIN_QSS)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QtWidgets.QLabel("RF HARDWARE & DSP SETTINGS")
        title.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 800; letter-spacing: 1.2px;")
        layout.addWidget(title)

        form = QtWidgets.QFormLayout()
        form.setSpacing(14)

        self.rate_spin = QtWidgets.QDoubleSpinBox()
        self.rate_spin.setRange(1e3, 100e6)
        self.rate_spin.setValue(samp_rate)
        self.rate_spin.setSingleStep(100e3)
        self.rate_spin.setSuffix(" S/s")
        form.addRow("Sample Rate:", self.rate_spin)

        self.freq_spin = QtWidgets.QDoubleSpinBox()
        self.freq_spin.setRange(-10e9, 10e9)
        self.freq_spin.setValue(center_freq)
        self.freq_spin.setSingleStep(10e3)
        self.freq_spin.setSuffix(" Hz")
        form.addRow("Center Frequency:", self.freq_spin)

        layout.addLayout(form)

        btn_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def get_values(self):
        return self.rate_spin.value(), self.freq_spin.value()


class SigmaMainWindow(QtWidgets.QMainWindow):
    """
    Main desktop workstation for SIGMA.
    Engineered with high-contrast pure white typography, responsive layouts,
    QScrollArea protection for small screens, and verifiable DSP calculations.
    """

    def __init__(self, initial_file="signal.iq"):
        super().__init__()
        self.setWindowTitle("SIGMA — Signal Intelligence & Generalized Modulation Analyzer")
        self.setWindowIcon(create_sigma_icon())
        self.resize(1280, 840)
        self.setMinimumSize(780, 520)

        # Global High-Contrast Dark Palette
        pal = QtGui.QPalette()
        pal.setColor(QtGui.QPalette.Window, QtGui.QColor("#0b0f17"))
        pal.setColor(QtGui.QPalette.WindowText, QtGui.QColor("#ffffff"))
        pal.setColor(QtGui.QPalette.Base, QtGui.QColor("#131822"))
        pal.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor("#1a2230"))
        pal.setColor(QtGui.QPalette.Text, QtGui.QColor("#ffffff"))
        pal.setColor(QtGui.QPalette.Button, QtGui.QColor("#1a2230"))
        pal.setColor(QtGui.QPalette.ButtonText, QtGui.QColor("#ffffff"))
        pal.setColor(QtGui.QPalette.BrightText, QtGui.QColor("#38bdf8"))
        pal.setColor(QtGui.QPalette.Highlight, QtGui.QColor("#38bdf8"))
        pal.setColor(QtGui.QPalette.HighlightedText, QtGui.QColor("#000000"))
        self.setPalette(pal)
        app = QtWidgets.QApplication.instance()
        if app:
            app.setPalette(pal)

        # Application state
        self.original_file = resolve_sample_path(initial_file)
        self.current_file = self.original_file
        self.samp_rate = 1000000
        self.center_freq = 0.0
        self.is_running = True
        self.is_looping = True

        # Audio Manager
        self.audio_manager = AudioManager()

        # Flowgraph & Analysis
        self.flowgraph = SigmaFlowgraph(
            filepath=self.current_file,
            samp_rate=self.samp_rate,
            center_freq=self.center_freq,
            repeat=self.is_looping
        )
        self.metadata = SignalMetadata(
            filepath=self.current_file,
            samp_rate=self.samp_rate,
            center_freq=self.center_freq
        )

        # Apply Stylesheet
        self.setStyleSheet(MAIN_QSS)

        # Build UI
        self._init_ui()
        self._update_all_displays()

        # Start Flowgraph
        self.flowgraph.start()
        self.flowgraph.flowgraph_started.set()

    # =========================================================================
    # Main UI Construction
    # =========================================================================
    def _init_ui(self):
        # QScrollArea prevents graph squishing on small displays
        scroll = QtWidgets.QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setCentralWidget(scroll)

        central = QtWidgets.QWidget()
        central.setObjectName("CentralWidget")
        central.setMinimumWidth(740)
        scroll.setWidget(central)

        main_layout = QtWidgets.QVBoxLayout(central)
        main_layout.setContentsMargins(18, 14, 18, 14)
        main_layout.setSpacing(12)

        # 1. Header Bar
        main_layout.addWidget(self._build_header())

        # 2. Section 1: Input Signal Card
        main_layout.addWidget(self._build_input_section())

        # 3. Section 2: Visualizations with View Switcher
        main_layout.addWidget(self._build_visualizations_section(), 1)

        # 4. Section 3: Results (Signal Analysis & Modulation)
        main_layout.addWidget(self._build_results_section())

        # 5. Bottom: Clean Processing Flow
        main_layout.addWidget(self._build_processing_flow())

    # =========================================================================
    # 1. Header Section
    # =========================================================================
    def _build_header(self):
        header = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 4)
        layout.setSpacing(12)

        brand_box = QtWidgets.QVBoxLayout()
        brand_box.setSpacing(2)

        title = QtWidgets.QLabel("SIGMA")
        title.setStyleSheet("color: #ffffff; font-size: 22px; font-weight: 900; letter-spacing: 1.5px;")
        title.setMinimumWidth(0)
        brand_box.addWidget(title)

        subtitle = QtWidgets.QLabel("Signal Intelligence & Generalized Modulation Analyzer")
        subtitle.setStyleSheet("color: #cbd5e1; font-size: 12px; font-weight: 500;")
        subtitle.setMinimumWidth(0)
        brand_box.addWidget(subtitle)

        layout.addLayout(brand_box)
        layout.addStretch(1)

        # Right: Settings Button
        self.btn_settings = QtWidgets.QPushButton("⚙ Settings")
        self.btn_settings.setStyleSheet("color: #ffffff; background-color: #1a2230; border: 1px solid #3b4d66; border-radius: 7px; padding: 6px 14px; font-weight: 700;")
        self.btn_settings.setMinimumWidth(0)
        self.btn_settings.clicked.connect(self._open_settings)
        layout.addWidget(self.btn_settings)

        return header

    # =========================================================================
    # 2. Section 1: Responsive Input Signal Bar
    # =========================================================================
    def _build_input_section(self):
        card = QtWidgets.QFrame()
        card.setProperty("class", "SigmaBigCard")
        card.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(14, 8, 14, 8)
        card_layout.setSpacing(6)

        # Top row: Filename, tag, action buttons
        top_row = QtWidgets.QHBoxLayout()
        top_row.setSpacing(10)

        tag = QtWidgets.QLabel("INPUT SIGNAL")
        tag.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 800; letter-spacing: 1.2px;")
        tag.setMinimumWidth(0)
        top_row.addWidget(tag)

        self.lbl_filename = QtWidgets.QLabel(os.path.basename(self.current_file) if self.current_file else "signal.iq")
        self.lbl_filename.setStyleSheet("color: #ffffff; font-size: 15px; font-weight: 800; font-family: 'Consolas', monospace;")
        self.lbl_filename.setMinimumWidth(0)
        top_row.addWidget(self.lbl_filename)

        top_row.addStretch(1)

        self.btn_load_signal = QtWidgets.QPushButton("📂 Load Signal File")
        self.btn_load_signal.setStyleSheet("background-color: #38bdf8; color: #0b1017; border: none; border-radius: 7px; padding: 6px 16px; font-weight: 800;")
        self.btn_load_signal.setMinimumWidth(0)
        self.btn_load_signal.clicked.connect(self._load_signal_file)
        top_row.addWidget(self.btn_load_signal)

        self.btn_load_iq = self.btn_load_signal
        self.btn_load_wav = self.btn_load_signal

        self.btn_play_audio = QtWidgets.QPushButton("🔊 Play Audio")
        self.btn_play_audio.setStyleSheet("background-color: rgba(244, 63, 94, 0.15); color: #f43f5e; border: 1px solid rgba(244, 63, 94, 0.5); border-radius: 7px; padding: 6px 16px; font-weight: 700;")
        self.btn_play_audio.setMinimumWidth(0)
        self.btn_play_audio.clicked.connect(self._toggle_audio_playback)
        top_row.addWidget(self.btn_play_audio)

        card_layout.addLayout(top_row)

        # Bottom row: Signal metadata badges
        badge_row = QtWidgets.QHBoxLayout()
        badge_row.setSpacing(8)

        badge_qss = "background-color: #1a2230; color: #cbd5e1; border: 1px solid #243042; border-radius: 6px; padding: 4px 8px; font-size: 11px; font-weight: 600;"

        self.badge_format = QtWidgets.QLabel("Format: Complex Float32")
        self.badge_format.setStyleSheet(badge_qss)
        self.badge_format.setMinimumWidth(0)
        badge_row.addWidget(self.badge_format)

        self.badge_samples = QtWidgets.QLabel("Samples: 50,000")
        self.badge_samples.setStyleSheet(badge_qss)
        self.badge_samples.setMinimumWidth(0)
        badge_row.addWidget(self.badge_samples)

        self.badge_rate = QtWidgets.QLabel("Rate: 1.00 MS/s")
        self.badge_rate.setStyleSheet(badge_qss)
        self.badge_rate.setMinimumWidth(0)
        badge_row.addWidget(self.badge_rate)

        self.badge_duration = QtWidgets.QLabel("Duration: 50.00 ms (400.0 KB)")
        self.badge_duration.setStyleSheet(badge_qss)
        self.badge_duration.setMinimumWidth(0)
        badge_row.addWidget(self.badge_duration)

        badge_row.addStretch(1)
        card_layout.addLayout(badge_row)

        return card

    # =========================================================================
    # 3. Section 2: Visualizations with View Switcher (2x2 Grid or Solo Views)
    # =========================================================================
    def _build_visualizations_section(self):
        container_widget = QtWidgets.QWidget()
        container = QtWidgets.QVBoxLayout(container_widget)
        container.setContentsMargins(0, 0, 0, 0)
        container.setSpacing(6)

        # Toolbar: Title + View Mode Buttons
        tb = QtWidgets.QHBoxLayout()
        tb.setContentsMargins(2, 0, 2, 0)
        tb.setSpacing(8)

        v_title = QtWidgets.QLabel("SIGNAL VISUALIZATIONS")
        v_title.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 800; letter-spacing: 1.2px;")
        v_title.setMinimumWidth(0)
        tb.addWidget(v_title)

        tb.addStretch(1)

        # View Mode Toggle Buttons
        self.btn_views = {}
        view_modes = [
            ("quad", "⊞ 2x2 Grid"),
            ("time", "⏱ Time"),
            ("freq", "📊 Spectrum"),
            ("waterfall", "🌊 Waterfall"),
            ("const", "✦ Constellation"),
        ]
        for key, text in view_modes:
            b = QtWidgets.QPushButton(text)
            b.setMinimumWidth(0)
            b.clicked.connect(lambda _, k=key: self._set_view_mode(k))
            tb.addWidget(b)
            self.btn_views[key] = b

        self._refresh_view_toggle_styles("quad")
        container.addLayout(tb)

        # Splitter hosting 2 rows of cards
        self.viz_splitter = QtWidgets.QSplitter(Qt.Vertical)
        self.viz_splitter.setChildrenCollapsible(False)
        self.viz_splitter.setHandleWidth(8)
        self.viz_splitter.setMinimumHeight(380)

        # Row 1: Time Domain & Frequency Spectrum
        self.w_upper_row = QtWidgets.QWidget()
        self.w_upper_row.setMinimumHeight(185)
        self.w_upper_row.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        lay_upper = QtWidgets.QHBoxLayout(self.w_upper_row)
        lay_upper.setContentsMargins(0, 0, 0, 0)
        lay_upper.setSpacing(8)

        # Card 1: Time Domain
        self.card_time = QtWidgets.QFrame()
        self.card_time.setProperty("class", "SigmaBigCard")
        self.card_time.setMinimumSize(280, 180)
        self.card_time.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        lay_time = QtWidgets.QVBoxLayout(self.card_time)
        lay_time.setContentsMargins(10, 6, 10, 6)
        lay_time.setSpacing(4)

        h_time = QtWidgets.QHBoxLayout()
        t_time = QtWidgets.QLabel("TIME DOMAIN")
        t_time.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 800; letter-spacing: 1.2px;")
        t_time.setMinimumWidth(0)
        h_time.addWidget(t_time)

        self.hud_time = QtWidgets.QLabel("📍 Hover/Drag to Inspect")
        self.hud_time.setStyleSheet("background-color: #0b0f17; border: 1px solid #243042; border-radius: 6px; color: #38bdf8; font-family: 'Consolas', monospace; font-size: 11px; font-weight: 700; padding: 2px 8px;")
        self.hud_time.setMinimumWidth(0)
        h_time.addWidget(self.hud_time)

        h_time.addStretch(1)
        leg_time = QtWidgets.QLabel("● I (cyan)   ● Q (magenta)")
        leg_time.setStyleSheet("color: #cbd5e1; font-size: 11px; font-weight: 700;")
        leg_time.setMinimumWidth(0)
        h_time.addWidget(leg_time)
        lay_time.addLayout(h_time)
        lay_time.addWidget(self.flowgraph.time_sink_widget, 1)
        lay_upper.addWidget(self.card_time, 1)
        self._attach_hud_overlay(self.flowgraph.time_sink_widget, self.hud_time, "time")

        # Card 2: Frequency Spectrum
        self.card_freq = QtWidgets.QFrame()
        self.card_freq.setProperty("class", "SigmaBigCard")
        self.card_freq.setMinimumSize(280, 180)
        self.card_freq.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        lay_freq = QtWidgets.QVBoxLayout(self.card_freq)
        lay_freq.setContentsMargins(10, 6, 10, 6)
        lay_freq.setSpacing(4)

        h_freq = QtWidgets.QHBoxLayout()
        t_freq = QtWidgets.QLabel("FREQUENCY SPECTRUM")
        t_freq.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 800; letter-spacing: 1.2px;")
        t_freq.setMinimumWidth(0)
        h_freq.addWidget(t_freq)

        self.hud_freq = QtWidgets.QLabel("📍 Hover/Drag to Inspect")
        self.hud_freq.setStyleSheet("background-color: #0b0f17; border: 1px solid #243042; border-radius: 6px; color: #38bdf8; font-family: 'Consolas', monospace; font-size: 11px; font-weight: 700; padding: 2px 8px;")
        self.hud_freq.setMinimumWidth(0)
        h_freq.addWidget(self.hud_freq)

        h_freq.addStretch(1)
        leg_freq = QtWidgets.QLabel("1024-pt FFT • dBFS")
        leg_freq.setStyleSheet("color: #cbd5e1; font-size: 11px; font-weight: 600;")
        leg_freq.setMinimumWidth(0)
        h_freq.addWidget(leg_freq)
        lay_freq.addLayout(h_freq)
        lay_freq.addWidget(self.flowgraph.freq_sink_widget, 1)
        lay_upper.addWidget(self.card_freq, 1)
        self._attach_hud_overlay(self.flowgraph.freq_sink_widget, self.hud_freq, "freq")

        self.viz_splitter.addWidget(self.w_upper_row)

        # Row 2: Waterfall & Constellation
        self.w_lower_row = QtWidgets.QWidget()
        self.w_lower_row.setMinimumHeight(185)
        self.w_lower_row.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        lay_lower = QtWidgets.QHBoxLayout(self.w_lower_row)
        lay_lower.setContentsMargins(0, 0, 0, 0)
        lay_lower.setSpacing(8)

        # Card 3: Waterfall (Spectrogram)
        self.card_waterfall = QtWidgets.QFrame()
        self.card_waterfall.setProperty("class", "SigmaBigCard")
        self.card_waterfall.setMinimumSize(280, 180)
        self.card_waterfall.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        lay_wf = QtWidgets.QVBoxLayout(self.card_waterfall)
        lay_wf.setContentsMargins(10, 6, 10, 6)
        lay_wf.setSpacing(4)

        h_wf = QtWidgets.QHBoxLayout()
        t_wf = QtWidgets.QLabel("WATERFALL (SPECTROGRAM)")
        t_wf.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 800; letter-spacing: 1.2px;")
        t_wf.setMinimumWidth(0)
        h_wf.addWidget(t_wf)

        self.hud_wf = QtWidgets.QLabel("📍 Hover/Drag to Inspect")
        self.hud_wf.setStyleSheet("background-color: #0b0f17; border: 1px solid #243042; border-radius: 6px; color: #38bdf8; font-family: 'Consolas', monospace; font-size: 11px; font-weight: 700; padding: 2px 8px;")
        self.hud_wf.setMinimumWidth(0)
        h_wf.addWidget(self.hud_wf)

        h_wf.addStretch(1)
        leg_wf = QtWidgets.QLabel("Intensity over Time")
        leg_wf.setStyleSheet("color: #cbd5e1; font-size: 11px; font-weight: 600;")
        leg_wf.setMinimumWidth(0)
        h_wf.addWidget(leg_wf)
        lay_wf.addLayout(h_wf)
        lay_wf.addWidget(self.flowgraph.waterfall_sink_widget, 1)
        lay_lower.addWidget(self.card_waterfall, 1)
        self._attach_hud_overlay(self.flowgraph.waterfall_sink_widget, self.hud_wf, "waterfall")

        # Card 4: Constellation
        self.card_const = QtWidgets.QFrame()
        self.card_const.setProperty("class", "SigmaBigCard")
        self.card_const.setMinimumSize(280, 180)
        self.card_const.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        lay_const = QtWidgets.QVBoxLayout(self.card_const)
        lay_const.setContentsMargins(10, 6, 10, 6)
        lay_const.setSpacing(4)

        h_const = QtWidgets.QHBoxLayout()
        t_const = QtWidgets.QLabel("CONSTELLATION DIAGRAM")
        t_const.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 800; letter-spacing: 1.2px;")
        t_const.setMinimumWidth(0)
        h_const.addWidget(t_const)

        self.hud_const = QtWidgets.QLabel("📍 Hover/Drag to Inspect")
        self.hud_const.setStyleSheet("background-color: #0b0f17; border: 1px solid #243042; border-radius: 6px; color: #38bdf8; font-family: 'Consolas', monospace; font-size: 11px; font-weight: 700; padding: 2px 8px;")
        self.hud_const.setMinimumWidth(0)
        h_const.addWidget(self.hud_const)

        h_const.addStretch(1)
        leg_const = QtWidgets.QLabel("In-Phase (I) vs Quadrature (Q)")
        leg_const.setStyleSheet("color: #cbd5e1; font-size: 11px; font-weight: 600;")
        leg_const.setMinimumWidth(0)
        h_const.addWidget(leg_const)
        lay_const.addLayout(h_const)
        lay_const.addWidget(self.flowgraph.const_sink_widget, 1)
        lay_lower.addWidget(self.card_const, 1)
        self._attach_hud_overlay(self.flowgraph.const_sink_widget, self.hud_const, "const")

        self.viz_splitter.addWidget(self.w_lower_row)

        self.viz_splitter.setSizes([220, 220])
        container.addWidget(self.viz_splitter, 1)

        return container_widget

    def _refresh_view_toggle_styles(self, active_key):
        for k, b in self.btn_views.items():
            if k == active_key:
                b.setStyleSheet("background-color: rgba(56, 189, 248, 0.22); color: #38bdf8; border: 1.5px solid #38bdf8; border-radius: 6px; padding: 5px 11px; font-weight: 800; font-size: 11px;")
            else:
                b.setStyleSheet("background-color: #1a2230; color: #cbd5e1; border: 1px solid #243042; border-radius: 6px; padding: 5px 11px; font-weight: 600; font-size: 11px;")

    def _set_view_mode(self, mode):
        """Switches between 2x2 Grid and solo full views."""
        self._refresh_view_toggle_styles(mode)

        if mode == "quad":
            self.w_upper_row.show()
            self.card_time.show()
            self.card_freq.show()
            self.w_lower_row.show()
            self.card_waterfall.show()
            self.card_const.show()
            self.card_time.setMinimumHeight(180)
            self.card_freq.setMinimumHeight(180)
            self.card_waterfall.setMinimumHeight(180)
            self.card_const.setMinimumHeight(180)
            self.viz_splitter.setSizes([220, 220])
        elif mode == "time":
            self.w_upper_row.show()
            self.card_time.show()
            self.card_time.setMinimumHeight(320)
            self.card_freq.hide()
            self.w_lower_row.hide()
        elif mode == "freq":
            self.w_upper_row.show()
            self.card_freq.show()
            self.card_freq.setMinimumHeight(320)
            self.card_time.hide()
            self.w_lower_row.hide()
        elif mode == "waterfall":
            self.w_upper_row.hide()
            self.w_lower_row.show()
            self.card_waterfall.show()
            self.card_waterfall.setMinimumHeight(320)
            self.card_const.hide()
        elif mode == "const":
            self.w_upper_row.hide()
            self.w_lower_row.show()
            self.card_const.show()
            self.card_const.setMinimumHeight(320)
            self.card_waterfall.hide()

    def _attach_hud_overlay(self, widget, label, kind="time"):
        """Connects plot zoomer to inspect HUD badge."""
        default_hint = "📍 Hover/Drag to Inspect"

        for obj in widget.findChildren(QtCore.QObject):
            cname = obj.metaObject().className()
            if "Zoomer" in cname:
                def make_point_handler(lbl, k):
                    def on_point(pt):
                        x, y = pt.x(), pt.y()
                        if k == "time":
                            if abs(x) >= 1000:
                                x_str = f"{x/1000.0:.3f} ms"
                            else:
                                x_str = f"{x:.2f} µs"
                            lbl.setText(f"📍 {x_str} | {y:+.4f} V")
                        elif k == "freq":
                            if abs(x) >= 1000:
                                x_str = f"{x/1000.0:.3f} MHz"
                            else:
                                x_str = f"{x:.2f} kHz"
                            lbl.setText(f"📍 {x_str} | {y:+.1f} dB")
                        elif k == "waterfall":
                            lbl.setText(f"📍 {x:.2f} kHz | {y:.2f} s")
                        elif k == "const":
                            lbl.setText(f"📍 I: {x:+.3f} | Q: {y:+.3f}")
                        else:
                            lbl.setText(f"📍 {x:.3f}, {y:.3f}")
                    return on_point

                def make_rect_handler(lbl, k):
                    def on_zoomed(rect):
                        lbl.setText(f"🔍 Zoomed [{rect.left():.1f} → {rect.right():.1f}]")
                    return on_zoomed

                try:
                    obj.moved['QPointF'].connect(make_point_handler(label, kind))
                    obj.appended['QPointF'].connect(make_point_handler(label, kind))
                    obj.zoomed['QRectF'].connect(make_rect_handler(label, kind))
                except Exception:
                    pass

        for w in widget.findChildren(QtWidgets.QWidget):
            cname = w.metaObject().className()
            if "PlotCanvas" in cname or "Canvas" in cname:
                class UnzoomFilter(QtCore.QObject):
                    def __init__(self, lbl, hint):
                        super().__init__()
                        self.lbl = lbl
                        self.hint = hint
                    def eventFilter(self, obj, ev):
                        if ev.type() == QtCore.QEvent.MouseButtonPress and ev.button() == QtCore.Qt.RightButton:
                            QtCore.QTimer.singleShot(120, lambda: self.lbl.setText(self.hint))
                        return False

                filt = UnzoomFilter(label, default_hint)
                w.installEventFilter(filt)
                if not hasattr(self, "_canvas_filters"):
                    self._canvas_filters = []
                self._canvas_filters.append(filt)

    # =========================================================================
    # 4. Section 3: Results (Signal Analysis & Modulation)
    # =========================================================================
    def _build_results_section(self):
        container = QtWidgets.QHBoxLayout()
        container.setContentsMargins(0, 0, 0, 0)
        container.setSpacing(10)

        # 1. Signal Analysis Card
        card_analysis = QtWidgets.QFrame()
        card_analysis.setProperty("class", "SigmaBigCard")
        card_analysis.setMinimumWidth(0)
        lay_an = QtWidgets.QVBoxLayout(card_analysis)
        lay_an.setContentsMargins(12, 8, 12, 8)
        lay_an.setSpacing(6)

        t_analysis = QtWidgets.QLabel("SIGNAL ANALYSIS & DSP METRICS")
        t_analysis.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 800; letter-spacing: 1.2px;")
        t_analysis.setMinimumWidth(0)
        lay_an.addWidget(t_analysis)

        # Metrics Grid (2 rows x 4 cols, fully responsive)
        grid = QtWidgets.QGridLayout()
        grid.setSpacing(6)
        grid.setContentsMargins(0, 0, 0, 0)

        self.m_peak_freq = self._create_big_metric_cell("Peak Frequency", "--", is_highlight=True)
        self.m_center_freq = self._create_big_metric_cell("Center Frequency", "--")
        self.m_bandwidth = self._create_big_metric_cell("Bandwidth", "--")
        self.m_signal_power = self._create_big_metric_cell("Signal Power", "--")

        self.m_noise_floor = self._create_big_metric_cell("Noise Floor", "--")
        self.m_snr = self._create_big_metric_cell("Signal SNR", "--")
        self.m_rms = self._create_big_metric_cell("RMS Amplitude", "--")
        self.m_peak_amp = self._create_big_metric_cell("Peak Amplitude", "--")

        grid.addWidget(self.m_peak_freq[0], 0, 0)
        grid.addWidget(self.m_center_freq[0], 0, 1)
        grid.addWidget(self.m_bandwidth[0], 0, 2)
        grid.addWidget(self.m_signal_power[0], 0, 3)

        grid.addWidget(self.m_noise_floor[0], 1, 0)
        grid.addWidget(self.m_snr[0], 1, 1)
        grid.addWidget(self.m_rms[0], 1, 2)
        grid.addWidget(self.m_peak_amp[0], 1, 3)

        lay_an.addLayout(grid)
        container.addWidget(card_analysis, 7)

        # 2. Modulation Card
        card_mod = QtWidgets.QFrame()
        card_mod.setProperty("class", "SigmaBigCard")
        card_mod.setMinimumWidth(0)
        lay_mod = QtWidgets.QVBoxLayout(card_mod)
        lay_mod.setContentsMargins(12, 8, 12, 8)
        lay_mod.setSpacing(4)

        t_mod = QtWidgets.QLabel("MODULATION")
        t_mod.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 800; letter-spacing: 1.2px;")
        t_mod.setMinimumWidth(0)
        lay_mod.addWidget(t_mod)

        mod_box = QtWidgets.QFrame()
        mod_box.setStyleSheet("background-color: #1a2230; border: 1px solid #243042; border-radius: 8px;")
        mod_box.setMinimumWidth(0)
        box_lay = QtWidgets.QVBoxLayout(mod_box)
        box_lay.setContentsMargins(10, 6, 10, 6)
        box_lay.setSpacing(2)

        self.lbl_mod_class = QtWidgets.QLabel("Not analyzed")
        self.lbl_mod_class.setStyleSheet("color: #fbbf24; font-size: 17px; font-weight: 900;")
        self.lbl_mod_class.setWordWrap(True)
        self.lbl_mod_class.setMinimumWidth(0)
        box_lay.addWidget(self.lbl_mod_class)

        self.lbl_mod_conf = QtWidgets.QLabel("Confidence: --")
        self.lbl_mod_conf.setStyleSheet("color: #34d399; font-size: 12px; font-weight: 700;")
        self.lbl_mod_conf.setMinimumWidth(0)
        box_lay.addWidget(self.lbl_mod_conf)

        lay_mod.addWidget(mod_box, 1)
        container.addWidget(card_mod, 3)

        res_widget = QtWidgets.QWidget()
        res_widget.setMinimumWidth(0)
        res_widget.setLayout(container)
        return res_widget

    def _create_big_metric_cell(self, label, default_val="--", is_highlight=False):
        cell = QtWidgets.QFrame()
        cell.setStyleSheet("background-color: #1a2230; border: 1px solid #243042; border-radius: 8px;")
        cell.setMinimumWidth(0)
        lay = QtWidgets.QVBoxLayout(cell)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(2)

        lbl = QtWidgets.QLabel(label)
        lbl.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: 700; letter-spacing: 0.8px; text-transform: uppercase;")
        lbl.setMinimumWidth(0)
        lay.addWidget(lbl)

        val = QtWidgets.QLabel(default_val)
        val_color = "#38bdf8" if is_highlight else "#ffffff"
        val.setStyleSheet(f"color: {val_color}; font-size: 16px; font-weight: 800; font-family: 'Consolas', monospace;")
        val.setMinimumWidth(0)
        lay.addWidget(val)

        return cell, val

    # =========================================================================
    # 5. Bottom: Clean Processing Flow
    # =========================================================================
    def _build_processing_flow(self):
        bar = QtWidgets.QFrame()
        bar.setStyleSheet("background-color: #131822; border: 1px solid #243042; border-radius: 8px;")
        bar.setMinimumWidth(0)
        layout = QtWidgets.QHBoxLayout(bar)
        layout.setContentsMargins(14, 4, 14, 4)
        layout.setSpacing(10)

        lbl_input = QtWidgets.QLabel("1. INPUT ✓")
        lbl_input.setStyleSheet("color: #34d399; font-size: 12px; font-weight: 800;")
        lbl_input.setMinimumWidth(0)
        layout.addWidget(lbl_input)

        arr1 = QtWidgets.QLabel("→")
        arr1.setStyleSheet("color: #64748b; font-size: 12px; font-weight: 800;")
        arr1.setMinimumWidth(0)
        layout.addWidget(arr1)

        lbl_analysis = QtWidgets.QLabel("2. ANALYSIS ✓")
        lbl_analysis.setStyleSheet("color: #34d399; font-size: 12px; font-weight: 800;")
        lbl_analysis.setMinimumWidth(0)
        layout.addWidget(lbl_analysis)

        arr2 = QtWidgets.QLabel("→")
        arr2.setStyleSheet("color: #64748b; font-size: 12px; font-weight: 800;")
        arr2.setMinimumWidth(0)
        layout.addWidget(arr2)

        lbl_mod = QtWidgets.QLabel("3. MODULATION ✓")
        lbl_mod.setStyleSheet("color: #34d399; font-size: 12px; font-weight: 800;")
        lbl_mod.setMinimumWidth(0)
        layout.addWidget(lbl_mod)

        arr3 = QtWidgets.QLabel("→")
        arr3.setStyleSheet("color: #64748b; font-size: 12px; font-weight: 800;")
        arr3.setMinimumWidth(0)
        layout.addWidget(arr3)

        lbl_demod = QtWidgets.QLabel("4. DEMOD ○")
        lbl_demod.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: 600;")
        lbl_demod.setMinimumWidth(0)
        layout.addWidget(lbl_demod)

        arr4 = QtWidgets.QLabel("→")
        arr4.setStyleSheet("color: #64748b; font-size: 12px; font-weight: 800;")
        arr4.setMinimumWidth(0)
        layout.addWidget(arr4)

        lbl_bits = QtWidgets.QLabel("5. BITS ○")
        lbl_bits.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: 600;")
        lbl_bits.setMinimumWidth(0)
        layout.addWidget(lbl_bits)

        layout.addStretch(1)

        legend = QtWidgets.QLabel("✓ completed   ● processing   ○ not available")
        legend.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 600;")
        legend.setMinimumWidth(0)
        layout.addWidget(legend)

        return bar

    # =========================================================================
    # Audio Playback Toggle
    # =========================================================================
    def _toggle_audio_playback(self):
        if self.audio_manager.is_playing:
            self.audio_manager.stop()
            self.btn_play_audio.setText("🔊 Play Audio")
            self.btn_play_audio.setStyleSheet("background-color: rgba(244, 63, 94, 0.15); color: #f43f5e; border: 1px solid rgba(244, 63, 94, 0.5); border-radius: 7px; padding: 6px 16px; font-weight: 700;")
        else:
            target = self.original_file if self.original_file.lower().endswith(".wav") else self.current_file
            success = self.audio_manager.play(target, self.samp_rate)
            if success:
                self.btn_play_audio.setText("⏹ Stop Audio")
                self.btn_play_audio.setStyleSheet("background-color: #10b981; color: #ffffff; border: none; border-radius: 7px; padding: 6px 16px; font-weight: 800;")
            else:
                QtWidgets.QMessageBox.information(
                    self,
                    "Audio Playback",
                    "Could not generate audio playback for the current signal file."
                )

    # =========================================================================
    # Displays Update & Event Handlers
    # =========================================================================
    def _update_all_displays(self):
        """Updates UI parameters with real calculated physical properties."""
        m = self.metadata

        # Section 1: Input
        self.lbl_filename.setText(m.filename)
        sr_str = f"{self.samp_rate / 1e6:.2f} MS/s" if self.samp_rate >= 1e6 else f"{self.samp_rate / 1e3:.1f} kS/s"
        cf_str = f"{self.center_freq / 1e6:.3f} MHz" if abs(self.center_freq) >= 1e6 else (f"{self.center_freq / 1e3:.1f} kHz" if abs(self.center_freq) >= 1e3 else f"{self.center_freq:.0f} Hz")
        samples_str = f"{m.num_samples:,}" if m.num_samples > 0 else "--"

        self.badge_format.setText(f"Format: {m.datatype}")
        self.badge_samples.setText(f"Samples: {samples_str}")
        self.badge_rate.setText(f"Rate: {sr_str}")
        self.badge_duration.setText(f"Duration: {m.duration_str} ({m.filesize_str})")

        # Section 3: Signal Analysis
        self.m_peak_freq[1].setText(m.peak_frequency)
        self.m_center_freq[1].setText(cf_str)
        self.m_bandwidth[1].setText(m.occupied_bandwidth)
        self.m_signal_power[1].setText(m.signal_power_dbfs)

        self.m_noise_floor[1].setText(m.noise_floor)
        self.m_snr[1].setText(m.snr)
        self.m_rms[1].setText(m.rms_amplitude)
        self.m_peak_amp[1].setText(m.peak_amplitude)

        # Modulation
        self.lbl_mod_class.setText(m.modulation_class)
        self.lbl_mod_conf.setText(f"Confidence: {m.modulation_confidence}")

    def _open_settings(self):
        dialog = SettingsDialog(self, self.samp_rate, self.center_freq)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            new_rate, new_freq = dialog.get_values()
            self.samp_rate = new_rate
            self.center_freq = new_freq
            self.flowgraph.set_samp_rate(self.samp_rate)
            self.flowgraph.set_center_freq(self.center_freq)
            self.metadata = SignalMetadata(self.current_file, self.samp_rate, self.center_freq)
            self._update_all_displays()

    def _load_signal_file(self):
        """Unified file picker that loads any supported signal format (IQ binary or WAV audio)."""
        default_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
        if not os.path.exists(default_dir):
            default_dir = os.getcwd()
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select Signal Recording (IQ Binary or WAV Audio)",
            default_dir,
            "All Supported Signals (*.iq *.wav *.bin *.raw *.dat *.cfile);;"
            "IQ Binary Files (*.iq *.bin *.raw *.dat *.cfile);;"
            "WAV Audio Files (*.wav);;"
            "All Files (*.*)"
        )
        if not path or not os.path.exists(path):
            return

        self.audio_manager.stop()
        self.btn_play_audio.setText("🔊 Play Audio")
        self.btn_play_audio.setStyleSheet("background-color: rgba(244, 63, 94, 0.15); color: #f43f5e; border: 1px solid rgba(244, 63, 94, 0.5); border-radius: 7px; padding: 6px 16px; font-weight: 700;")

        self.original_file = path

        if path.lower().endswith(".wav"):
            try:
                out_iq, sr, num_samples, is_stereo = load_and_convert_wav(path)
                self.samp_rate = sr
                self.current_file = out_iq
                self.flowgraph.set_samp_rate(self.samp_rate)
                self.flowgraph.reload_file(self.current_file, repeat=self.is_looping)
                self.metadata = SignalMetadata(self.current_file, self.samp_rate, self.center_freq)
                self.metadata.filename = os.path.basename(path)
                self.metadata.datatype = "WAV Stereo IQ (fc32)" if is_stereo else "WAV Baseband Audio (fc32)"
                self._update_all_displays()
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "Signal Load Error", f"Could not load WAV file:\\n{e}")
        else:
            self.current_file = path
            fname_lower = os.path.basename(path).lower()
            if "250k" in fname_lower:
                self.samp_rate = 250000
            elif "1m" in fname_lower or "1msps" in fname_lower:
                self.samp_rate = 1000000

            self.flowgraph.set_samp_rate(self.samp_rate)
            self.flowgraph.reload_file(self.current_file, repeat=self.is_looping)
            self.metadata = SignalMetadata(self.current_file, self.samp_rate, self.center_freq)
            self._update_all_displays()

    def _load_iq_file(self):
        return self._load_signal_file()

    def _load_wav_file(self):
        return self._load_signal_file()

    def closeEvent(self, event):
        try:
            self.audio_manager.stop()
            self.flowgraph.stop()
            self.flowgraph.wait()
        except Exception:
            pass
        event.accept()
'''

with open('src/sigma_main_window.py', 'w', encoding='utf-8') as f:
    f.write(code)

print('Written src/sigma_main_window.py successfully!')
