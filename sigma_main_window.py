"""
SIGMA - Signal Intelligence & Generalized Modulation Analyzer
Main Application Window (PyQt5)
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
    """Settings dialog for RF configuration."""

    def __init__(self, parent=None, samp_rate=1000000, center_freq=0.0):
        super().__init__(parent)
        self.setWindowTitle("SIGMA - System Configuration")
        self.setMinimumWidth(380)
        self.setStyleSheet(MAIN_QSS)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(18, 18, 18, 18)

        title = QtWidgets.QLabel("RF HARDWARE & DSP SETTINGS")
        title.setProperty("class", "PanelHeader")
        layout.addWidget(title)

        form = QtWidgets.QFormLayout()
        form.setSpacing(10)

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
    """Main desktop interface for the SIGMA system."""

    def __init__(self, initial_file="signal.iq"):
        super().__init__()
        self.setWindowTitle("SIGMA — Signal Intelligence & Generalized Modulation Analyzer")
        self.resize(1440, 920)

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

        # Set stylesheet
        self.setStyleSheet(MAIN_QSS)

        # Build UI
        self._init_ui()
        self._update_all_displays()

        # Start GNU Radio flowgraph
        self.flowgraph.start()
        self.flowgraph.flowgraph_started.set()

    def _init_ui(self):
        central = QtWidgets.QWidget(self)
        central.setObjectName("CentralWidget")
        self.setCentralWidget(central)

        main_layout = QtWidgets.QVBoxLayout(central)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(10)

        # 1. Header Bar
        main_layout.addWidget(self._build_header())

        # 2. Top Info Row (Input Panel + Signal Overview)
        main_layout.addLayout(self._build_top_row())

        # 3. Main Visualizers (Splitter: Graphs Left & Right)
        graphs_splitter = QtWidgets.QSplitter(Qt.Vertical)
        graphs_splitter.setChildrenCollapsible(False)

        # Middle: Time Domain & Frequency Spectrum
        mid_row = QtWidgets.QHBoxLayout()
        mid_row.setSpacing(10)
        mid_row.addWidget(self._build_time_domain_panel(), 1)
        mid_row.addWidget(self._build_freq_panel(), 1)
        mid_widget = QtWidgets.QWidget()
        mid_widget.setLayout(mid_row)
        graphs_splitter.addWidget(mid_widget)

        # Lower: Constellation & Signal Analysis
        low_row = QtWidgets.QHBoxLayout()
        low_row.setSpacing(10)
        low_row.addWidget(self._build_constellation_panel(), 1)
        low_row.addWidget(self._build_analysis_panel(), 1)
        low_widget = QtWidgets.QWidget()
        low_widget.setLayout(low_row)
        graphs_splitter.addWidget(low_widget)

        main_layout.addWidget(graphs_splitter, 1)

        # 4. Bottom Processing Pipeline
        main_layout.addWidget(self._build_pipeline_bar())

    # =========================================================================
    # Header Section
    # =========================================================================
    def _build_header(self):
        header_frame = QtWidgets.QFrame()
        header_frame.setProperty("class", "SigmaPanel")
        layout = QtWidgets.QHBoxLayout(header_frame)
        layout.setContentsMargins(14, 8, 14, 8)

        # Project Branding
        brand_layout = QtWidgets.QVBoxLayout()
        brand_layout.setSpacing(2)

        title_label = QtWidgets.QLabel("SIGMA")
        title_label.setProperty("class", "HeaderTitle")
        brand_layout.addWidget(title_label)

        sub_label = QtWidgets.QLabel("Signal Intelligence & Generalized Modulation Analyzer")
        sub_label.setProperty("class", "HeaderSubtitle")
        brand_layout.addWidget(sub_label)

        layout.addLayout(brand_layout)
        layout.addStretch(1)

        # Controls & Status
        ctrl_layout = QtWidgets.QHBoxLayout()
        ctrl_layout.setSpacing(10)

        # Status indicator
        self.status_pill = QtWidgets.QLabel("● SYSTEM ONLINE")
        self.status_pill.setProperty("class", "StatusPillOnline")
        ctrl_layout.addWidget(self.status_pill)

        # Run / Stop Toggle Button
        self.run_stop_btn = QtWidgets.QPushButton("⏹ Stop DSP")
        self.run_stop_btn.setProperty("class", "PrimaryButton")
        self.run_stop_btn.clicked.connect(self._toggle_run_stop)
        ctrl_layout.addWidget(self.run_stop_btn)

        # Continuous Loop Toggle
        self.loop_btn = QtWidgets.QPushButton("🔁 Loop: ON")
        self.loop_btn.clicked.connect(self._toggle_loop)
        ctrl_layout.addWidget(self.loop_btn)

        # Settings Button
        self.settings_btn = QtWidgets.QPushButton("⚙ Settings")
        self.settings_btn.clicked.connect(self._open_settings)
        ctrl_layout.addWidget(self.settings_btn)

        layout.addLayout(ctrl_layout)
        return header_frame

    # =========================================================================
    # Top Information Row (Input Panel & Signal Overview)
    # =========================================================================
    def _build_top_row(self):
        layout = QtWidgets.QHBoxLayout()
        layout.setSpacing(10)

        # 1. File Input Panel
        input_frame = QtWidgets.QFrame()
        input_frame.setProperty("class", "SigmaPanel")
        in_layout = QtWidgets.QVBoxLayout(input_frame)
        in_layout.setContentsMargins(12, 10, 12, 10)
        in_layout.setSpacing(8)

        in_title = QtWidgets.QLabel("INPUT SOURCE")
        in_title.setProperty("class", "PanelHeader")
        in_layout.addWidget(in_title)

        # Grid of input parameters
        grid = QtWidgets.QGridLayout()
        grid.setSpacing(6)

        grid.addWidget(self._make_label("File:", "CardLabel"), 0, 0)
        self.lbl_in_file = self._make_label("--", "CardValueAccent")
        grid.addWidget(self.lbl_in_file, 0, 1)

        grid.addWidget(self._make_label("Format:", "CardLabel"), 1, 0)
        self.lbl_in_format = self._make_label("Raw IQ Binary", "CardValue")
        grid.addWidget(self.lbl_in_format, 1, 1)

        grid.addWidget(self._make_label("Datatype:", "CardLabel"), 2, 0)
        self.lbl_in_type = self._make_label("Complex Float32", "CardValue")
        grid.addWidget(self.lbl_in_type, 2, 1)

        grid.addWidget(self._make_label("Samples:", "CardLabel"), 0, 2)
        self.lbl_in_samples = self._make_label("--", "CardValue")
        grid.addWidget(self.lbl_in_samples, 0, 3)

        grid.addWidget(self._make_label("Duration:", "CardLabel"), 1, 2)
        self.lbl_in_duration = self._make_label("--", "CardValue")
        grid.addWidget(self.lbl_in_duration, 1, 3)

        grid.addWidget(self._make_label("File Size:", "CardLabel"), 2, 2)
        self.lbl_in_size = self._make_label("--", "CardValue")
        grid.addWidget(self.lbl_in_size, 2, 3)

        in_layout.addLayout(grid)

        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.setSpacing(8)

        self.btn_load_iq = QtWidgets.QPushButton("📂 Load IQ File")
        self.btn_load_iq.setProperty("class", "PrimaryButton")
        self.btn_load_iq.clicked.connect(self._load_iq_file)
        btn_layout.addWidget(self.btn_load_iq)

        self.btn_load_wav = QtWidgets.QPushButton("🎵 Load WAV File")
        self.btn_load_wav.clicked.connect(self._load_wav_file)
        btn_layout.addWidget(self.btn_load_wav)

        self.btn_reset = QtWidgets.QPushButton("🔄 Reset")
        self.btn_reset.clicked.connect(self._reset_file)
        btn_layout.addWidget(self.btn_reset)

        in_layout.addLayout(btn_layout)
        layout.addWidget(input_frame, 4)

        # 2. Signal Overview (Compact Metric Cards)
        overview_frame = QtWidgets.QFrame()
        overview_frame.setProperty("class", "SigmaPanel")
        over_layout = QtWidgets.QVBoxLayout(overview_frame)
        over_layout.setContentsMargins(12, 10, 12, 10)
        over_layout.setSpacing(8)

        over_title = QtWidgets.QLabel("SIGNAL OVERVIEW")
        over_title.setProperty("class", "PanelHeader")
        over_layout.addWidget(over_title)

        cards_grid = QtWidgets.QGridLayout()
        cards_grid.setSpacing(6)

        self.card_center_freq = self._create_metric_card("Center Frequency", "--")
        self.card_samp_rate = self._create_metric_card("Sample Rate", "--", is_accent=True)
        self.card_bandwidth = self._create_metric_card("Bandwidth", "--")
        self.card_signal_power = self._create_metric_card("Signal Power", "--")

        self.card_noise_floor = self._create_metric_card("Noise Floor", "--")
        self.card_snr = self._create_metric_card("SNR", "--")
        self.card_peak_freq = self._create_metric_card("Peak Frequency", "--")
        self.card_duration = self._create_metric_card("Duration", "--")

        cards_grid.addWidget(self.card_center_freq[0], 0, 0)
        cards_grid.addWidget(self.card_samp_rate[0], 0, 1)
        cards_grid.addWidget(self.card_bandwidth[0], 0, 2)
        cards_grid.addWidget(self.card_signal_power[0], 0, 3)

        cards_grid.addWidget(self.card_noise_floor[0], 1, 0)
        cards_grid.addWidget(self.card_snr[0], 1, 1)
        cards_grid.addWidget(self.card_peak_freq[0], 1, 2)
        cards_grid.addWidget(self.card_duration[0], 1, 3)

        over_layout.addLayout(cards_grid)
        layout.addWidget(overview_frame, 6)

        return layout

    def _create_metric_card(self, title, default_val="--", is_accent=False):
        frame = QtWidgets.QFrame()
        frame.setProperty("class", "SigmaCard")
        lay = QtWidgets.QVBoxLayout(frame)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setSpacing(2)

        lbl_title = QtWidgets.QLabel(title)
        lbl_title.setProperty("class", "CardLabel")
        lay.addWidget(lbl_title)

        val_class = "CardValueAccent" if is_accent else "CardValue"
        lbl_val = QtWidgets.QLabel(default_val)
        lbl_val.setProperty("class", val_class)
        lay.addWidget(lbl_val)

        return frame, lbl_val

    # =========================================================================
    # Middle Visualizers (Time Domain & Frequency Spectrum)
    # =========================================================================
    def _build_time_domain_panel(self):
        panel = QtWidgets.QFrame()
        panel.setProperty("class", "SigmaPanel")
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        header_lay = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("TIME DOMAIN (RAW I / Q)")
        title.setProperty("class", "PanelHeader")
        header_lay.addWidget(title)

        info = QtWidgets.QLabel("● In-Phase (I): Cyan  |  ● Quadrature (Q): Magenta")
        info.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 10px;")
        header_lay.addStretch(1)
        header_lay.addWidget(info)
        layout.addLayout(header_lay)

        # Embedded GNU Radio Time Sink Widget
        layout.addWidget(self.flowgraph.time_sink_widget, 1)
        return panel

    def _build_freq_panel(self):
        panel = QtWidgets.QFrame()
        panel.setProperty("class", "SigmaPanel")
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        header_lay = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("FREQUENCY SPECTRUM / PSD")
        title.setProperty("class", "PanelHeader")
        header_lay.addWidget(title)

        info = QtWidgets.QLabel("FFT: 1024-pt Blackman-Harris  |  Unit: Relative Gain (dB)")
        info.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 10px;")
        header_lay.addStretch(1)
        header_lay.addWidget(info)
        layout.addLayout(header_lay)

        # Embedded GNU Radio Frequency Sink Widget
        layout.addWidget(self.flowgraph.freq_sink_widget, 1)
        return panel

    # =========================================================================
    # Lower Visualizers (Constellation & Signal Analysis)
    # =========================================================================
    def _build_constellation_panel(self):
        panel = QtWidgets.QFrame()
        panel.setProperty("class", "SigmaPanel")
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        header_lay = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("CONSTELLATION DIAGRAM")
        title.setProperty("class", "PanelHeader")
        header_lay.addWidget(title)

        info = QtWidgets.QLabel("In-Phase (I) vs Quadrature (Q)  |  Size: 1024")
        info.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 10px;")
        header_lay.addStretch(1)
        header_lay.addWidget(info)
        layout.addLayout(header_lay)

        # Embedded GNU Radio Constellation Sink Widget
        layout.addWidget(self.flowgraph.const_sink_widget, 1)
        return panel

    def _build_analysis_panel(self):
        panel = QtWidgets.QFrame()
        panel.setProperty("class", "SigmaPanel")
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        # Subpanel 1: Signal Parameters
        title1 = QtWidgets.QLabel("AUTOMATIC SIGNAL PARAMETERS")
        title1.setProperty("class", "PanelHeader")
        layout.addWidget(title1)

        param_grid = QtWidgets.QGridLayout()
        param_grid.setSpacing(6)

        self.p_center_freq = self._create_metric_card("Center Freq", "--")
        self.p_bandwidth = self._create_metric_card("Occupied BW", "--")
        self.p_peak_freq = self._create_metric_card("Peak Frequency", "--")
        self.p_power = self._create_metric_card("Signal Power", "--")

        self.p_noise_floor = self._create_metric_card("Noise Floor", "--")
        self.p_snr = self._create_metric_card("SNR", "--")
        self.p_rms = self._create_metric_card("RMS Amplitude", "--")
        self.p_peak_amp = self._create_metric_card("Peak Amplitude", "--")

        param_grid.addWidget(self.p_center_freq[0], 0, 0)
        param_grid.addWidget(self.p_bandwidth[0], 0, 1)
        param_grid.addWidget(self.p_peak_freq[0], 0, 2)
        param_grid.addWidget(self.p_power[0], 0, 3)

        param_grid.addWidget(self.p_noise_floor[0], 1, 0)
        param_grid.addWidget(self.p_snr[0], 1, 1)
        param_grid.addWidget(self.p_rms[0], 1, 2)
        param_grid.addWidget(self.p_peak_amp[0], 1, 3)

        layout.addLayout(param_grid)

        # Subpanel 2: Modulation Classification (Honest prototype indicator)
        title2 = QtWidgets.QLabel("MODULATION CLASSIFICATION")
        title2.setProperty("class", "PanelHeader")
        layout.addWidget(title2)

        mod_box = QtWidgets.QFrame()
        mod_box.setProperty("class", "SigmaSubPanel")
        mod_lay = QtWidgets.QVBoxLayout(mod_box)
        mod_lay.setContentsMargins(10, 8, 10, 8)
        mod_lay.setSpacing(6)

        row_mod = QtWidgets.QHBoxLayout()
        lbl_m = QtWidgets.QLabel("Identified Modulation:")
        lbl_m.setProperty("class", "CardLabel")
        row_mod.addWidget(lbl_m)

        self.lbl_mod_val = QtWidgets.QLabel("Not analyzed")
        self.lbl_mod_val.setStyleSheet(
            f"background-color: rgba(245, 158, 11, 0.15); color: {COLORS['accent_yellow']}; "
            f"border: 1px solid {COLORS['accent_yellow']}; border-radius: 3px; "
            f"padding: 2px 8px; font-weight: 700; font-size: 11px;"
        )
        row_mod.addWidget(self.lbl_mod_val)

        row_mod.addSpacing(16)
        lbl_conf = QtWidgets.QLabel("Confidence:")
        lbl_conf.setProperty("class", "CardLabel")
        row_mod.addWidget(lbl_conf)

        self.lbl_conf_val = QtWidgets.QLabel("--")
        self.lbl_conf_val.setProperty("class", "CardValue")
        row_mod.addWidget(self.lbl_conf_val)
        row_mod.addStretch(1)

        mod_lay.addLayout(row_mod)

        # Candidate modulations
        cand_label = QtWidgets.QLabel(
            "Classification Targets:  AM  •  FM  •  ASK  •  FSK  •  BPSK  •  QPSK  •  8PSK  •  QAM"
        )
        cand_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px; font-weight: 600;")
        mod_lay.addWidget(cand_label)

        layout.addWidget(mod_box)
        return panel

    # =========================================================================
    # Bottom Processing Pipeline Bar
    # =========================================================================
    def _build_pipeline_bar(self):
        frame = QtWidgets.QFrame()
        frame.setProperty("class", "SigmaPanel")
        layout = QtWidgets.QVBoxLayout(frame)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(4)

        header_lay = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("PROCESSING PIPELINE")
        title.setProperty("class", "PanelHeader")
        header_lay.addWidget(title)

        legend = QtWidgets.QLabel("✓ Implemented Stage  |  ◉ Active DSP Stage  |  ○ Planned Pipeline Stage")
        legend.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 10px;")
        header_lay.addStretch(1)
        header_lay.addWidget(legend)
        layout.addLayout(header_lay)

        # Pipeline stages row
        stages_lay = QtWidgets.QHBoxLayout()
        stages_lay.setSpacing(4)

        stages = [
            ("INPUT", "✓", "done"),
            ("IQ PARSER", "✓", "done"),
            ("DSP CORE", "◉", "active"),
            ("FFT", "✓", "done"),
            ("SPECTRUM", "✓", "done"),
            ("CONSTELLATION", "✓", "done"),
            ("FEATURES", "○", "pending"),
            ("MODULATION", "○", "pending"),
            ("DEMOD", "○", "pending"),
            ("SYMBOLS", "○", "pending"),
            ("BITS", "○", "pending"),
        ]

        for i, (name, symbol, status) in enumerate(stages):
            block = QtWidgets.QFrame()
            if status == "active":
                block.setProperty("class", "PipelineStageActive")
            elif status == "done":
                block.setProperty("class", "PipelineStageDone")
            else:
                block.setProperty("class", "PipelineStagePending")

            b_lay = QtWidgets.QVBoxLayout(block)
            b_lay.setContentsMargins(4, 3, 4, 3)
            b_lay.setSpacing(1)
            b_lay.setAlignment(Qt.AlignCenter)

            sym_lbl = QtWidgets.QLabel(symbol)
            sym_lbl.setProperty("class", "PipelineStageStatus")
            if status == "active":
                sym_lbl.setStyleSheet(f"color: {COLORS['accent_cyan']};")
            elif status == "done":
                sym_lbl.setStyleSheet(f"color: {COLORS['accent_green']};")
            else:
                sym_lbl.setStyleSheet(f"color: {COLORS['text_muted']};")

            name_lbl = QtWidgets.QLabel(name)
            name_lbl.setProperty("class", "PipelineStageName")
            name_lbl.setStyleSheet(f"color: {COLORS['text_primary'] if status != 'pending' else COLORS['text_muted']};")

            b_lay.addWidget(sym_lbl, 0, Qt.AlignCenter)
            b_lay.addWidget(name_lbl, 0, Qt.AlignCenter)

            stages_lay.addWidget(block, 1)

            # Arrow between blocks
            if i < len(stages) - 1:
                arr = QtWidgets.QLabel("→")
                arr.setStyleSheet(f"color: {COLORS['border_light']}; font-weight: bold; font-size: 11px;")
                stages_lay.addWidget(arr, 0, Qt.AlignCenter)

        layout.addLayout(stages_lay)
        return frame

    # =========================================================================
    # Helpers & Event Handlers
    # =========================================================================
    def _make_label(self, text, style_class):
        lbl = QtWidgets.QLabel(text)
        lbl.setProperty("class", style_class)
        return lbl

    def _update_all_displays(self):
        """Refreshes all metadata and UI card telemetry with real values."""
        m = self.metadata

        # Input panel
        self.lbl_in_file.setText(m.filename)
        self.lbl_in_format.setText(m.format_name)
        self.lbl_in_type.setText(m.datatype)
        self.lbl_in_samples.setText(f"{m.num_samples:,}" if m.num_samples > 0 else "--")
        self.lbl_in_duration.setText(m.duration_str)
        self.lbl_in_size.setText(m.filesize_str)

        # Overview cards
        cf_str = f"{self.center_freq / 1e3:.1f} kHz" if abs(self.center_freq) >= 1e3 else f"{self.center_freq:.0f} Hz"
        sr_str = f"{self.samp_rate / 1e6:.2f} MS/s" if self.samp_rate >= 1e6 else f"{self.samp_rate / 1e3:.1f} kS/s"

        self.card_center_freq[1].setText(cf_str)
        self.card_samp_rate[1].setText(sr_str)
        self.card_bandwidth[1].setText(m.occupied_bandwidth)
        self.card_signal_power[1].setText(m.signal_power_dbfs)
        self.card_noise_floor[1].setText(m.noise_floor)
        self.card_snr[1].setText(m.snr)
        self.card_peak_freq[1].setText(m.peak_frequency)
        self.card_duration[1].setText(m.duration_str)

        # Analysis parameters
        self.p_center_freq[1].setText(cf_str)
        self.p_bandwidth[1].setText(m.occupied_bandwidth)
        self.p_peak_freq[1].setText(m.peak_frequency)
        self.p_power[1].setText(m.signal_power_dbfs)
        self.p_noise_floor[1].setText(m.noise_floor)
        self.p_snr[1].setText(m.snr)
        self.p_rms[1].setText(m.rms_amplitude)
        self.p_peak_amp[1].setText(m.peak_amplitude)

        # Modulation
        self.lbl_mod_val.setText(m.modulation_class)
        self.lbl_conf_val.setText(m.modulation_confidence)

    def _toggle_run_stop(self):
        if self.is_running:
            self.flowgraph.stop()
            self.flowgraph.wait()
            self.is_running = False
            self.run_stop_btn.setText("▶ Start DSP")
            self.run_stop_btn.setProperty("class", "")
            self.status_pill.setText("○ DSP PAUSED")
            self.status_pill.setProperty("class", "StatusPillIdle")
        else:
            self.flowgraph.start()
            self.is_running = True
            self.run_stop_btn.setText("⏹ Stop DSP")
            self.run_stop_btn.setProperty("class", "PrimaryButton")
            self.status_pill.setText("● SYSTEM ONLINE")
            self.status_pill.setProperty("class", "StatusPillOnline")

        self.run_stop_btn.style().unpolish(self.run_stop_btn)
        self.run_stop_btn.style().polish(self.run_stop_btn)
        self.status_pill.style().unpolish(self.status_pill)
        self.status_pill.style().polish(self.status_pill)

    def _toggle_loop(self):
        self.is_looping = not self.is_looping
        self.loop_btn.setText(f"🔁 Loop: {'ON' if self.is_looping else 'OFF'}")
        self.flowgraph.reload_file(self.current_file, repeat=self.is_looping)

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
                "WAV IQ Parser Notice",
                f"Selected WAV file:\n{os.path.basename(path)}\n\n"
                "SIGMA WAV Demuxer is registered for pipeline stage 1. "
                "In this prototype, raw complex float32 (.iq) files are directly streamed into the GNU Radio core."
            )

    def _reset_file(self):
        default_file = "signal.iq"
        if os.path.exists(default_file):
            self.current_file = default_file
            self.flowgraph.reload_file(self.current_file, repeat=self.is_looping)
            self.metadata = SignalMetadata(self.current_file, self.samp_rate, self.center_freq)
            self._update_all_displays()

    def closeEvent(self, event):
        try:
            self.flowgraph.stop()
            self.flowgraph.wait()
        except Exception:
            pass
        event.accept()
