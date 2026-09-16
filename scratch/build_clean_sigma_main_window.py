# -*- coding: utf-8 -*-
"""
Builder script to generate production-ready src/sigma_main_window.py
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

_src_dir = os.path.dirname(os.path.abspath(__file__))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

try:
    from .sigma_theme import COLORS, MAIN_QSS, create_sigma_icon
    from .sigma_analyzer_core import SignalMetadata, load_and_convert_wav
    from .sigma_flowgraph import SigmaFlowgraph
except (ImportError, ValueError):
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

        try:
            if filepath.lower().endswith(".wav"):
                self.current_audio_file = filepath
                winsound.PlaySound(filepath, winsound.SND_ASYNC | winsound.SND_FILENAME)
                self.is_playing = True
                return True
            else:
                # Synthesize quick preview audio from IQ file
                temp_wav = os.path.join(os.path.dirname(__file__), "..", "data", "_preview_audio.wav")
                os.makedirs(os.path.dirname(temp_wav), exist_ok=True)
                raw_data = np.fromfile(filepath, dtype=np.complex64, count=96000)
                if len(raw_data) == 0:
                    return False
                audio_mono = np.abs(raw_data)
                audio_mono = audio_mono - np.mean(audio_mono)
                mx = np.max(np.abs(audio_mono)) + 1e-9
                audio_norm = (audio_mono / mx * 32767.0).astype(np.int16)
                wavfile.write(temp_wav, 48000, audio_norm)
                self.current_audio_file = temp_wav
                winsound.PlaySound(temp_wav, winsound.SND_ASYNC | winsound.SND_FILENAME)
                self.is_playing = True
                return True
        except Exception as e:
            print(f"AudioManager playback error: {e}")
            self.is_playing = False
            return False

    def stop(self):
        if winsound is not None:
            try:
                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception:
                pass
        self.is_playing = False


class SettingsDialog(QtWidgets.QDialog):
    """Dialog to configure sampling rate and center frequency."""

    def __init__(self, parent=None, samp_rate=1000000, center_freq=0.0):
        super().__init__(parent)
        self.setWindowTitle("SIGMA — Ingestion Settings")
        self.setMinimumWidth(380)
        self.setStyleSheet("""
            QDialog {
                background-color: #0d0f12;
                border: 1px solid #202532;
                border-radius: 10px;
            }
            QLabel {
                color: #ffffff;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 12px;
            }
            QLineEdit {
                background-color: #171c26;
                color: #ffffff;
                border: 1px solid #2d3446;
                border-radius: 6px;
                padding: 7px 10px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #14b8a6;
            }
            QPushButton {
                background-color: #14b8a6;
                color: #0b0e14;
                border: none;
                border-radius: 6px;
                padding: 7px 16px;
                font-weight: 700;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #2dd4bf;
            }
            QPushButton#btnCancel {
                background-color: #1c212d;
                color: #cbd5e1;
                border: 1px solid #2d3446;
            }
            QPushButton#btnCancel:hover {
                background-color: #242b3a;
                color: #ffffff;
            }
        """)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QtWidgets.QLabel("Signal Ingestion Parameters")
        title.setStyleSheet("color: #ffffff; font-size: 15px; font-weight: 800;")
        layout.addWidget(title)

        desc = QtWidgets.QLabel("Configure hardware or capture attributes for IQ processing.")
        desc.setStyleSheet("color: #8e9bb0; font-size: 11px;")
        layout.addWidget(desc)

        layout.addSpacing(6)

        lbl_sr = QtWidgets.QLabel("Sample Rate (S/s):")
        layout.addWidget(lbl_sr)
        self.edit_sr = QtWidgets.QLineEdit(str(int(samp_rate)))
        layout.addWidget(self.edit_sr)

        lbl_cf = QtWidgets.QLabel("Center Frequency (Hz):")
        layout.addWidget(lbl_cf)
        self.edit_cf = QtWidgets.QLineEdit(str(int(center_freq)))
        layout.addWidget(self.edit_cf)

        layout.addSpacing(10)

        btn_box = QtWidgets.QHBoxLayout()
        btn_box.addStretch(1)
        self.btn_cancel = QtWidgets.QPushButton("Cancel")
        self.btn_cancel.setObjectName("btnCancel")
        self.btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(self.btn_cancel)

        self.btn_apply = QtWidgets.QPushButton("Apply Settings")
        self.btn_apply.clicked.connect(self.accept)
        btn_box.addWidget(self.btn_apply)
        layout.addLayout(btn_box)

    def get_values(self):
        try:
            sr = float(self.edit_sr.text().strip())
        except ValueError:
            sr = 1000000.0
        try:
            cf = float(self.edit_cf.text().strip())
        except ValueError:
            cf = 0.0
        return sr, cf


class SigmaMainWindow(QtWidgets.QMainWindow):
    """
    SIGMA Primary Intelligence Workstation Window.
    Full-width, responsive single-page architecture featuring high-contrast pure white typography.
    """

    def __init__(self, filepath=None, samp_rate=1000000, center_freq=0.0):
        super().__init__()
        self.setWindowTitle("SIGMA — Signal Intelligence & Generalized Modulation Analyzer")
        self.setWindowIcon(create_sigma_icon())
        self.resize(1280, 800)
        self.setMinimumSize(780, 520)

        self.original_file = resolve_sample_path(filepath)
        self.current_file = self.original_file
        self.samp_rate = samp_rate
        self.center_freq = center_freq
        self.is_looping = True
        self.current_view = "grid"

        # Audio manager
        self.audio_manager = AudioManager()

        # Physical signal metadata
        self.metadata = SignalMetadata(self.current_file, self.samp_rate, self.center_freq)

        # Initialize GNU Radio DSP flowgraph
        self.flowgraph = SigmaFlowgraph(
            filepath=self.current_file,
            samp_rate=self.samp_rate,
            center_freq=self.center_freq
        )
        self.flowgraph.start()

        self._init_ui()
        self._update_all_displays()

    def _init_ui(self):
        """Constructs the responsive single-page dashboard inside a QScrollArea."""
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.central_widget = QtWidgets.QWidget()
        self.central_widget.setObjectName("CentralWidget")
        self.central_layout = QtWidgets.QVBoxLayout(self.central_widget)
        self.central_layout.setContentsMargins(14, 12, 14, 12)
        self.central_layout.setSpacing(10)

        # 1. Header Section
        self.central_layout.addLayout(self._build_header())

        # 2. Input Signal Bar
        self.central_layout.addWidget(self._build_input_bar())

        # 3. Visualizations Section (2x2 Grid + Solo View Switcher)
        self.central_layout.addWidget(self._build_visualizations_section(), 1)

        # 4. Results Section (Signal Analysis & Modulation)
        self.central_layout.addLayout(self._build_results_section())

        # 5. Pipeline / Stepper Status Bar
        self.central_layout.addWidget(self._build_stepper_bar())

        self.scroll_area.setWidget(self.central_widget)
        self.setCentralWidget(self.scroll_area)

    # =========================================================================
    # 1. Header Section
    # =========================================================================
    def _build_header(self):
        header_layout = QtWidgets.QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)

        title_box = QtWidgets.QVBoxLayout()
        title_box.setSpacing(1)

        self.lbl_app_title = QtWidgets.QLabel("SIGMA")
        self.lbl_app_title.setStyleSheet("color: #ffffff; font-size: 20px; font-weight: 900; letter-spacing: 1.5px;")
        title_box.addWidget(self.lbl_app_title)

        self.lbl_app_sub = QtWidgets.QLabel("Signal Intelligence & Generalized Modulation Analyzer")
        self.lbl_app_sub.setStyleSheet("color: #cbd5e1; font-size: 11px; font-weight: 500;")
        title_box.addWidget(self.lbl_app_sub)

        header_layout.addLayout(title_box)
        header_layout.addStretch(1)

        # Settings button
        self.btn_settings = QtWidgets.QPushButton("⚙ Settings")
        self.btn_settings.setStyleSheet("""
            QPushButton {
                background-color: #171c26;
                color: #ffffff;
                border: 1px solid #2d3446;
                border-radius: 7px;
                padding: 6px 14px;
                font-weight: 700;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #242b3a;
                border: 1px solid #14b8a6;
                color: #14b8a6;
            }
        """)
        self.btn_settings.clicked.connect(self._open_settings)
        header_layout.addWidget(self.btn_settings)

        return header_layout

    # =========================================================================
    # 2. Input Signal Bar
    # =========================================================================
    def _build_input_bar(self):
        card = QtWidgets.QFrame()
        card.setProperty("class", "SigmaBigCard")
        card.setStyleSheet("""
            QFrame {
                background-color: #13161f;
                border: 1px solid #202532;
                border-radius: 10px;
                padding: 8px 12px;
            }
        """)

        layout = QtWidgets.QHBoxLayout(card)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(10)

        # Signal Name Badge
        lbl_tag = QtWidgets.QLabel("INPUT SIGNAL")
        lbl_tag.setStyleSheet("color: #14b8a6; font-size: 11px; font-weight: 800; letter-spacing: 1px;")
        layout.addWidget(lbl_tag)

        self.lbl_filename = QtWidgets.QLabel(os.path.basename(self.current_file))
        self.lbl_filename.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: 800;")
        layout.addWidget(self.lbl_filename)

        layout.addSpacing(6)

        # Badges
        badge_style = "background-color: #171c26; color: #ffffff; border: 1px solid #2d3446; border-radius: 6px; padding: 4px 10px; font-size: 11px; font-weight: 600;"

        self.badge_format = QtWidgets.QLabel("Format: Complex Float32 (fc32)")
        self.badge_format.setStyleSheet(badge_style)
        layout.addWidget(self.badge_format)

        self.badge_samples = QtWidgets.QLabel("Samples: --")
        self.badge_samples.setStyleSheet(badge_style)
        layout.addWidget(self.badge_samples)

        self.badge_rate = QtWidgets.QLabel(f"Rate: {self.samp_rate/1e6:.2f} MS/s")
        self.badge_rate.setStyleSheet(badge_style)
        layout.addWidget(self.badge_rate)

        self.badge_duration = QtWidgets.QLabel("Duration: --")
        self.badge_duration.setStyleSheet(badge_style)
        layout.addWidget(self.badge_duration)

        layout.addStretch(1)

        # Load Signal Button
        self.btn_load_file = QtWidgets.QPushButton("📁 Load Signal File")
        self.btn_load_file.setStyleSheet("""
            QPushButton {
                background-color: #38bdf8;
                color: #0b0e14;
                border: none;
                border-radius: 7px;
                padding: 6px 16px;
                font-weight: 800;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #7dd3fc;
            }
        """)
        self.btn_load_file.clicked.connect(lambda: self.load_signal_file(None))
        layout.addWidget(self.btn_load_file)

        # Audio Playback Button
        self.btn_play_audio = QtWidgets.QPushButton("🔊 Play Audio")
        self.btn_play_audio.setStyleSheet("""
            QPushButton {
                background-color: rgba(244, 63, 94, 0.15);
                color: #f43f5e;
                border: 1px solid rgba(244, 63, 94, 0.5);
                border-radius: 7px;
                padding: 6px 16px;
                font-weight: 700;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(244, 63, 94, 0.25);
            }
        """)
        self.btn_play_audio.clicked.connect(self._toggle_audio_playback)
        layout.addWidget(self.btn_play_audio)

        return card

    # =========================================================================
    # 3. Visualizations Section (2x2 Grid + Solo View Switcher)
    # =========================================================================
    def _build_visualizations_section(self):
        container_widget = QtWidgets.QWidget()
        container = QtWidgets.QVBoxLayout(container_widget)
        container.setContentsMargins(0, 0, 0, 0)
        container.setSpacing(6)

        # Top Bar: Title & View Switcher Buttons
        top_bar = QtWidgets.QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)

        lbl_viz = QtWidgets.QLabel("SIGNAL VISUALIZATIONS")
        lbl_viz.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 800; letter-spacing: 1.2px;")
        top_bar.addWidget(lbl_viz)

        top_bar.addStretch(1)

        self.btn_views = {}
        views = [
            ("grid", "⊞ 2x2 Grid"),
            ("time", "⏱ Time"),
            ("freq", "📊 Spectrum"),
            ("waterfall", "🌊 Waterfall"),
            ("const", "✦ Constellation")
        ]

        for key, text in views:
            btn = QtWidgets.QPushButton(text)
            btn.setCheckable(True)
            btn.setProperty("view_key", key)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #171c26;
                    color: #cbd5e1;
                    border: 1px solid #2d3446;
                    border-radius: 6px;
                    padding: 5px 11px;
                    font-size: 11px;
                    font-weight: 700;
                }
                QPushButton:hover {
                    background-color: #242b3a;
                    color: #ffffff;
                }
            """)
            btn.clicked.connect(lambda checked, k=key: self._switch_view_mode(k))
            self.btn_views[key] = btn
            top_bar.addWidget(btn)

        self.btn_views["grid"].setChecked(True)
        self._refresh_view_toggle_styles("grid")

        container.addLayout(top_bar)

        # Visualization Splitter (Upper row & Lower row)
        self.viz_splitter = QtWidgets.QSplitter(Qt.Vertical)
        self.viz_splitter.setHandleWidth(4)

        # Row 1: Time Domain & Spectrum
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
        h_time.addWidget(t_time)

        h_time.addStretch(1)
        self.hud_time = QtWidgets.QLabel("● I (cyan)   ● Q (magenta)")
        self.hud_time.setStyleSheet("color: #cbd5e1; font-size: 11px; font-weight: 700;")
        h_time.addWidget(self.hud_time)
        lay_time.addLayout(h_time)
        lay_time.addWidget(self.flowgraph.time_sink_widget, 1)
        lay_upper.addWidget(self.card_time, 1)
        self._attach_hud_overlay(self.flowgraph.time_sink_widget, self.hud_time, "time", "● I (cyan)   ● Q (magenta)")

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
        h_freq.addWidget(t_freq)

        h_freq.addStretch(1)
        self.hud_freq = QtWidgets.QLabel("1024-pt FFT • dBFS")
        self.hud_freq.setStyleSheet("color: #cbd5e1; font-size: 11px; font-weight: 600;")
        h_freq.addWidget(self.hud_freq)
        lay_freq.addLayout(h_freq)
        lay_freq.addWidget(self.flowgraph.freq_sink_widget, 1)
        lay_upper.addWidget(self.card_freq, 1)
        self._attach_hud_overlay(self.flowgraph.freq_sink_widget, self.hud_freq, "freq", "1024-pt FFT • dBFS")

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
        h_wf.addWidget(t_wf)

        h_wf.addStretch(1)
        self.hud_wf = QtWidgets.QLabel("Intensity over Time")
        self.hud_wf.setStyleSheet("color: #cbd5e1; font-size: 11px; font-weight: 600;")
        h_wf.addWidget(self.hud_wf)
        lay_wf.addLayout(h_wf)
        lay_wf.addWidget(self.flowgraph.waterfall_sink_widget, 1)
        lay_lower.addWidget(self.card_waterfall, 1)
        self._attach_hud_overlay(self.flowgraph.waterfall_sink_widget, self.hud_wf, "waterfall", "Intensity over Time")

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
        h_const.addWidget(t_const)

        h_const.addStretch(1)
        self.hud_const = QtWidgets.QLabel("In-Phase (I) vs Quadrature (Q)")
        self.hud_const.setStyleSheet("color: #cbd5e1; font-size: 11px; font-weight: 600;")
        h_const.addWidget(self.hud_const)
        lay_const.addLayout(h_const)
        lay_const.addWidget(self.flowgraph.const_sink_widget, 1)
        lay_lower.addWidget(self.card_const, 1)
        self._attach_hud_overlay(self.flowgraph.const_sink_widget, self.hud_const, "const", "In-Phase (I) vs Quadrature (Q)")

        self.viz_splitter.addWidget(self.w_lower_row)

        self.viz_splitter.setSizes([220, 220])
        container.addWidget(self.viz_splitter, 1)

        return container_widget

    def _refresh_view_toggle_styles(self, active_key):
        for k, b in self.btn_views.items():
            if k == active_key:
                b.setStyleSheet("background-color: rgba(56, 189, 248, 0.22); color: #38bdf8; border: 1.5px solid #38bdf8; border-radius: 6px; padding: 5px 11px; font-weight: 800; font-size: 11px;")
            else:
                b.setStyleSheet("background-color: #171c26; color: #cbd5e1; border: 1px solid #2d3446; border-radius: 6px; padding: 5px 11px; font-size: 11px; font-weight: 700;")

    def _switch_view_mode(self, mode):
        self.current_view = mode
        self._refresh_view_toggle_styles(mode)

        if mode == "grid":
            self.w_upper_row.show()
            self.w_lower_row.show()
            self.card_time.show()
            self.card_freq.show()
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

    def _attach_hud_overlay(self, widget, label, kind="time", default_text=""):
        """Connects plot zoomer to inspect HUD label."""
        default_hint = default_text
        default_style = label.styleSheet()

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
                        lbl.setStyleSheet("color: #38bdf8; font-family: 'Consolas', monospace; font-size: 11px; font-weight: 700;")
                    return on_point

                def make_rect_handler(lbl, k):
                    def on_zoomed(rect):
                        lbl.setText(f"🔍 Zoomed [{rect.left():.1f} → {rect.right():.1f}]")
                        lbl.setStyleSheet("color: #38bdf8; font-family: 'Consolas', monospace; font-size: 11px; font-weight: 700;")
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
                    def __init__(self, lbl, hint, style):
                        super().__init__()
                        self.lbl = lbl
                        self.hint = hint
                        self.style = style
                    def eventFilter(self, obj, ev):
                        if ev.type() == QtCore.QEvent.MouseButtonPress and ev.button() == QtCore.Qt.RightButton:
                            def _restore():
                                self.lbl.setText(self.hint)
                                self.lbl.setStyleSheet(self.style)
                            QtCore.QTimer.singleShot(120, _restore)
                        return False

                filt = UnzoomFilter(label, default_hint, default_style)
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
        lay_an.addWidget(t_analysis)

        # Metrics Grid (2 rows x 4 cols, fully responsive)
        grid = QtWidgets.QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)

        self.m_peak_freq = self._create_metric_cell("PEAK FREQUENCY", "--")
        self.m_center_freq = self._create_metric_cell("CENTER FREQUENCY", "--")
        self.m_bandwidth = self._create_metric_cell("BANDWIDTH", "--")
        self.m_signal_power = self._create_metric_cell("SIGNAL POWER", "--")

        self.m_noise_floor = self._create_metric_cell("NOISE FLOOR", "--")
        self.m_snr = self._create_metric_cell("SIGNAL SNR", "--")
        self.m_rms = self._create_metric_cell("RMS AMPLITUDE", "--")
        self.m_peak_amp = self._create_metric_cell("PEAK AMPLITUDE", "--")

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
        card_mod.setMinimumWidth(220)
        lay_mod = QtWidgets.QVBoxLayout(card_mod)
        lay_mod.setContentsMargins(12, 8, 12, 8)
        lay_mod.setSpacing(6)

        t_mod = QtWidgets.QLabel("MODULATION")
        t_mod.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 800; letter-spacing: 1.2px;")
        lay_mod.addWidget(t_mod)

        self.lbl_mod_class = QtWidgets.QLabel("Not analyzed")
        self.lbl_mod_class.setStyleSheet("color: #f59e0b; font-size: 16px; font-weight: 900; margin-top: 4px;")
        lay_mod.addWidget(self.lbl_mod_class)

        self.lbl_mod_conf = QtWidgets.QLabel("Confidence: --")
        self.lbl_mod_conf.setStyleSheet("color: #10b981; font-size: 12px; font-weight: 700;")
        lay_mod.addWidget(self.lbl_mod_conf)

        lay_mod.addStretch(1)
        container.addWidget(card_mod, 3)

        return container

    def _create_metric_cell(self, title_text, init_value):
        cell = QtWidgets.QFrame()
        cell.setStyleSheet("""
            QFrame {
                background-color: #171c26;
                border: 1px solid #243042;
                border-radius: 6px;
                padding: 4px 8px;
            }
        """)
        lay = QtWidgets.QVBoxLayout(cell)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.setSpacing(1)

        t = QtWidgets.QLabel(title_text)
        t.setStyleSheet("color: #cbd5e1; font-size: 10px; font-weight: 700; letter-spacing: 0.5px;")
        lay.addWidget(t)

        v = QtWidgets.QLabel(init_value)
        v.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: 800; font-family: 'Consolas', monospace;")
        lay.addWidget(v)

        return cell, v

    # =========================================================================
    # 5. Section 4: Stepper / Pipeline Status Bar
    # =========================================================================
    def _build_stepper_bar(self):
        bar = QtWidgets.QFrame()
        bar.setStyleSheet("""
            QFrame {
                background-color: #0f1218;
                border: 1px solid #202532;
                border-radius: 8px;
                padding: 4px 10px;
            }
        """)
        layout = QtWidgets.QHBoxLayout(bar)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(8)

        steps = [
            ("INPUT", "✓", True),
            ("ANALYSIS", "✓", True),
            ("MODULATION", "⟳", False),
            ("DEMOD", "○", False),
            ("BITS", "○", False)
        ]

        for idx, (name, icon, is_done) in enumerate(steps):
            w = QtWidgets.QLabel(f"{name} {icon}")
            if is_done:
                w.setStyleSheet("color: #10b981; font-size: 11px; font-weight: 800; background-color: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.35); border-radius: 5px; padding: 3px 8px;")
            else:
                w.setStyleSheet("color: #8e9bb0; font-size: 11px; font-weight: 600; background-color: #171c26; border: 1px solid #243042; border-radius: 5px; padding: 3px 8px;")
            layout.addWidget(w)

            if idx < len(steps) - 1:
                sep = QtWidgets.QLabel("→")
                sep.setStyleSheet("color: #475569; font-weight: 700; font-size: 12px;")
                layout.addWidget(sep)

        layout.addStretch(1)
        legend = QtWidgets.QLabel("✓ completed   ⟳ processing   ○ not available")
        legend.setStyleSheet("color: #64748b; font-size: 10px; font-style: italic;")
        layout.addWidget(legend)

        return bar

    # =========================================================================
    # Audio Playback
    # =========================================================================
    def _toggle_audio_playback(self):
        if self.audio_manager.is_playing:
            self.audio_manager.stop()
            self.btn_play_audio.setText("🔊 Play Audio")
            self.btn_play_audio.setStyleSheet("background-color: rgba(244, 63, 94, 0.15); color: #f43f5e; border: 1px solid rgba(244, 63, 94, 0.5); border-radius: 7px; padding: 6px 16px; font-weight: 700;")
        else:
            success = self.audio_manager.play(self.current_file, self.samp_rate)
            if success:
                self.btn_play_audio.setText("⏹ Stop Audio")
                self.btn_play_audio.setStyleSheet("background-color: rgba(16, 185, 129, 0.2); color: #10b981; border: 1px solid #10b981; border-radius: 7px; padding: 6px 16px; font-weight: 800;")
            else:
                QtWidgets.QMessageBox.information(
                    self, "Audio Playback",
                    "Audio playback is only available for supported WAV or demodulated IQ files on Windows."
                )

    # =========================================================================
    # Signal State & Display Updates
    # =========================================================================
    def _update_all_displays(self):
        """Updates UI parameters with real calculated physical properties."""
        m = self.metadata
        if not m:
            return

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

    def load_file(self, filepath=None):
        return self.load_signal_file(filepath)

    def _load_signal_file(self, filepath=None):
        return self.load_signal_file(filepath)

    def load_signal_file(self, filepath=None):
        """Unified file loader that loads any supported signal format (IQ binary or WAV audio)."""
        if filepath is None:
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
        else:
            path = filepath

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
        return self.load_signal_file(None)

    def _load_wav_file(self):
        return self.load_signal_file(None)

    def closeEvent(self, event):
        try:
            self.audio_manager.stop()
            self.flowgraph.stop()
            self.flowgraph.wait()
        except Exception:
            pass
        event.accept()


MainWindow = SigmaMainWindow
'''

with open('src/sigma_main_window.py', 'w', encoding='utf-8') as f:
    f.write(code)

print('Generated clean src/sigma_main_window.py successfully!')
