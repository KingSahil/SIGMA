"""
SIGMA - Signal Intelligence & Generalized Modulation Analyzer
Clean, Simple, User-Friendly UI
SIH 2026 Engineering Prototype
"""

import os
import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt

from sigma_theme import COLORS, MAIN_QSS
from sigma_analyzer_core import SignalMetadata
from sigma_flowgraph import SigmaFlowgraph


class SettingsDialog(QtWidgets.QDialog):
    """Clean, minimal settings dialog for RF configuration."""

    def __init__(self, parent=None, samp_rate=1000000, center_freq=0.0):
        super().__init__(parent)
        self.setWindowTitle("SIGMA — Settings")
        self.setMinimumWidth(360)
        self.setStyleSheet(MAIN_QSS)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QtWidgets.QLabel("RF HARDWARE & DSP SETTINGS")
        title.setProperty("class", "SectionTitle")
        layout.addWidget(title)

        form = QtWidgets.QFormLayout()
        form.setSpacing(12)

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
    Designed for maximum clarity, simplicity, and ease of use.
    """

    def __init__(self, initial_file="signal.iq"):
        super().__init__()
        self.setWindowTitle("SIGMA — Signal Intelligence & Generalized Modulation Analyzer")
        self.resize(1420, 940)

        # Application state
        self.current_file = initial_file if os.path.exists(initial_file) else "signal.iq"
        self.samp_rate = 1000000
        self.center_freq = 0.0
        self.is_running = True
        self.is_looping = True

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
        central = QtWidgets.QWidget(self)
        central.setObjectName("CentralWidget")
        self.setCentralWidget(central)

        main_layout = QtWidgets.QVBoxLayout(central)
        main_layout.setContentsMargins(18, 14, 18, 14)
        main_layout.setSpacing(12)

        # 1. Header Bar
        main_layout.addWidget(self._build_header())

        # 2. Section 1: Input Signal
        main_layout.addWidget(self._build_input_section())

        # 3. Section 2: Signal Visualization (3 Cards)
        main_layout.addWidget(self._build_visualizations_section(), 1)

        # 4. Section 3: Results (Signal Analysis & Modulation)
        main_layout.addWidget(self._build_results_section())

        # 5. Bottom: Compact Processing Flow
        main_layout.addWidget(self._build_processing_flow())

    # =========================================================================
    # Header Section
    # =========================================================================
    def _build_header(self):
        header = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 4)
        layout.setSpacing(12)

        # Left: Branding
        brand_box = QtWidgets.QVBoxLayout()
        brand_box.setSpacing(2)

        title = QtWidgets.QLabel("SIGMA")
        title.setProperty("class", "AppTitle")
        brand_box.addWidget(title)

        subtitle = QtWidgets.QLabel("Signal Intelligence & Generalized Modulation Analyzer")
        subtitle.setProperty("class", "AppSubtitle")
        brand_box.addWidget(subtitle)

        layout.addLayout(brand_box)
        layout.addStretch(1)

        # Right: Status and Settings
        ctrl_box = QtWidgets.QHBoxLayout()
        ctrl_box.setSpacing(12)

        self.status_pill = QtWidgets.QLabel("● Analyzing")
        self.status_pill.setProperty("class", "StatusAnalyzing")
        ctrl_box.addWidget(self.status_pill)

        self.btn_settings = QtWidgets.QPushButton("⚙ Settings")
        self.btn_settings.clicked.connect(self._open_settings)
        ctrl_box.addWidget(self.btn_settings)

        layout.addLayout(ctrl_box)
        return header

    # =========================================================================
    # Section 1: Input Signal
    # =========================================================================
    def _build_input_section(self):
        card = QtWidgets.QFrame()
        card.setProperty("class", "SigmaCard")
        layout = QtWidgets.QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # Section Header
        sec_title = QtWidgets.QLabel("INPUT SIGNAL")
        sec_title.setProperty("class", "SectionTitle")
        layout.addWidget(sec_title)

        # Content Row
        row = QtWidgets.QHBoxLayout()
        row.setSpacing(16)

        # File & Details
        file_info_box = QtWidgets.QVBoxLayout()
        file_info_box.setSpacing(4)

        self.lbl_filename = QtWidgets.QLabel("signal.iq")
        self.lbl_filename.setProperty("class", "FileName")
        file_info_box.addWidget(self.lbl_filename)

        # Summary line
        self.lbl_file_details = QtWidgets.QLabel("Format: Complex Float32  •  Samples: 50,000  •  Sample Rate: 1 MS/s  •  Duration: 50.00 ms")
        self.lbl_file_details.setProperty("class", "FileDetailText")
        file_info_box.addWidget(self.lbl_file_details)

        row.addLayout(file_info_box, 1)

        # Action Buttons
        btn_box = QtWidgets.QHBoxLayout()
        btn_box.setSpacing(10)

        self.btn_load_iq = QtWidgets.QPushButton("📂 Load IQ File")
        self.btn_load_iq.setProperty("class", "PrimaryBtn")
        self.btn_load_iq.clicked.connect(self._load_iq_file)
        btn_box.addWidget(self.btn_load_iq)

        self.btn_load_wav = QtWidgets.QPushButton("🎵 Load WAV")
        self.btn_load_wav.clicked.connect(self._load_wav_file)
        btn_box.addWidget(self.btn_load_wav)

        row.addLayout(btn_box)
        layout.addLayout(row)

        return card

    # =========================================================================
    # Section 2: Signal Visualization (3 Clean Cards)
    # =========================================================================
    def _build_visualizations_section(self):
        splitter = QtWidgets.QSplitter(Qt.Vertical)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(8)

        # Upper row: Time Domain & Frequency Spectrum
        upper_widget = QtWidgets.QWidget()
        upper_layout = QtWidgets.QHBoxLayout(upper_widget)
        upper_layout.setContentsMargins(0, 0, 0, 0)
        upper_layout.setSpacing(12)

        # Card 1: Time Domain
        card_time = QtWidgets.QFrame()
        card_time.setProperty("class", "SigmaCard")
        lay_time = QtWidgets.QVBoxLayout(card_time)
        lay_time.setContentsMargins(12, 10, 12, 10)
        lay_time.setSpacing(6)

        header_time = QtWidgets.QHBoxLayout()
        t_time = QtWidgets.QLabel("TIME DOMAIN")
        t_time.setProperty("class", "SectionTitle")
        header_time.addWidget(t_time)
        header_time.addStretch(1)

        legend_time = QtWidgets.QLabel("● I (Cyan)   ● Q (Magenta)")
        legend_time.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 10px; font-weight: 600;")
        header_time.addWidget(legend_time)
        lay_time.addLayout(header_time)

        lay_time.addWidget(self.flowgraph.time_sink_widget, 1)
        upper_layout.addWidget(card_time, 1)

        # Card 2: Frequency Spectrum
        card_freq = QtWidgets.QFrame()
        card_freq.setProperty("class", "SigmaCard")
        lay_freq = QtWidgets.QVBoxLayout(card_freq)
        lay_freq.setContentsMargins(12, 10, 12, 10)
        lay_freq.setSpacing(6)

        header_freq = QtWidgets.QHBoxLayout()
        t_freq = QtWidgets.QLabel("FREQUENCY SPECTRUM")
        t_freq.setProperty("class", "SectionTitle")
        header_freq.addWidget(t_freq)
        header_freq.addStretch(1)

        info_freq = QtWidgets.QLabel("FFT 1024  •  dB Gain")
        info_freq.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 10px;")
        header_freq.addWidget(info_freq)
        lay_freq.addLayout(header_freq)

        lay_freq.addWidget(self.flowgraph.freq_sink_widget, 1)
        upper_layout.addWidget(card_freq, 1)

        splitter.addWidget(upper_widget)

        # Card 3: Constellation
        card_const = QtWidgets.QFrame()
        card_const.setProperty("class", "SigmaCard")
        lay_const = QtWidgets.QVBoxLayout(card_const)
        lay_const.setContentsMargins(12, 10, 12, 10)
        lay_const.setSpacing(6)

        header_const = QtWidgets.QHBoxLayout()
        t_const = QtWidgets.QLabel("CONSTELLATION")
        t_const.setProperty("class", "SectionTitle")
        header_const.addWidget(t_const)
        header_const.addStretch(1)

        info_const = QtWidgets.QLabel("In-Phase (I) vs Quadrature (Q)")
        info_const.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 10px;")
        header_const.addWidget(info_const)
        lay_const.addLayout(header_const)

        lay_const.addWidget(self.flowgraph.const_sink_widget, 1)
        splitter.addWidget(card_const)

        # Proportions: 55% upper, 45% lower
        splitter.setSizes([460, 360])

        return splitter

    # =========================================================================
    # Section 3: Results (Signal Analysis & Modulation)
    # =========================================================================
    def _build_results_section(self):
        container = QtWidgets.QHBoxLayout()
        container.setSpacing(12)

        # 1. Signal Analysis Card
        card_analysis = QtWidgets.QFrame()
        card_analysis.setProperty("class", "SigmaCard")
        lay_an = QtWidgets.QVBoxLayout(card_analysis)
        lay_an.setContentsMargins(16, 12, 16, 12)
        lay_an.setSpacing(10)

        t_analysis = QtWidgets.QLabel("SIGNAL ANALYSIS")
        t_analysis.setProperty("class", "SectionTitle")
        lay_an.addWidget(t_analysis)

        # Parameter Metrics Grid
        grid = QtWidgets.QGridLayout()
        grid.setSpacing(8)

        self.m_peak_freq = self._create_metric_cell("Peak Frequency", "--", is_highlight=True)
        self.m_center_freq = self._create_metric_cell("Center Frequency", "--")
        self.m_bandwidth = self._create_metric_cell("Bandwidth", "--")
        self.m_signal_power = self._create_metric_cell("Signal Power", "--")

        self.m_noise_floor = self._create_metric_cell("Noise Floor", "--")
        self.m_snr = self._create_metric_cell("SNR", "--")
        self.m_rms = self._create_metric_cell("RMS Amplitude", "--")
        self.m_peak_amp = self._create_metric_cell("Peak Amplitude", "--")

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

        # 2. Modulation Result Card
        card_mod = QtWidgets.QFrame()
        card_mod.setProperty("class", "SigmaCard")
        lay_mod = QtWidgets.QVBoxLayout(card_mod)
        lay_mod.setContentsMargins(16, 12, 16, 12)
        lay_mod.setSpacing(10)

        t_mod = QtWidgets.QLabel("MODULATION")
        t_mod.setProperty("class", "SectionTitle")
        lay_mod.addWidget(t_mod)

        # Clean modulation display box
        mod_box = QtWidgets.QFrame()
        mod_box.setProperty("class", "ModulationBox")
        box_lay = QtWidgets.QVBoxLayout(mod_box)
        box_lay.setContentsMargins(12, 10, 12, 10)
        box_lay.setSpacing(6)

        self.lbl_mod_class = QtWidgets.QLabel("Not analyzed")
        self.lbl_mod_class.setProperty("class", "ModulationState")
        box_lay.addWidget(self.lbl_mod_class)

        self.lbl_mod_conf = QtWidgets.QLabel("Confidence: --")
        self.lbl_mod_conf.setProperty("class", "ModulationConfidence")
        box_lay.addWidget(self.lbl_mod_conf)

        lay_mod.addWidget(mod_box, 1)
        container.addWidget(card_mod, 3)

        res_widget = QtWidgets.QWidget()
        res_widget.setLayout(container)
        return res_widget

    def _create_metric_cell(self, label, default_val="--", is_highlight=False):
        cell = QtWidgets.QFrame()
        cell.setProperty("class", "MetricCell")
        lay = QtWidgets.QVBoxLayout(cell)
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(2)

        lbl = QtWidgets.QLabel(label)
        lbl.setProperty("class", "MetricLabel")
        lay.addWidget(lbl)

        val_class = "MetricValueHighlight" if is_highlight else "MetricValue"
        val = QtWidgets.QLabel(default_val)
        val.setProperty("class", val_class)
        lay.addWidget(val)

        return cell, val

    # =========================================================================
    # Bottom: Compact Processing Flow
    # =========================================================================
    def _build_processing_flow(self):
        bar = QtWidgets.QFrame()
        bar.setStyleSheet(f"background-color: {COLORS['bg_card']}; border: 1px solid {COLORS['border']}; border-radius: 4px; padding: 4px 12px;")
        layout = QtWidgets.QHBoxLayout(bar)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(8)

        lbl_input = QtWidgets.QLabel("INPUT ✓")
        lbl_input.setProperty("class", "PipelineStepDone")
        layout.addWidget(lbl_input)

        arr1 = QtWidgets.QLabel("→")
        arr1.setProperty("class", "PipelineArrow")
        layout.addWidget(arr1)

        lbl_analysis = QtWidgets.QLabel("ANALYSIS ✓")
        lbl_analysis.setProperty("class", "PipelineStepDone")
        layout.addWidget(lbl_analysis)

        arr2 = QtWidgets.QLabel("→")
        arr2.setProperty("class", "PipelineArrow")
        layout.addWidget(arr2)

        lbl_mod = QtWidgets.QLabel("MODULATION ○")
        lbl_mod.setProperty("class", "PipelineStepPending")
        layout.addWidget(lbl_mod)

        arr3 = QtWidgets.QLabel("→")
        arr3.setProperty("class", "PipelineArrow")
        layout.addWidget(arr3)

        lbl_demod = QtWidgets.QLabel("DEMOD ○")
        lbl_demod.setProperty("class", "PipelineStepPending")
        layout.addWidget(lbl_demod)

        arr4 = QtWidgets.QLabel("→")
        arr4.setProperty("class", "PipelineArrow")
        layout.addWidget(arr4)

        lbl_bits = QtWidgets.QLabel("BITS ○")
        lbl_bits.setProperty("class", "PipelineStepPending")
        layout.addWidget(lbl_bits)

        layout.addStretch(1)

        legend = QtWidgets.QLabel("✓ completed   ● processing   ○ not available")
        legend.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        layout.addWidget(legend)

        return bar

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
        self.lbl_file_details.setText(
            f"Format: {m.datatype}  •  Samples: {samples_str}  •  Sample Rate: {sr_str}  •  Duration: {m.duration_str} ({m.filesize_str})"
        )

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

    def _load_iq_file(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select Raw Complex IQ File",
            os.getcwd(),
            "IQ Binary Files (*.iq *.bin *.raw *.dat);;All Files (*.*)"
        )
        if path and os.path.exists(path):
            self.current_file = path
            self.flowgraph.reload_file(self.current_file, repeat=self.is_looping)
            self.metadata = SignalMetadata(self.current_file, self.samp_rate, self.center_freq)
            self._update_all_displays()

    def _load_wav_file(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select RF Recording (WAV format)",
            os.getcwd(),
            "WAV Audio Files (*.wav);;All Files (*.*)"
        )
        if path:
            QtWidgets.QMessageBox.information(
                self,
                "WAV Audio Demuxer",
                f"Selected WAV file:\n{os.path.basename(path)}\n\n"
                "In this prototype, raw complex float32 (.iq) files are directly streamed into the GNU Radio core."
            )

    def closeEvent(self, event):
        try:
            self.flowgraph.stop()
            self.flowgraph.wait()
        except Exception:
            pass
        event.accept()
