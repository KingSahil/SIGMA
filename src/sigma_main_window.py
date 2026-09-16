"""
SIGMA - Signal Intelligence & Generalized Modulation Analyzer
Big, Spacious, Modern UI (Google Stitch / Material Design 3)
Features Native Audio Playback, Large Typography, High Readability
"""

import os
import sys
import winsound
import numpy as np
import scipy.io.wavfile as wavfile
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt

try:
    from .sigma_theme import COLORS, MAIN_QSS, create_sigma_icon
    from .sigma_analyzer_core import SignalMetadata, load_and_convert_wav
    from .sigma_flowgraph import SigmaFlowgraph
except ImportError:
    from sigma_theme import COLORS, MAIN_QSS, create_sigma_icon
    from sigma_analyzer_core import SignalMetadata, load_and_convert_wav
    from sigma_flowgraph import SigmaFlowgraph


def resolve_sample_path(filepath=None):
    """Resolves an IQ sample file path, checking standard data locations."""
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

        # If it's a WAV file, check if 16-bit PCM for winsound, or re-export
        if filepath.lower().endswith(".wav"):
            target_wav = self._prepare_wav_for_playback(filepath)
        else:
            # IQ binary file: convert envelope / audio baseband to preview WAV
            target_wav = self._convert_iq_to_audio_wav(filepath, samp_rate)

        if target_wav and os.path.exists(target_wav):
            self.current_audio_file = target_wav
            self.is_playing = True
            # Play in background looping mode so user can comfortably listen
            flags = winsound.SND_ASYNC | winsound.SND_FILENAME | winsound.SND_LOOP
            winsound.PlaySound(target_wav, flags)
            return True
        return False

    def stop(self):
        if self.is_playing:
            winsound.PlaySound(None, winsound.SND_PURGE)
            self.is_playing = False

    def _prepare_wav_for_playback(self, wav_path):
        """Ensures WAV file is in standard 16-bit PCM for Windows audio playback."""
        try:
            sr, data = wavfile.read(wav_path)
            if data.dtype == np.int16 and data.ndim == 1:
                return wav_path

            # Normalize to 16-bit PCM mono/stereo
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
        """
        Converts any IQ baseband signal into rich, audible audio.
        Uses multi-mode demodulation: FM discriminator + BFO audio heterodyne (1.2 kHz).
        Seamlessly loops to ensure at least 3.0 seconds of clear continuous listening.
        """
        try:
            # Read up to 1,000,000 samples to prevent high memory usage on large files
            samples = np.fromfile(iq_path, dtype=np.complex64, count=1000000)
            if len(samples) == 0:
                return None

            # 1. Extend short signals so playback lasts at least 3.0 seconds
            raw_duration = len(samples) / float(samp_rate) if samp_rate > 0 else 0.05
            if raw_duration < 3.0:
                repeats = int(np.ceil(3.0 / max(raw_duration, 0.001)))
                repeats = min(repeats, 80)
                samples = np.tile(samples, repeats)

            # 2. Decimate to standard audio sample rate (44.1 kHz) with anti-aliasing
            audio_rate = 44100
            decim = max(1, int(samp_rate / audio_rate))
            if decim > 1 and len(samples) >= decim:
                trim_len = (len(samples) // decim) * decim
                sub_samples = samples[:trim_len].reshape(-1, decim).mean(axis=1)
            else:
                sub_samples = samples[::decim]
            actual_fs = samp_rate / decim

            # 3. FM Discriminator
            if len(sub_samples) > 1:
                fm_demod = np.angle(sub_samples[1:] * np.conj(sub_samples[:-1]))
                fm_demod = np.append(fm_demod, fm_demod[-1])
                fm_std = np.std(fm_demod)
            else:
                fm_demod = np.zeros(len(sub_samples))
                fm_std = 0.0

            # 4. BFO Heterodyne Mixer (shifts baseband complex IQ to 1.2 kHz audible pitch)
            t = np.arange(len(sub_samples)) / float(actual_fs)
            bfo = np.exp(1j * 2 * np.pi * 1200.0 * t)
            heterodyne = np.real(sub_samples * bfo)

            # 5. Envelope (AM)
            env = np.abs(sub_samples)
            env_ac = env - np.mean(env)

            # Blend modes based on signal properties
            if fm_std > 0.15:
                # Strong FM/FSK content
                audio = (fm_demod - np.mean(fm_demod)) * 0.75 + heterodyne * 0.25
            elif np.std(env_ac) > 0.12:
                # Strong AM content
                audio = env_ac * 0.75 + heterodyne * 0.25
            else:
                # Digital phase modulation (PSK/QPSK) or CW
                audio = heterodyne

            # Normalize & balance volume
            audio = audio - np.mean(audio)
            peak = np.max(np.abs(audio))
            if peak > 1e-6:
                audio = (audio / peak) * 0.88

            # Resample to exact 44100 Hz if needed
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
            print(f"[SIGMA Audio] IQ Audio generation error: {e}")
            return None


class SettingsDialog(QtWidgets.QDialog):
    """Clean, spacious settings dialog for RF configuration."""

    def __init__(self, parent=None, samp_rate=1000000, center_freq=0.0):
        super().__init__(parent)
        self.setWindowTitle("SIGMA — Hardware & DSP Configuration")
        self.setMinimumWidth(440)
        self.setStyleSheet(MAIN_QSS)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(18)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QtWidgets.QLabel("RF HARDWARE & DSP SETTINGS")
        title.setProperty("class", "SectionTitle")
        layout.addWidget(title)

        form = QtWidgets.QFormLayout()
        form.setSpacing(16)

        # Sample Rate
        self.rate_spin = QtWidgets.QDoubleSpinBox()
        self.rate_spin.setRange(1e3, 100e6)
        self.rate_spin.setValue(samp_rate)
        self.rate_spin.setSingleStep(100e3)
        self.rate_spin.setSuffix(" S/s")
        form.addRow("Sample Rate:", self.rate_spin)

        # Center Frequency
        self.freq_spin = QtWidgets.QDoubleSpinBox()
        self.freq_spin.setRange(-10e9, 10e9)
        self.freq_spin.setValue(center_freq)
        self.freq_spin.setSingleStep(10e3)
        self.freq_spin.setSuffix(" Hz")
        form.addRow("Center Frequency:", self.freq_spin)

        layout.addLayout(form)

        # Buttons
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
    Main desktop interface for the SIGMA system.
    Big, modern, user-friendly Google Stitch design with native audio playback.
    """

    def __init__(self, initial_file="signal.iq"):
        super().__init__()
        self.setWindowTitle("SIGMA — Signal Intelligence & Generalized Modulation Analyzer")
        self.setWindowIcon(create_sigma_icon())
        self.resize(1400, 880)
        self.setMinimumSize(960, 600)

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

        # Populate initial plot preview and keep waves frozen (only move when playing audio)
        self.flowgraph.capture_preview(duration_sec=0.15)

    # =========================================================================
    # Main UI Construction
    # =========================================================================
    def _init_ui(self):
        # Root Scroll Area to guarantee seamless display on all screen resolutions and DPI scaling
        scroll = QtWidgets.QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setCentralWidget(scroll)

        central = QtWidgets.QWidget()
        central.setObjectName("CentralWidget")
        scroll.setWidget(central)

        main_layout = QtWidgets.QVBoxLayout(central)
        main_layout.setContentsMargins(24, 18, 24, 18)
        main_layout.setSpacing(16)

        # 1. Header Bar (Big & Spacious)
        main_layout.addWidget(self._build_header())

        # 2. Section 1: Input Signal Card
        main_layout.addWidget(self._build_input_section())

        # 3. Section 2: Visualizations (3 Big Cards in Splitter)
        main_layout.addWidget(self._build_visualizations_section(), 1)

        # 4. Section 3: Results (Signal Analysis & Modulation)
        main_layout.addWidget(self._build_results_section())

        # 5. Bottom: Big Clean Processing Flow
        main_layout.addWidget(self._build_processing_flow())

    # =========================================================================
    # 1. Big Header Section
    # =========================================================================
    def _build_header(self):
        header = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 6)
        layout.setSpacing(16)

        # Left: Branding
        brand_box = QtWidgets.QVBoxLayout()
        brand_box.setSpacing(4)

        title = QtWidgets.QLabel("SIGMA")
        title.setProperty("class", "AppTitle")
        brand_box.addWidget(title)

        subtitle = QtWidgets.QLabel("Signal Intelligence & Generalized Modulation Analyzer")
        subtitle.setProperty("class", "AppSubtitle")
        brand_box.addWidget(subtitle)

        layout.addLayout(brand_box)
        layout.addStretch(1)

        # Right: Settings
        ctrl_box = QtWidgets.QHBoxLayout()
        ctrl_box.setSpacing(16)

        self.btn_settings = QtWidgets.QPushButton("⚙ Settings")
        self.btn_settings.clicked.connect(self._open_settings)
        ctrl_box.addWidget(self.btn_settings)

        layout.addLayout(ctrl_box)
        return header

    # =========================================================================
    # 2. Section 1: Big Input Signal Card
    # =========================================================================
    # =========================================================================
    # 2. Section 1: Compact Input Signal Bar
    # =========================================================================
    def _build_input_section(self):
        card = QtWidgets.QFrame()
        card.setProperty("class", "SigmaBigCard")
        layout = QtWidgets.QHBoxLayout(card)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(10)

        tag = QtWidgets.QLabel("INPUT")
        tag.setProperty("class", "SectionTitle")
        layout.addWidget(tag)

        self.lbl_filename = QtWidgets.QLabel(os.path.basename(self.current_file) if self.current_file else "signal.iq")
        self.lbl_filename.setProperty("class", "FileName")
        layout.addWidget(self.lbl_filename)

        self.badge_format = QtWidgets.QLabel("Format: Complex Float32")
        self.badge_format.setProperty("class", "FileDetailBadge")
        layout.addWidget(self.badge_format)

        self.badge_samples = QtWidgets.QLabel("Samples: 50,000")
        self.badge_samples.setProperty("class", "FileDetailBadge")
        layout.addWidget(self.badge_samples)

        self.badge_rate = QtWidgets.QLabel("Rate: 1.00 MS/s")
        self.badge_rate.setProperty("class", "FileDetailBadge")
        layout.addWidget(self.badge_rate)

        self.badge_duration = QtWidgets.QLabel("Duration: 50.00 ms (400.0 KB)")
        self.badge_duration.setProperty("class", "FileDetailBadge")
        layout.addWidget(self.badge_duration)

        layout.addStretch(1)

        self.btn_load_signal = QtWidgets.QPushButton("📂 Load Signal File")
        self.btn_load_signal.setProperty("class", "PrimaryBtn")
        self.btn_load_signal.clicked.connect(self._load_signal_file)
        layout.addWidget(self.btn_load_signal)

        # Backwards compatibility aliases
        self.btn_load_iq = self.btn_load_signal
        self.btn_load_wav = self.btn_load_signal

        self.btn_play_audio = QtWidgets.QPushButton("🔊 Play Audio")
        self.btn_play_audio.setProperty("class", "AudioBtnIdle")
        self.btn_play_audio.clicked.connect(self._toggle_audio_playback)
        layout.addWidget(self.btn_play_audio)

        return card

    # =========================================================================
    # 3. Section 2: Visualizations with View Switcher (Quad 2x2 or Full Views)
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
        v_title.setProperty("class", "SectionTitle")
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
            b.setProperty("class", "ViewToggleBtnActive" if key == "quad" else "ViewToggleBtn")
            b.clicked.connect(lambda _, k=key: self._set_view_mode(k))
            tb.addWidget(b)
            self.btn_views[key] = b

        container.addLayout(tb)

        # Splitter hosting 2 rows of cards
        self.viz_splitter = QtWidgets.QSplitter(Qt.Vertical)
        self.viz_splitter.setChildrenCollapsible(False)
        self.viz_splitter.setHandleWidth(8)

        # Row 1: Time Domain & Frequency Spectrum
        self.w_upper_row = QtWidgets.QWidget()
        lay_upper = QtWidgets.QHBoxLayout(self.w_upper_row)
        lay_upper.setContentsMargins(0, 0, 0, 0)
        lay_upper.setSpacing(8)

        # Card 1: Time Domain
        self.card_time = QtWidgets.QFrame()
        self.card_time.setProperty("class", "SigmaBigCard")
        lay_time = QtWidgets.QVBoxLayout(self.card_time)
        lay_time.setContentsMargins(10, 6, 10, 6)
        lay_time.setSpacing(4)

        h_time = QtWidgets.QHBoxLayout()
        t_time = QtWidgets.QLabel("TIME DOMAIN")
        t_time.setProperty("class", "SectionTitle")
        h_time.addWidget(t_time)

        self.hud_time = QtWidgets.QLabel("📍 Click/Drag to Inspect")
        self.hud_time.setProperty("class", "HudOverlayBadge")
        h_time.addWidget(self.hud_time)

        h_time.addStretch(1)
        leg_time = QtWidgets.QLabel("● I (cyan)   ● Q (magenta)")
        leg_time.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px; font-weight: 700;")
        h_time.addWidget(leg_time)
        lay_time.addLayout(h_time)
        lay_time.addWidget(self.flowgraph.time_sink_widget, 1)
        lay_upper.addWidget(self.card_time, 1)
        self._attach_hud_overlay(self.flowgraph.time_sink_widget, self.hud_time, "time")

        # Card 2: Frequency Spectrum
        self.card_freq = QtWidgets.QFrame()
        self.card_freq.setProperty("class", "SigmaBigCard")
        lay_freq = QtWidgets.QVBoxLayout(self.card_freq)
        lay_freq.setContentsMargins(10, 6, 10, 6)
        lay_freq.setSpacing(4)

        h_freq = QtWidgets.QHBoxLayout()
        t_freq = QtWidgets.QLabel("FREQUENCY SPECTRUM")
        t_freq.setProperty("class", "SectionTitle")
        h_freq.addWidget(t_freq)

        self.hud_freq = QtWidgets.QLabel("📍 Click/Drag to Inspect")
        self.hud_freq.setProperty("class", "HudOverlayBadge")
        h_freq.addWidget(self.hud_freq)

        h_freq.addStretch(1)
        leg_freq = QtWidgets.QLabel("1024-pt FFT • -140 to +10 dB")
        leg_freq.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px; font-weight: 600;")
        h_freq.addWidget(leg_freq)
        lay_freq.addLayout(h_freq)
        lay_freq.addWidget(self.flowgraph.freq_sink_widget, 1)
        lay_upper.addWidget(self.card_freq, 1)
        self._attach_hud_overlay(self.flowgraph.freq_sink_widget, self.hud_freq, "freq")

        self.viz_splitter.addWidget(self.w_upper_row)

        # Row 2: Waterfall & Constellation
        self.w_lower_row = QtWidgets.QWidget()
        lay_lower = QtWidgets.QHBoxLayout(self.w_lower_row)
        lay_lower.setContentsMargins(0, 0, 0, 0)
        lay_lower.setSpacing(8)

        # Card 3: Waterfall (Spectrogram)
        self.card_waterfall = QtWidgets.QFrame()
        self.card_waterfall.setProperty("class", "SigmaBigCard")
        lay_wf = QtWidgets.QVBoxLayout(self.card_waterfall)
        lay_wf.setContentsMargins(10, 6, 10, 6)
        lay_wf.setSpacing(4)

        h_wf = QtWidgets.QHBoxLayout()
        t_wf = QtWidgets.QLabel("WATERFALL (SPECTROGRAM)")
        t_wf.setProperty("class", "SectionTitle")
        h_wf.addWidget(t_wf)

        self.hud_wf = QtWidgets.QLabel("📍 Click/Drag to Inspect")
        self.hud_wf.setProperty("class", "HudOverlayBadge")
        h_wf.addWidget(self.hud_wf)

        h_wf.addStretch(1)
        leg_wf = QtWidgets.QLabel("Intensity over Time")
        leg_wf.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px; font-weight: 600;")
        h_wf.addWidget(leg_wf)
        lay_wf.addLayout(h_wf)
        lay_wf.addWidget(self.flowgraph.waterfall_sink_widget, 1)
        lay_lower.addWidget(self.card_waterfall, 1)
        self._attach_hud_overlay(self.flowgraph.waterfall_sink_widget, self.hud_wf, "waterfall")

        # Card 4: Constellation
        self.card_const = QtWidgets.QFrame()
        self.card_const.setProperty("class", "SigmaBigCard")
        lay_const = QtWidgets.QVBoxLayout(self.card_const)
        lay_const.setContentsMargins(10, 6, 10, 6)
        lay_const.setSpacing(4)

        h_const = QtWidgets.QHBoxLayout()
        t_const = QtWidgets.QLabel("CONSTELLATION DIAGRAM")
        t_const.setProperty("class", "SectionTitle")
        h_const.addWidget(t_const)

        self.hud_const = QtWidgets.QLabel("📍 Click/Drag to Inspect")
        self.hud_const.setProperty("class", "HudOverlayBadge")
        h_const.addWidget(self.hud_const)

        h_const.addStretch(1)
        leg_const = QtWidgets.QLabel("Quadrature (Q) vs In-Phase (I)")
        leg_const.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px; font-weight: 600;")
        h_const.addWidget(leg_const)
        lay_const.addLayout(h_const)
        lay_const.addWidget(self.flowgraph.const_sink_widget, 1)
        lay_lower.addWidget(self.card_const, 1)
        self._attach_hud_overlay(self.flowgraph.const_sink_widget, self.hud_const, "const")

        self.viz_splitter.addWidget(self.w_lower_row)

        # Set default split sizes
        self.viz_splitter.setSizes([220, 220])
        container.addWidget(self.viz_splitter, 1)

        return container_widget

    def _set_view_mode(self, mode):
        """Switches between Quad View and expanded individual plot views."""
        for k, btn in self.btn_views.items():
            btn.setProperty("class", "ViewToggleBtnActive" if k == mode else "ViewToggleBtn")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        if mode == "quad":
            self.w_upper_row.show()
            self.card_time.show()
            self.card_freq.show()
            self.w_lower_row.show()
            self.card_waterfall.show()
            self.card_const.show()
            self.viz_splitter.setSizes([220, 220])
        elif mode == "time":
            self.w_upper_row.show()
            self.card_time.show()
            self.card_freq.hide()
            self.w_lower_row.hide()
        elif mode == "freq":
            self.w_upper_row.show()
            self.card_freq.show()
            self.card_time.hide()
            self.w_lower_row.hide()
        elif mode == "waterfall":
            self.w_upper_row.hide()
            self.w_lower_row.show()
            self.card_waterfall.show()
            self.card_const.hide()
        elif mode == "const":
            self.w_upper_row.hide()
            self.w_lower_row.show()
            self.card_const.show()
            self.card_waterfall.hide()

    def _attach_hud_overlay(self, widget, label, kind="time"):
        """Connects QwtPlotZoomer from a sink widget to an external high-contrast HUD overlay badge."""
        default_hint = "📍 Click/Drag to Inspect"

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
                            lbl.setText(f"📍 {x_str}  |  {y:+.4f} V")
                        elif k == "freq":
                            if abs(x) >= 1000:
                                x_str = f"{x/1000.0:.3f} MHz"
                            else:
                                x_str = f"{x:.2f} kHz"
                            lbl.setText(f"📍 {x_str}  |  {y:+.1f} dB")
                        elif k == "waterfall":
                            lbl.setText(f"📍 {x:.2f} kHz  |  {y:.2f} s")
                        elif k == "const":
                            lbl.setText(f"📍 I: {x:+.3f}  |  Q: {y:+.3f}")
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

        # Install event filter on canvas to detect right-click unzoom and reset hint
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
        lay_an = QtWidgets.QVBoxLayout(card_analysis)
        lay_an.setContentsMargins(12, 8, 12, 8)
        lay_an.setSpacing(6)

        t_analysis = QtWidgets.QLabel("SIGNAL ANALYSIS & DSP METRICS")
        t_analysis.setProperty("class", "SectionTitle")
        lay_an.addWidget(t_analysis)

        # Metrics Grid (2 rows x 4 cols, compact)
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

        # Row 1
        grid.addWidget(self.m_peak_freq[0], 0, 0)
        grid.addWidget(self.m_center_freq[0], 0, 1)
        grid.addWidget(self.m_bandwidth[0], 0, 2)
        grid.addWidget(self.m_signal_power[0], 0, 3)

        # Row 2
        grid.addWidget(self.m_noise_floor[0], 1, 0)
        grid.addWidget(self.m_snr[0], 1, 1)
        grid.addWidget(self.m_rms[0], 1, 2)
        grid.addWidget(self.m_peak_amp[0], 1, 3)

        lay_an.addLayout(grid)
        container.addWidget(card_analysis, 7)

        # 2. Modulation Card
        card_mod = QtWidgets.QFrame()
        card_mod.setProperty("class", "SigmaBigCard")
        lay_mod = QtWidgets.QVBoxLayout(card_mod)
        lay_mod.setContentsMargins(12, 8, 12, 8)
        lay_mod.setSpacing(4)

        t_mod = QtWidgets.QLabel("MODULATION")
        t_mod.setProperty("class", "SectionTitle")
        lay_mod.addWidget(t_mod)

        mod_box = QtWidgets.QFrame()
        mod_box.setProperty("class", "BigModulationBox")
        box_lay = QtWidgets.QVBoxLayout(mod_box)
        box_lay.setContentsMargins(10, 6, 10, 6)
        box_lay.setSpacing(2)

        self.lbl_mod_class = QtWidgets.QLabel("Not analyzed")
        self.lbl_mod_class.setProperty("class", "BigModulationState")
        self.lbl_mod_class.setWordWrap(True)
        box_lay.addWidget(self.lbl_mod_class)

        self.lbl_mod_conf = QtWidgets.QLabel("Confidence: --")
        self.lbl_mod_conf.setProperty("class", "BigModulationConfidence")
        box_lay.addWidget(self.lbl_mod_conf)

        lay_mod.addWidget(mod_box, 1)
        container.addWidget(card_mod, 3)

        res_widget = QtWidgets.QWidget()
        res_widget.setLayout(container)
        return res_widget

    def _create_big_metric_cell(self, label, default_val="--", is_highlight=False):
        cell = QtWidgets.QFrame()
        cell.setProperty("class", "BigMetricCell")
        lay = QtWidgets.QVBoxLayout(cell)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(4)

        lbl = QtWidgets.QLabel(label)
        lbl.setProperty("class", "BigMetricLabel")
        lay.addWidget(lbl)

        val_class = "BigMetricValueHighlight" if is_highlight else "BigMetricValue"
        val = QtWidgets.QLabel(default_val)
        val.setProperty("class", val_class)
        lay.addWidget(val)

        return cell, val

    # =========================================================================
    # 5. Bottom: Big Clean Processing Flow
    # =========================================================================
    def _build_processing_flow(self):
        bar = QtWidgets.QFrame()
        bar.setProperty("class", "BigPipelineBar")
        layout = QtWidgets.QHBoxLayout(bar)
        layout.setContentsMargins(16, 4, 16, 4)
        layout.setSpacing(12)

        lbl_input = QtWidgets.QLabel("1. INPUT ✓")
        lbl_input.setProperty("class", "BigPipelineStepDone")
        layout.addWidget(lbl_input)

        arr1 = QtWidgets.QLabel("→")
        arr1.setProperty("class", "BigPipelineArrow")
        layout.addWidget(arr1)

        lbl_analysis = QtWidgets.QLabel("2. ANALYSIS ✓")
        lbl_analysis.setProperty("class", "BigPipelineStepDone")
        layout.addWidget(lbl_analysis)

        arr2 = QtWidgets.QLabel("→")
        arr2.setProperty("class", "BigPipelineArrow")
        layout.addWidget(arr2)

        lbl_mod = QtWidgets.QLabel("3. MODULATION ✓")
        lbl_mod.setProperty("class", "BigPipelineStepDone")
        layout.addWidget(lbl_mod)

        arr3 = QtWidgets.QLabel("→")
        arr3.setProperty("class", "BigPipelineArrow")
        layout.addWidget(arr3)

        lbl_demod = QtWidgets.QLabel("4. DEMOD ○")
        lbl_demod.setProperty("class", "BigPipelineStepPending")
        layout.addWidget(lbl_demod)

        arr4 = QtWidgets.QLabel("→")
        arr4.setProperty("class", "BigPipelineArrow")
        layout.addWidget(arr4)

        lbl_bits = QtWidgets.QLabel("5. BITS ○")
        lbl_bits.setProperty("class", "BigPipelineStepPending")
        layout.addWidget(lbl_bits)

        layout.addStretch(1)

        legend = QtWidgets.QLabel("✓ completed    ● processing    ○ not available")
        legend.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 13px; font-weight: 600;")
        layout.addWidget(legend)

        return bar

    # =========================================================================
    # Audio Playback Toggle
    # =========================================================================
    def _toggle_audio_playback(self):
        if self.audio_manager.is_playing:
            self.audio_manager.stop()
            self.flowgraph.stop_waves()
            self.btn_play_audio.setText("🔊 Play Audio")
            self.btn_play_audio.setProperty("class", "AudioBtnIdle")
        else:
            # Play original WAV if loaded, or current IQ file
            target = self.original_file if self.original_file.lower().endswith(".wav") else self.current_file
            success = self.audio_manager.play(target, self.samp_rate)
            if success:
                self.flowgraph.start_waves(rewind=True)
                self.btn_play_audio.setText("⏹ Stop Audio")
                self.btn_play_audio.setProperty("class", "AudioBtnPlaying")
            else:
                QtWidgets.QMessageBox.information(
                    self,
                    "Audio Playback",
                    "Could not generate audio playback for the current signal file."
                )

        self.btn_play_audio.style().unpolish(self.btn_play_audio)
        self.btn_play_audio.style().polish(self.btn_play_audio)

    # =========================================================================
    # Displays Update & Event Handlers
    # =========================================================================
    def _update_all_displays(self):
        """Updates UI parameters with real calculated physical properties."""
        m = self.metadata

        # Input Card
        self.lbl_filename.setText(m.filename)
        sr_str = f"{self.samp_rate / 1e6:.2f} MS/s" if self.samp_rate >= 1e6 else f"{self.samp_rate / 1e3:.1f} kS/s"
        cf_str = f"{self.center_freq / 1e6:.3f} MHz" if abs(self.center_freq) >= 1e6 else (f"{self.center_freq / 1e3:.1f} kHz" if abs(self.center_freq) >= 1e3 else f"{self.center_freq:.0f} Hz")
        samples_str = f"{m.num_samples:,}" if m.num_samples > 0 else "--"

        self.badge_format.setText(m.datatype)
        self.badge_samples.setText(f"{samples_str} smp")
        self.badge_rate.setText(f"Rate: {sr_str}")
        self.badge_duration.setText(f"{m.duration_str} ({m.filesize_str})")

        # Results: Signal Analysis
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
            if not self.audio_manager.is_playing:
                self.flowgraph.capture_preview(0.15)

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

        # Reset audio button state and stop waves
        self.audio_manager.stop()
        self.flowgraph.stop_waves()
        self.btn_play_audio.setText("🔊 Play Audio")
        self.btn_play_audio.setProperty("class", "AudioBtnIdle")
        self.btn_play_audio.style().unpolish(self.btn_play_audio)
        self.btn_play_audio.style().polish(self.btn_play_audio)

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
                self.flowgraph.capture_preview(0.15)
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "Signal Load Error", f"Could not load WAV file:\n{e}")
        else:
            # IQ binary file
            self.current_file = path

            # Automatically infer sample rate if known from dataset filename
            fname_lower = os.path.basename(path).lower()
            if "250k" in fname_lower:
                self.samp_rate = 250000
            elif "1m" in fname_lower or "1msps" in fname_lower:
                self.samp_rate = 1000000

            self.flowgraph.set_samp_rate(self.samp_rate)
            self.flowgraph.reload_file(self.current_file, repeat=self.is_looping)
            self.metadata = SignalMetadata(self.current_file, self.samp_rate, self.center_freq)
            self._update_all_displays()
            self.flowgraph.capture_preview(0.15)

    # Aliases for backwards compatibility
    def _load_iq_file(self):
        return self._load_signal_file()

    def _load_wav_file(self):
        return self._load_signal_file()

    def closeEvent(self, event):
        try:
            self.audio_manager.stop()
            self.flowgraph.stop_waves()
            self.flowgraph.stop()
            self.flowgraph.wait()
        except Exception:
            pass
        event.accept()
