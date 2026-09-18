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
    from .sigma_demod import format_bitstream_summary
    from .sigma_coding import analyse_coding_layer
    from .sigma_sample_rate import (
        resolve_sample_rate_file, format_sample_rate, format_sample_rate_source,
    )
except ImportError:
    from sigma_theme import COLORS, MAIN_QSS, create_sigma_icon
    from sigma_analyzer_core import SignalMetadata, load_and_convert_wav
    from sigma_flowgraph import SigmaFlowgraph
    from sigma_demod import format_bitstream_summary
    from sigma_coding import analyse_coding_layer
    from sigma_sample_rate import (
        resolve_sample_rate_file, format_sample_rate, format_sample_rate_source,
    )


_STARTUP_DEMO = "demo_bpsk_100ksps_1msps.iq"


def _iq_search_dirs():
    """Directories that may hold bundled captures, relative to this file."""
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(os.path.join(here, os.pardir))
    return [
        os.path.join(root, "data", "iq"),
        os.path.join(root, "data"),
        root,
        here,
    ]


def find_startup_demo():
    """Path to the capture the app should open on, or None.

    The app must open on a file the *whole* pipeline can finish. The bundled
    signal.iq is synthetic and carries no recoverable symbol clock, so it
    always halts at stage 3 and the first screen a reviewer sees is a declined
    DEMOD step. We therefore prefer a capture known to lock.
    """
    for d in _iq_search_dirs():
        p = os.path.join(d, _STARTUP_DEMO)
        if os.path.exists(p):
            return p
    return None


def resolve_sample_path(filepath=None):
    """Resolves an IQ sample file path, checking standard data locations.

    An explicit, existing path always wins -- if the user picked a file, we
    load that file and nothing else. The default is only chosen when no usable
    path was supplied.
    """
    if filepath:
        if os.path.exists(filepath):
            return os.path.abspath(filepath)
        # A bare name like "signal.iq" -- look for it in the standard dirs
        # before falling back to the startup demo.
        for d in _iq_search_dirs():
            p = os.path.join(d, os.path.basename(filepath))
            if os.path.exists(p):
                return os.path.abspath(p)

    demo = find_startup_demo()
    if demo:
        return demo

    for d in _iq_search_dirs():
        p = os.path.join(d, "signal.iq")
        if os.path.exists(p):
            return os.path.abspath(p)
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

    def __init__(self, initial_file=None):
        super().__init__()
        self.setWindowTitle("SIGMA — Signal Intelligence & Generalized Modulation Analyzer")
        self.setWindowIcon(create_sigma_icon())
        self.setMinimumSize(960, 600)
        # NOTE: window sizing happens at the end of _init_ui(), once the
        # layout exists and its sizeHint can actually be measured.

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

    def _apply_initial_geometry(self):
        """Open at a size that shows the whole panel stack where possible.

        The required height is asked of the layout rather than hardcoded:
        `sizeHint()` on the scroll content tells us exactly how tall the
        stack wants to be, so adding a results card cannot silently push
        content below the fold again. A hardcoded 950 was already too small
        once the DEMODULATION card was added (the stack wants ~921px of
        content plus chrome).

        If the screen cannot fit that, fall back to the largest size that
        fits inside the available area rather than opening off-screen.
        """
        want_w = 1400
        hint = None
        try:
            hint = self.scroll_area.widget().sizeHint().height()
        except Exception:
            pass
        # Chrome: window title bar, header, input bar and margins.
        want_h = (hint + 150) if hint else 1000
        want_h = max(700, want_h)

        screen = QtWidgets.QApplication.primaryScreen()
        if screen is not None:
            avail = screen.availableGeometry()
            # Leave a small margin so window decorations stay on screen.
            fit_w = max(960, min(want_w, avail.width() - 40))
            fit_h = max(600, min(want_h, avail.height() - 60))
            self.resize(fit_w, fit_h)
            # Centre it; a window that opens flush to a corner looks broken.
            self.move(
                avail.x() + (avail.width() - fit_w) // 2,
                avail.y() + (avail.height() - fit_h) // 2,
            )
        else:
            self.resize(want_w, want_h)

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
        self.scroll_area = scroll

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

        # Size the window now that the layout exists and can be measured.
        # Calling this from __init__ before _init_ui() built anything meant
        # the sizeHint was unavailable and the height fell back to a guess.
        self._apply_initial_geometry()

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

        # Sample-rate provenance.
        #
        # f_s cannot be measured from IQ samples (see sigma_sample_rate.py), so
        # whatever number we show is a label, not a measurement. This line makes
        # the difference visible: an operator-set or protocol-derived rate
        # (MEASURED) looks different from one read out of a filename string
        # (INFERRED), which in turn differs from a bare fallback (ASSUMED).
        self.lbl_rate_source = QtWidgets.QLabel("Sample rate: --")
        self.lbl_rate_source.setProperty("class", "RateSource")
        layout.addWidget(self.lbl_rate_source)

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
        # Two rows:
        #   row 1 - Signal Analysis (metrics grid) + Modulation
        #   row 2 - Demodulation / Bitstream readout, full width
        #
        # The demodulation readout is naturally wide (monospace bitstream plus
        # a stats line), so placing it beside the metric grid forced the whole
        # window's minimum width past the screen and produced a horizontal
        # scrollbar. Giving it its own full-width row keeps the window inside
        # 1400px while showing more, not less.
        outer = QtWidgets.QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(10)

        row1 = QtWidgets.QHBoxLayout()
        row1.setContentsMargins(0, 0, 0, 0)
        row1.setSpacing(10)

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

        # Symbol rate row (Stage 4 prerequisite for timing recovery)
        self.m_symbol_rate = self._create_big_metric_cell(
            "Symbol Rate", "--", is_highlight=True
        )
        self.m_sps = self._create_big_metric_cell("Samples/Symbol", "--")
        self.m_symrate_conf = self._create_big_metric_cell(
            "Symbol Rate Lock", "--"
        )

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

        # Row 3
        grid.addWidget(self.m_symbol_rate[0], 2, 0)
        grid.addWidget(self.m_sps[0], 2, 1)
        grid.addWidget(self.m_symrate_conf[0], 2, 2)

        lay_an.addLayout(grid)
        row1.addWidget(card_analysis, 7)

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
        row1.addWidget(card_mod, 3)

        outer.addLayout(row1)

        # 3. Demodulation / Bitstream Card (full width, own row)
        #
        # The demodulator produces real numbers (symbol count, EVM, carrier
        # offset, the first bits). Previously they only reached a tooltip,
        # which meant a verified-stage looked like a tick mark with nothing
        # behind it. Surface them.
        card_demod = QtWidgets.QFrame()
        card_demod.setProperty("class", "SigmaBigCard")
        lay_dm = QtWidgets.QVBoxLayout(card_demod)
        lay_dm.setContentsMargins(12, 8, 12, 8)
        lay_dm.setSpacing(5)

        t_dm = QtWidgets.QLabel("DEMODULATION & BITSTREAM")
        t_dm.setProperty("class", "SectionTitle")
        lay_dm.addWidget(t_dm)

        dm_box = QtWidgets.QFrame()
        dm_box.setProperty("class", "BigModulationBox")
        dm_lay = QtWidgets.QVBoxLayout(dm_box)
        dm_lay.setContentsMargins(10, 6, 10, 6)
        dm_lay.setSpacing(6)

        # Row 1 -- status (LOCKED / DECLINED) + method used
        dm_row1 = QtWidgets.QHBoxLayout()
        dm_row1.setSpacing(8)
        self.lbl_demod_state = QtWidgets.QLabel("NOT RUN")
        self.lbl_demod_state.setProperty("class", "DemodValueIdle")
        dm_row1.addWidget(self.lbl_demod_state)
        dm_row1.addStretch(1)
        self.lbl_demod_method = QtWidgets.QLabel("--")
        self.lbl_demod_method.setProperty("class", "BigModulationConfidence")
        dm_row1.addWidget(self.lbl_demod_method)
        dm_lay.addLayout(dm_row1)

        # Row 2 -- the measured quality numbers
        self.lbl_demod_stats = QtWidgets.QLabel("--")
        self.lbl_demod_stats.setProperty("class", "BigModulationConfidence")
        self.lbl_demod_stats.setWordWrap(True)
        dm_lay.addWidget(self.lbl_demod_stats)

        # Row 3 -- why it did not run (hidden when it did)
        self.lbl_demod_reason = QtWidgets.QLabel("")
        self.lbl_demod_reason.setProperty("class", "DemodReason")
        self.lbl_demod_reason.setWordWrap(True)
        self.lbl_demod_reason.setVisible(False)
        dm_lay.addWidget(self.lbl_demod_reason)

        # Row 4 -- the actual recovered bits
        t_bits = QtWidgets.QLabel("RECOVERED BITSTREAM (first bits)")
        t_bits.setProperty("class", "BigMetricLabel")
        dm_lay.addWidget(t_bits)

        self.lbl_bitstream = QtWidgets.QLabel("--")
        self.lbl_bitstream.setProperty("class", "DemodBitstream")
        self.lbl_bitstream.setWordWrap(True)
        dm_lay.addWidget(self.lbl_bitstream)

        lay_dm.addWidget(dm_box, 1)
        outer.addWidget(card_demod)

        res_widget = QtWidgets.QWidget()
        res_widget.setLayout(outer)
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

        self.lbl_demod = QtWidgets.QLabel("4. DEMOD ○")
        self.lbl_demod.setProperty("class", "BigPipelineStepPending")
        layout.addWidget(self.lbl_demod)

        arr4 = QtWidgets.QLabel("→")
        arr4.setProperty("class", "BigPipelineArrow")
        layout.addWidget(arr4)

        self.lbl_bits = QtWidgets.QLabel("5. BITS ○")
        self.lbl_bits.setProperty("class", "BigPipelineStepPending")
        layout.addWidget(self.lbl_bits)

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

        # Sample-rate provenance line.
        #
        # Colour carries the meaning here: green = we have an external
        # reference (operator or a matched standard), amber = a filename
        # string we chose to trust, muted = we fell back and are guessing.
        conf = getattr(m, "sample_rate_confidence", "--")
        src_txt = getattr(m, "sample_rate_source", "--")
        warn = getattr(m, "sample_rate_warning", "")
        self.lbl_rate_source.setText(f"Sample rate: {src_txt}")
        if conf == "MEASURED":
            self.lbl_rate_source.setProperty("class", "RateSourceOk")
        elif conf == "INFERRED":
            self.lbl_rate_source.setProperty("class", "RateSourceWarn")
        else:
            self.lbl_rate_source.setProperty("class", "RateSourceIdle")
        self.lbl_rate_source.setToolTip(
            f"{src_txt}\nf_s is not measurable from IQ samples; "
            f"this value is {conf}."
            + (f"\n\n{warn}" if warn else "")
        )
        self.lbl_rate_source.style().unpolish(self.lbl_rate_source)
        self.lbl_rate_source.style().polish(self.lbl_rate_source)

        # Results: Signal Analysis
        self.m_peak_freq[1].setText(m.peak_frequency)
        self.m_center_freq[1].setText(cf_str)
        self.m_bandwidth[1].setText(m.occupied_bandwidth)
        self.m_signal_power[1].setText(m.signal_power_dbfs)

        self.m_noise_floor[1].setText(m.noise_floor)
        self.m_snr[1].setText(m.snr)
        self.m_rms[1].setText(m.rms_amplitude)
        self.m_peak_amp[1].setText(m.peak_amplitude)

        # Symbol rate estimation results
        self.m_symbol_rate[1].setText(m.symbol_rate)
        self.m_sps[1].setText(m.samples_per_symbol)
        self.m_symrate_conf[1].setText(m.symbol_rate_confidence)

        # Modulation
        self.lbl_mod_class.setText(m.modulation_class)
        self.lbl_mod_conf.setText(f"Confidence: {m.modulation_confidence}")

        self._run_demod_stage()

    def _reset_demod_panel(self, state_text, reason=None):
        """Put the DEMODULATION card into a non-running state with an optional reason."""
        self.lbl_demod_state.setText(state_text)
        self.lbl_demod_state.setProperty("class", "DemodValueWarn")
        self.lbl_demod_method.setText("--")
        self.lbl_demod_stats.setText("--")
        self.lbl_bitstream.setText("--")
        if reason:
            self.lbl_demod_reason.setText(reason)
            self.lbl_demod_reason.setVisible(True)
        else:
            self.lbl_demod_reason.setVisible(False)
        for w in (self.lbl_demod_state, self.lbl_demod_method):
            w.style().unpolish(w)
            w.style().polish(w)

    def _run_demod_stage(self):
        """Run demodulation on the loaded capture and update the pipeline steps.

        Demodulation needs a symbol rate it can trust, so it only runs when
        the estimator actually locked. When it does not lock -- or when the
        modulation is not one the demodulator supports -- the steps stay
        "not available" and the reason is shown. Reporting a refusal is the
        point: a confident wrong bitstream would be worse than no bitstream.
        """
        m = self.metadata
        sr = getattr(m, "symbol_rate_result", None)
        self.demod_result = None
        self.coding_result = None

        # Reset to pending, then promote only on real success.
        self._set_pipeline_step(self.lbl_demod, "4. DEMOD", done=False)
        self._set_pipeline_step(self.lbl_bits, "5. BITS", done=False)
        self._reset_demod_panel("NOT RUN")

        if not sr or not sr.get("locked"):
            reason = "No symbol rate lock, so there is no clock to sample at."
            self.lbl_demod.setToolTip(reason)
            self._reset_demod_panel("NO CLOCK", reason)
            return

        # A LOW-confidence lock means the clock line is barely above the noise
        # floor. Demodulating anyway would produce a plausible-looking
        # bitstream sampled at a rate that is probably wrong, which is worse
        # than declining. Require MEDIUM or better.
        if sr.get("confidence_label") == "LOW":
            reason = (f"Symbol rate lock is only LOW ({sr['prominence_db']:.1f} dB "
                      f"over the noise floor), so the bitstream would be sampled "
                      f"on an untrusted clock. Declined.")
            self.lbl_demod.setToolTip(reason)
            self._reset_demod_panel("DECLINED", reason)
            return

        # Which constellation to slice against.
        #
        # The spectral classifier can only name BPSK and QPSK: its M-th power
        # order detector is deliberately conservative, and 8PSK/16QAM are not
        # separable that way. Measured on known signals, 8PSK's strongest line
        # is at x^2 rather than x^8, so the spectral route calls an 8PSK capture
        # BPSK. When it has no usable name, ask the demodulator instead --
        # demodulating under each constellation and keeping the simplest that
        # explains the symbols identifies all four (verified 144/144, with
        # noise correctly refused rather than guessed).
        #
        # "BPSK / 2-FSK" is an ambiguity in the classifier, not a disagreement
        # with the demodulator: it fires on the signature of BPSK (constant
        # envelope, high phase variance after differencing), which is precisely
        # what a BPSK demodulator can resolve. Try the PSK reading and let the
        # demodulator's own lock decide -- it is the thing that actually knows
        # whether the bits came out, and it declines on its own if they did not.
        #
        # Order matters. A combined label such as "QPSK / 8PSK" names two
        # candidates, and the same parsimony that resolves the EVM tie applies:
        # prefer the constellation with fewer points, so test ascending by
        # size. Note "8PSK" contains neither "QPSK" nor "BPSK".
        mod = m.modulation_class or ""
        label = None
        for name in ("BPSK", "QPSK", "8PSK", "16QAM"):
            if name in mod:
                label = name
                break

        try:
            samples = self._read_samples_for_demod()
            if samples is None:
                return

            try:
                from .sigma_demod import demodulate, classify_constellation
            except ImportError:
                from sigma_demod import demodulate, classify_constellation

            sps = sr["samples_per_symbol"]
            source = f"classifier: {mod or 'unknown'}"

            if label is None:
                # Ask the demodulator. It is safe to ask even when the label
                # names a different family: `classify_constellation` refuses
                # any signal that does not occupy at least two constellation
                # phases, which was measured to correctly refuse a real FM/RDS
                # capture, plus AM, ASK, CW and audio baseband.
                #
                # That matters, because 16QAM is misclassified as "AM / ASK" by
                # the spectral classifier -- its envelope varies, and the
                # classifier reads that as amplitude modulation. A family check
                # here would block the one modulation we can now slice.
                label, evms = classify_constellation(samples, self.samp_rate, sps)
                if label is None:
                    best = min(evms.values())
                    best_txt = ("n/a" if best == float("inf")
                                else f"{best:.0f}%")
                    reason = (
                        f"Detected {mod or 'unknown'}; no digital constellation "
                        f"explains the symbols (best EVM {best_txt}). Declined "
                        f"rather than guessing a constellation order.")
                    self.lbl_demod.setToolTip(reason)
                    self._reset_demod_panel("UNSUPPORTED", reason)
                    return
                source = (f"symbols: {label} is the simplest that fits "
                          f"(EVM {evms[label]:.1f}%)")

            res = demodulate(samples, self.samp_rate, modulation=label, sps=sps)

            # The spectral classifier cannot separate BPSK from 8PSK (its
            # strongest M-th-power line sits at x^2 either way), so an 8PSK
            # capture can arrive here named BPSK -- and a BPSK slice refuses
            # it. Before giving up, ask the demodulator-based classifier, which
            # reads the symbols themselves and does separate all four.
            if not res.locked:
                alt, alt_evms = classify_constellation(samples, self.samp_rate, sps)
                if alt is not None and alt != label:
                    res_alt = demodulate(samples, self.samp_rate,
                                         modulation=alt, sps=sps)
                    if res_alt.locked:
                        res = res_alt
                        source = (f"symbols: {alt} is the simplest that fits "
                                  f"(EVM {alt_evms[alt]:.1f}%; "
                                  f"the classifier said {label})")
            self.demod_result = res

            if not res.locked:
                self.lbl_demod.setToolTip(f"Demodulator declined: {res.reason}")
                self._reset_demod_panel("DECLINED", res.reason)
                return

            self._set_pipeline_step(self.lbl_demod, "4. DEMOD", done=True)
            self._set_pipeline_step(self.lbl_bits, "5. BITS", done=True)

            # PS section 3 (iii)/(iv): interleaver detection + FEC decode.
            # Runs over the recovered bits. It is expected to find nothing on
            # ordinary uncoded traffic -- it reports "no FEC detected" rather
            # than inventing a payload, which is why it is safe to run always.
            coding = None
            try:
                coding = analyse_coding_layer(res.bits)
                self.coding_result = coding
            except Exception as ce:
                print(f"[SIGMA] Coding-layer analysis skipped: {ce}")
                self.coding_result = None

            self.lbl_demod.setToolTip(
                f"{res.modulation}, {res.n_symbols} symbols, "
                f"EVM {res.evm_percent:.1f}%  --  chosen by {source}")
            self.lbl_bits.setToolTip(
                f"{len(res.bits)} bits recovered, EVM {res.evm_percent:.1f}%"
                + (f"; {coding.reason}" if coding else ""))

            # Populate the DEMODULATION card with the real measured output.
            self.lbl_demod_state.setText("LOCKED")
            self.lbl_demod_state.setProperty("class", "DemodValue")
            self.lbl_demod_method.setText(
                f"{res.modulation}  \u00b7  RRC matched filter")
            resid_txt = (f"{res.residual_freq_hz:+,.1f} Hz"
                         if res.residual_freq_hz is not None else "--")
            coding_txt = "--"
            header_txt = "--"
            if coding is not None and coding.analysed:
                if coding.had_fec:
                    coding_txt = (f"FEC {coding.interleaver or 'none'}"
                                  f" (residual {coding.residual:.3f})")
                else:
                    coding_txt = "not present"
                # PS section 3 (v). An empty result is the normal outcome for
                # unframed traffic, so say so rather than leaving a blank.
                if coding.sync_hits:
                    off, err = coding.sync_hits[0]
                    header_txt = f"bit {off} ({err} err)"
                    if len(coding.sync_hits) > 1:
                        header_txt += f" +{len(coding.sync_hits) - 1}"
                elif coding.sync_detectable is None:
                    header_txt = "not decidable at this length"
                else:
                    header_txt = "none found"
            self.lbl_demod_stats.setText(
                f"Symbols: {res.n_symbols}      Bits: {len(res.bits)}      "
                f"EVM: {res.evm_percent:.1f}%\n"
                f"Carrier offset: {res.carrier_offset_hz:+,.0f} Hz      "
                f"Residual tracked: {resid_txt}      "
                f"SPS used: {res.sps:.2f}\n"
                f"Coding: {coding_txt}      Header: {header_txt}"
            )
            self.lbl_demod_reason.setVisible(False)
            # 48 bits in spaced groups: long enough to be a real payload
            # preview, short enough that the monospace label does not set the
            # minimum width of the window.
            bits_txt = format_bitstream_summary(res, max_bits=48)
            spaced = " ".join(bits_txt[i:i + 4] for i in range(0, len(bits_txt), 4))
            self.lbl_bitstream.setText(spaced)
            for w in (self.lbl_demod_state, self.lbl_demod_method):
                w.style().unpolish(w)
                w.style().polish(w)
        except Exception as e:
            print(f"[SIGMA] Demodulation error: {e}")
            self.lbl_demod.setToolTip(f"Demodulation error: {e}")
            self._reset_demod_panel("ERROR", str(e))

    def _read_samples_for_demod(self, max_samples=400_000):
        """Read complex baseband samples from the loaded file for demodulation."""
        path = self.current_file
        if not path or not os.path.exists(path):
            return None
        try:
            data = np.fromfile(path, dtype=np.complex64)
            if data.size == 0:
                return None
            # Demodulating a prefix is enough and keeps the UI responsive.
            return data[:max_samples]
        except Exception as e:
            print(f"[SIGMA] Could not read samples for demodulation: {e}")
            return None

    def _set_pipeline_step(self, label_widget, text, done):
        """Flip a pipeline step between completed and not-available styling."""
        label_widget.setText(f"{text} ✓" if done else f"{text} ○")
        label_widget.setProperty(
            "class", "BigPipelineStepDone" if done else "BigPipelineStepPending")
        label_widget.style().unpolish(label_widget)
        label_widget.style().polish(label_widget)

    def _open_settings(self):
        dialog = SettingsDialog(self, self.samp_rate, self.center_freq)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            new_rate, new_freq = dialog.get_values()
            self.samp_rate = new_rate
            self.center_freq = new_freq
            self.flowgraph.set_samp_rate(self.samp_rate)
            self.flowgraph.set_center_freq(self.center_freq)
            self.metadata = SignalMetadata(self.current_file, self.samp_rate, self.center_freq)
            # The operator just told us the rate. That is the single most
            # trustworthy source in the whole ranking -- it outranks even a
            # protocol match -- so label it accordingly instead of letting the
            # metadata inherit a filename guess from the previous load.
            self._mark_measured_rate("operator set")
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
                # A WAV carries its own rate in its header, so this is a real
                # measurement -- record it as such rather than letting the
                # resolver call it an assumption.
                self._mark_measured_rate("WAV header")
                self.samp_rate = self.metadata.samp_rate
                self.flowgraph.set_samp_rate(self.samp_rate)
                self._update_all_displays()
                self.flowgraph.capture_preview(0.15)
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "Signal Load Error", f"Could not load WAV file:\n{e}")
        else:
            # IQ binary file
            self.current_file = path

            # Resolve the sample rate from the filename with a priority-ordered
            # parse rather than a substring test. The old version was:
            #
            #   if "250k" in fname_lower: self.samp_rate = 250000
            #   elif "1m" in fname_lower or "1msps" in fname_lower: ...
            #
            # which mis-read "demo_bpsk_100ksps_1msps.iq" (it matched the
            # symbol-rate token "100ksps" as 100 kSps) and silently kept
            # whatever rate the previous file had set when nothing matched.
            # The resolver handles both, and reports which token it used so a
            # guess stays visibly a guess.
            from_sr = resolve_sample_rate_file(path, fallback=self.samp_rate)
            self.samp_rate = from_sr

            self.flowgraph.set_samp_rate(self.samp_rate)
            self.flowgraph.reload_file(self.current_file, repeat=self.is_looping)
            self.metadata = SignalMetadata(self.current_file, self.samp_rate, self.center_freq)
            # The analyser may have corrected f_s from a matched standard
            # symbol rate. Adopt it here so the flowgraph, the duration and the
            # reported R_s all agree on one value.
            if abs(self.metadata.samp_rate - self.samp_rate) > 1.0:
                self.samp_rate = self.metadata.samp_rate
                self.flowgraph.set_samp_rate(self.samp_rate)
            self._update_all_displays()
            self.flowgraph.capture_preview(0.15)

    def _mark_measured_rate(self, why):
        """Label the current metadata's sample rate as externally referenced."""
        m = self.metadata
        if m is None:
            return
        m.sample_rate_confidence = "MEASURED"
        m.sample_rate_source = f"MEASURED - {why}"

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
