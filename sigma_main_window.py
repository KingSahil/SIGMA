"""
SIGMA - Signal Intelligence & Generalized Modulation Analyzer
Main Application Window (PyQt5)
FL Studio Inspired Digital Audio / SDR Workstation Design
"""

import os
import sys
import random
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt, QTimer

from sigma_theme import COLORS, MAIN_QSS
from sigma_analyzer_core import SignalMetadata
from sigma_flowgraph import SigmaFlowgraph


class SettingsDialog(QtWidgets.QDialog):
    """FL Studio Styled Settings Dialog for RF configuration."""

    def __init__(self, parent=None, samp_rate=1000000, center_freq=0.0):
        super().__init__(parent)
        self.setWindowTitle("SIGMA — Project Audio & SDR Configuration")
        self.setMinimumWidth(400)
        self.setStyleSheet(MAIN_QSS)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(18, 18, 18, 18)

        title = QtWidgets.QLabel("RF HARDWARE & DSP ENGINE CONFIG")
        title.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {COLORS['fl_orange']}; letter-spacing: 1px;")
        layout.addWidget(title)

        form = QtWidgets.QFormLayout()
        form.setSpacing(12)

        # Sample Rate
        self.rate_spin = QtWidgets.QDoubleSpinBox()
        self.rate_spin.setRange(1e3, 100e6)
        self.rate_spin.setValue(samp_rate)
        self.rate_spin.setSingleStep(100e3)
        self.rate_spin.setSuffix(" S/s")
        form.addRow("Master Sample Rate:", self.rate_spin)

        # Center Frequency
        self.freq_spin = QtWidgets.QDoubleSpinBox()
        self.freq_spin.setRange(-10e9, 10e9)
        self.freq_spin.setValue(center_freq)
        self.freq_spin.setSingleStep(10e3)
        self.freq_spin.setSuffix(" Hz")
        form.addRow("Master Center Freq:", self.freq_spin)

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


class VUMeterWidget(QtWidgets.QWidget):
    """FL Studio styled LED Bar VU Meter with peak hold."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(120, 26)
        self.setMaximumHeight(32)
        self.level = 0.72
        self.peak = 0.85
        self.is_active = True

    def set_level(self, level, peak=None):
        self.level = max(0.0, min(1.0, level))
        if peak is not None:
            self.peak = max(0.0, min(1.0, peak))
        elif self.level > self.peak:
            self.peak = self.level
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # Background well
        painter.setPen(QtGui.QColor(COLORS['border_dark']))
        painter.setBrush(QtGui.QColor(COLORS['bg_surface_dark']))
        painter.drawRoundedRect(0, 0, w, h, 3, 3)

        if not self.is_active:
            return

        # Segments: 20 LED bars
        num_bars = 20
        gap = 2
        bar_w = max(2, int((w - 8 - (num_bars - 1) * gap) / num_bars))
        active_bars = int(self.level * num_bars)
        peak_bar = int(self.peak * num_bars)

        start_x = 4
        bar_h = h - 8
        bar_y = 4

        for i in range(num_bars):
            bx = start_x + i * (bar_w + gap)
            frac = i / float(num_bars)

            # FL Studio LED Color stops: Green -> Yellow/Amber -> Red
            if frac < 0.65:
                on_color = QtGui.QColor(COLORS['fl_lime'])
                off_color = QtGui.QColor(25, 45, 30)
            elif frac < 0.85:
                on_color = QtGui.QColor(COLORS['fl_amber'])
                off_color = QtGui.QColor(50, 40, 15)
            else:
                on_color = QtGui.QColor(COLORS['fl_red'])
                off_color = QtGui.QColor(55, 20, 25)

            if i <= active_bars:
                painter.fillRect(bx, bar_y, bar_w, bar_h, on_color)
            elif i == peak_bar:
                painter.fillRect(bx, bar_y, bar_w, bar_h, QtGui.QColor("#ffffff"))
            else:
                painter.fillRect(bx, bar_y, bar_w, bar_h, off_color)


class SigmaMainWindow(QtWidgets.QMainWindow):
    """
    Main desktop interface for the SIGMA system.
    FL Studio Inspired Digital Audio / SDR Workstation Design.
    """

    def __init__(self, initial_file="signal.iq"):
        super().__init__()
        self.setWindowTitle("SIGMA — Signal Intelligence & Generalized Modulation Analyzer [FL SDR Studio]")
        self.resize(1480, 960)

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

        # Apply FL Studio Stylesheet
        self.setStyleSheet(MAIN_QSS)

        # Build UI
        self._init_menu_bar()
        self._init_ui()
        self._update_all_displays()

        # Start Flowgraph
        self.flowgraph.start()
        self.flowgraph.flowgraph_started.set()

        # Dynamic VU Meter & LED Animation Timer
        self.anim_timer = QTimer(self)
        self.anim_timer.setInterval(80)
        self.anim_timer.timeout.connect(self._animate_live_meters)
        self.anim_timer.start()

    # =========================================================================
    # Top FL Studio Menu Bar
    # =========================================================================
    def _init_menu_bar(self):
        menubar = self.menuBar()

        # File
        file_menu = menubar.addMenu("FILE")
        act_open_iq = QtWidgets.QAction("📂 Open IQ File...", self)
        act_open_iq.triggered.connect(self._load_iq_file)
        file_menu.addAction(act_open_iq)

        act_open_wav = QtWidgets.QAction("🎵 Open WAV Audio...", self)
        act_open_wav.triggered.connect(self._load_wav_file)
        file_menu.addAction(act_open_wav)

        file_menu.addSeparator()
        act_reset = QtWidgets.QAction("🔄 Revert to Default (signal.iq)", self)
        act_reset.triggered.connect(self._reset_file)
        file_menu.addAction(act_reset)

        act_exit = QtWidgets.QAction("✕ Exit SIGMA", self)
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

        # Edit
        edit_menu = menubar.addMenu("EDIT")
        edit_menu.addAction("Cut IQ Region")
        edit_menu.addAction("Copy Samples")
        edit_menu.addAction("Paste")

        # View
        view_menu = menubar.addMenu("VIEW")
        view_menu.addAction("Wave Candy (Time Domain)")
        view_menu.addAction("Fruity Parametric (Spectrum)")
        view_menu.addAction("Vector Scope (Constellation)")
        view_menu.addAction("Mixer Insert Chain")

        # DSP
        dsp_menu = menubar.addMenu("DSP")
        act_run = QtWidgets.QAction("Toggle DSP Engine (Space)", self)
        act_run.triggered.connect(self._toggle_run_stop)
        dsp_menu.addAction(act_run)

        act_loop = QtWidgets.QAction("Toggle Loop Playback", self)
        act_loop.triggered.connect(self._toggle_loop)
        dsp_menu.addAction(act_loop)

        # Options
        opt_menu = menubar.addMenu("OPTIONS")
        act_settings = QtWidgets.QAction("⚙ Audio / SDR Settings...", self)
        act_settings.triggered.connect(self._open_settings)
        opt_menu.addAction(act_settings)

        # Help
        help_menu = menubar.addMenu("HELP")
        help_menu.addAction("SIGMA SIH 2026 Manual")
        help_menu.addAction("About FL SDR Studio")

    # =========================================================================
    # Main UI Construction
    # =========================================================================
    def _init_ui(self):
        central = QtWidgets.QWidget(self)
        central.setObjectName("CentralWidget")
        self.setCentralWidget(central)

        main_layout = QtWidgets.QVBoxLayout(central)
        main_layout.setContentsMargins(10, 6, 10, 8)
        main_layout.setSpacing(8)

        # 1. Master FL Studio Transport Bar
        main_layout.addWidget(self._build_transport_bar())

        # 2. Deck: Channel Rack & Inspector
        main_layout.addLayout(self._build_channel_deck())

        # 3. Main Center Workstation (Visualizer Windows Splitter)
        graphs_splitter = QtWidgets.QSplitter(Qt.Vertical)
        graphs_splitter.setChildrenCollapsible(False)

        # Upper Deck: Time Domain & Frequency Spectrum
        upper_row = QtWidgets.QHBoxLayout()
        upper_row.setSpacing(8)
        upper_row.addWidget(self._build_time_domain_window(), 1)
        upper_row.addWidget(self._build_freq_window(), 1)
        upper_widget = QtWidgets.QWidget()
        upper_widget.setLayout(upper_row)
        graphs_splitter.addWidget(upper_widget)

        # Lower Deck: Constellation & Signal Analyzer
        lower_row = QtWidgets.QHBoxLayout()
        lower_row.setSpacing(8)
        lower_row.addWidget(self._build_constellation_window(), 1)
        lower_row.addWidget(self._build_analyzer_window(), 1)
        lower_widget = QtWidgets.QWidget()
        lower_widget.setLayout(lower_row)
        graphs_splitter.addWidget(lower_widget)

        main_layout.addWidget(graphs_splitter, 1)

        # 4. Bottom Mixer FX Insert Chain
        main_layout.addWidget(self._build_mixer_rack())

    # =========================================================================
    # Window Wrapper Helper (FL Studio Window Header & Frame)
    # =========================================================================
    def _build_fl_window(self, title, badge_text, badge_color, inner_widget, subtitle=""):
        frame = QtWidgets.QFrame()
        frame.setProperty("class", "FLWindow")
        layout = QtWidgets.QVBoxLayout(frame)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)

        # Header Bar
        header = QtWidgets.QFrame()
        header.setProperty("class", "FLWindowHeader")
        h_lay = QtWidgets.QHBoxLayout(header)
        h_lay.setContentsMargins(8, 3, 8, 3)
        h_lay.setSpacing(8)

        # Color strip dot
        dot = QtWidgets.QLabel("●")
        dot.setStyleSheet(f"color: {badge_color}; font-size: 11px;")
        h_lay.addWidget(dot)

        # Title
        t_lbl = QtWidgets.QLabel(title)
        t_lbl.setProperty("class", "FLWindowTitle")
        h_lay.addWidget(t_lbl)

        # Badge
        badge = QtWidgets.QLabel(badge_text)
        badge.setProperty("class", "FLWindowBadge")
        badge.setStyleSheet(f"background-color: {badge_color}; color: #000000;")
        h_lay.addWidget(badge)

        h_lay.addStretch(1)

        if subtitle:
            sub = QtWidgets.QLabel(subtitle)
            sub.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 10px; font-family: 'Consolas', monospace;")
            h_lay.addWidget(sub)

        # Window controls mockup (FL Studio style)
        min_btn = QtWidgets.QLabel("–")
        min_btn.setStyleSheet(f"color: {COLORS['text_muted']}; font-weight: bold; padding: 0 4px;")
        cls_btn = QtWidgets.QLabel("✕")
        cls_btn.setStyleSheet(f"color: {COLORS['text_muted']}; font-weight: bold; padding: 0 4px;")
        h_lay.addWidget(min_btn)
        h_lay.addWidget(cls_btn)

        layout.addWidget(header)

        # Body container
        body = QtWidgets.QWidget()
        body_lay = QtWidgets.QVBoxLayout(body)
        body_lay.setContentsMargins(8, 6, 8, 6)
        body_lay.addWidget(inner_widget)
        layout.addWidget(body, 1)

        return frame

    # =========================================================================
    # 1. Master FL Studio Transport Bar
    # =========================================================================
    def _build_transport_bar(self):
        bar = QtWidgets.QFrame()
        bar.setProperty("class", "FLWindow")
        layout = QtWidgets.QHBoxLayout(bar)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(10)

        # Brand / Logo
        brand_box = QtWidgets.QHBoxLayout()
        brand_box.setSpacing(6)
        logo = QtWidgets.QLabel("🎛️")
        logo.setStyleSheet("font-size: 18px;")
        brand_box.addWidget(logo)

        brand_text = QtWidgets.QVBoxLayout()
        brand_text.setSpacing(0)
        t1 = QtWidgets.QLabel("SIGMA 2.0")
        t1.setStyleSheet(f"font-weight: 800; font-size: 13px; letter-spacing: 1.5px; color: {COLORS['text_primary']};")
        t2 = QtWidgets.QLabel("SDR WORKSTATION")
        t2.setStyleSheet(f"font-size: 9px; font-weight: 700; letter-spacing: 1px; color: {COLORS['fl_orange']};")
        brand_text.addWidget(t1)
        brand_text.addWidget(t2)
        brand_box.addLayout(brand_text)
        layout.addLayout(brand_box)

        # Vertical separator
        layout.addWidget(self._make_vsep())

        # Transport Buttons (FL Studio DAW Style)
        trans_box = QtWidgets.QHBoxLayout()
        trans_box.setSpacing(6)

        # Play / Pause
        self.btn_play = QtWidgets.QPushButton("▶ PLAY")
        self.btn_play.setProperty("class", "FLTransportBtn FLPlayActive")
        self.btn_play.clicked.connect(self._toggle_run_stop)
        trans_box.addWidget(self.btn_play)

        # Stop
        self.btn_stop = QtWidgets.QPushButton("⏹ STOP")
        self.btn_stop.setProperty("class", "FLTransportBtn")
        self.btn_stop.clicked.connect(self._force_stop)
        trans_box.addWidget(self.btn_stop)

        # Loop
        self.btn_loop = QtWidgets.QPushButton("🔁 SONG LOOP")
        self.btn_loop.setProperty("class", "FLTransportBtn")
        self.btn_loop.setStyleSheet(f"color: {COLORS['fl_orange']};")
        self.btn_loop.clicked.connect(self._toggle_loop)
        trans_box.addWidget(self.btn_loop)

        # Rewind
        self.btn_rewind = QtWidgets.QPushButton("⏮ REW")
        self.btn_rewind.setProperty("class", "FLTransportBtn")
        self.btn_rewind.clicked.connect(self._reset_file)
        trans_box.addWidget(self.btn_rewind)

        layout.addLayout(trans_box)
        layout.addWidget(self._make_vsep())

        # Digital LCD Readouts (Digital Clock & Sample Counter)
        lcd_row = QtWidgets.QHBoxLayout()
        lcd_row.setSpacing(8)

        # Time / Position LCD
        lcd_time = QtWidgets.QFrame()
        lcd_time.setProperty("class", "FLLcdBox")
        lt_lay = QtWidgets.QVBoxLayout(lcd_time)
        lt_lay.setContentsMargins(8, 2, 8, 2)
        lt_lay.setSpacing(0)
        lbl_t_title = QtWidgets.QLabel("TIME / POS")
        lbl_t_title.setProperty("class", "FLLcdLabel")
        self.lbl_lcd_time = QtWidgets.QLabel("00:00:50.00")
        self.lbl_lcd_time.setProperty("class", "FLLcdValue")
        lt_lay.addWidget(lbl_t_title)
        lt_lay.addWidget(self.lbl_lcd_time)
        lcd_row.addWidget(lcd_time)

        # Sample Rate LCD
        lcd_rate = QtWidgets.QFrame()
        lcd_rate.setProperty("class", "FLLcdBox")
        lr_lay = QtWidgets.QVBoxLayout(lcd_rate)
        lr_lay.setContentsMargins(8, 2, 8, 2)
        lr_lay.setSpacing(0)
        lbl_r_title = QtWidgets.QLabel("SAMPLE CLOCK")
        lbl_r_title.setProperty("class", "FLLcdLabel")
        self.lbl_lcd_rate = QtWidgets.QLabel("1.00 MSPS")
        self.lbl_lcd_rate.setProperty("class", "FLLcdValueAmber")
        lr_lay.addWidget(lbl_r_title)
        lr_lay.addWidget(self.lbl_lcd_rate)
        lcd_row.addWidget(lcd_rate)

        # Center Freq LCD
        lcd_freq = QtWidgets.QFrame()
        lcd_freq.setProperty("class", "FLLcdBox")
        lf_lay = QtWidgets.QVBoxLayout(lcd_freq)
        lf_lay.setContentsMargins(8, 2, 8, 2)
        lf_lay.setSpacing(0)
        lbl_f_title = QtWidgets.QLabel("TUNING FREQ")
        lbl_f_title.setProperty("class", "FLLcdLabel")
        self.lbl_lcd_freq = QtWidgets.QLabel("0.000 MHz")
        self.lbl_lcd_freq.setProperty("class", "FLLcdValueCyan")
        lf_lay.addWidget(lbl_f_title)
        lf_lay.addWidget(self.lbl_lcd_freq)
        lcd_row.addWidget(lcd_freq)

        layout.addLayout(lcd_row)
        layout.addWidget(self._make_vsep())

        # Master Output VU Meter
        vu_box = QtWidgets.QVBoxLayout()
        vu_box.setSpacing(1)
        vu_header = QtWidgets.QHBoxLayout()
        vu_lbl = QtWidgets.QLabel("MASTER RF LEVEL")
        vu_lbl.setProperty("class", "FLLcdLabel")
        self.lbl_vu_peak = QtWidgets.QLabel("-0.0 dB")
        self.lbl_vu_peak.setStyleSheet(f"font-size: 9px; font-family: 'Consolas', monospace; color: {COLORS['fl_lime']};")
        vu_header.addWidget(vu_lbl)
        vu_header.addStretch(1)
        vu_header.addWidget(self.lbl_vu_peak)
        vu_box.addLayout(vu_header)

        self.vu_meter = VUMeterWidget()
        vu_box.addWidget(self.vu_meter)
        layout.addLayout(vu_box)

        layout.addStretch(1)

        # System Online LED pill & Settings
        right_box = QtWidgets.QHBoxLayout()
        right_box.setSpacing(8)

        self.status_pill = QtWidgets.QLabel("● ONLINE")
        self.status_pill.setProperty("class", "FLLedOnline")
        right_box.addWidget(self.status_pill)

        self.btn_settings = QtWidgets.QPushButton("⚙ CONFIG")
        self.btn_settings.setProperty("class", "FLActionBtn")
        self.btn_settings.clicked.connect(self._open_settings)
        right_box.addWidget(self.btn_settings)

        layout.addLayout(right_box)
        return bar

    # =========================================================================
    # 2. Deck: Channel Rack & Signal Overview
    # =========================================================================
    def _build_channel_deck(self):
        row = QtWidgets.QHBoxLayout()
        row.setSpacing(8)

        # Track 01: Input Source (FL Studio Track Header Style)
        input_container = QtWidgets.QWidget()
        in_main = QtWidgets.QVBoxLayout(input_container)
        in_main.setContentsMargins(4, 4, 4, 4)
        in_main.setSpacing(8)

        # Track parameters grid
        grid = QtWidgets.QGridLayout()
        grid.setSpacing(6)

        grid.addWidget(self._make_label("Source Stream:", "FLTrackLabel"), 0, 0)
        self.lbl_in_file = self._make_label("--", "FLTrackValue")
        self.lbl_in_file.setStyleSheet(f"color: {COLORS['fl_cyan']}; font-weight: bold;")
        grid.addWidget(self.lbl_in_file, 0, 1)

        grid.addWidget(self._make_label("Datatype:", "FLTrackLabel"), 1, 0)
        self.lbl_in_type = self._make_label("Complex Float32 (fc32)", "FLTrackValue")
        grid.addWidget(self.lbl_in_type, 1, 1)

        grid.addWidget(self._make_label("Buffer Samples:", "FLTrackLabel"), 0, 2)
        self.lbl_in_samples = self._make_label("--", "FLTrackValue")
        grid.addWidget(self.lbl_in_samples, 0, 3)

        grid.addWidget(self._make_label("Duration / Size:", "FLTrackLabel"), 1, 2)
        self.lbl_in_duration = self._make_label("--", "FLTrackValue")
        grid.addWidget(self.lbl_in_duration, 1, 3)

        in_main.addLayout(grid)

        # Action Buttons
        btn_bar = QtWidgets.QHBoxLayout()
        btn_bar.setSpacing(6)

        self.btn_load_iq = QtWidgets.QPushButton("📂 LOAD IQ FILE")
        self.btn_load_iq.setProperty("class", "FLActionBtn")
        self.btn_load_iq.setStyleSheet(f"border-color: {COLORS['fl_cyan']}; color: {COLORS['fl_cyan']};")
        self.btn_load_iq.clicked.connect(self._load_iq_file)
        btn_bar.addWidget(self.btn_load_iq)

        self.btn_load_wav = QtWidgets.QPushButton("🎵 LOAD WAV AUDIO")
        self.btn_load_wav.setProperty("class", "FLActionBtn")
        self.btn_load_wav.clicked.connect(self._load_wav_file)
        btn_bar.addWidget(self.btn_load_wav)

        self.btn_reset = QtWidgets.QPushButton("🔄 RELOAD")
        self.btn_reset.setProperty("class", "FLActionBtn")
        self.btn_reset.clicked.connect(self._reset_file)
        btn_bar.addWidget(self.btn_reset)

        in_main.addLayout(btn_bar)

        input_window = self._build_fl_window(
            "INPUT SOURCE",
            "TRACK 01",
            COLORS['fl_purple'],
            input_container,
            "RAW IQ BINARY STREAM"
        )
        row.addWidget(input_window, 4)

        # Track 02: Signal Overview (Hardware Rack Style)
        overview_container = QtWidgets.QWidget()
        over_main = QtWidgets.QVBoxLayout(overview_container)
        over_main.setContentsMargins(4, 4, 4, 4)
        over_main.setSpacing(6)

        cards_grid = QtWidgets.QGridLayout()
        cards_grid.setSpacing(6)

        self.card_center_freq = self._create_rack_card("Center Frequency", "--", COLORS['fl_cyan'])
        self.card_samp_rate = self._create_rack_card("Sample Rate", "--", COLORS['fl_amber'])
        self.card_bandwidth = self._create_rack_card("Occupied BW", "--", COLORS['fl_lime'])
        self.card_signal_power = self._create_rack_card("Signal Power", "--", COLORS['fl_orange'])

        self.card_noise_floor = self._create_rack_card("Noise Floor", "--", COLORS['text_secondary'])
        self.card_snr = self._create_rack_card("Signal SNR", "--", COLORS['fl_lime'])
        self.card_peak_freq = self._create_rack_card("Peak Frequency", "--", COLORS['fl_magenta'])
        self.card_duration = self._create_rack_card("Time Length", "--", COLORS['text_secondary'])

        cards_grid.addWidget(self.card_center_freq[0], 0, 0)
        cards_grid.addWidget(self.card_samp_rate[0], 0, 1)
        cards_grid.addWidget(self.card_bandwidth[0], 0, 2)
        cards_grid.addWidget(self.card_signal_power[0], 0, 3)

        cards_grid.addWidget(self.card_noise_floor[0], 1, 0)
        cards_grid.addWidget(self.card_snr[0], 1, 1)
        cards_grid.addWidget(self.card_peak_freq[0], 1, 2)
        cards_grid.addWidget(self.card_duration[0], 1, 3)

        over_main.addLayout(cards_grid)

        overview_window = self._build_fl_window(
            "SIGNAL OVERVIEW",
            "MASTER BUS",
            COLORS['fl_sage'],
            overview_container,
            "TELEMETRY DSP"
        )
        row.addWidget(overview_window, 6)

        return row

    def _create_rack_card(self, title, default_val="--", accent_color=None):
        frame = QtWidgets.QFrame()
        frame.setProperty("class", "FLTrackCard")
        lay = QtWidgets.QVBoxLayout(frame)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setSpacing(2)

        lbl_title = QtWidgets.QLabel(title)
        lbl_title.setProperty("class", "FLTrackLabel")
        lay.addWidget(lbl_title)

        lbl_val = QtWidgets.QLabel(default_val)
        lbl_val.setProperty("class", "FLTrackValue")
        if accent_color:
            lbl_val.setStyleSheet(f"color: {accent_color};")
        lay.addWidget(lbl_val)

        return frame, lbl_val

    # =========================================================================
    # 3. Workstation Visualizer Windows
    # =========================================================================
    def _build_time_domain_window(self):
        container = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.flowgraph.time_sink_widget)

        return self._build_fl_window(
            "WAVE CANDY — TIME DOMAIN",
            "RAW I / Q",
            COLORS['fl_cyan'],
            container,
            "I: Cyan  |  Q: Magenta"
        )

    def _build_freq_window(self):
        container = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.flowgraph.freq_sink_widget)

        return self._build_fl_window(
            "FRUITY PARAMETRIC — SPECTRUM",
            "FFT 1024",
            COLORS['fl_lime'],
            container,
            "Blackman-Harris Window"
        )

    def _build_constellation_window(self):
        container = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.flowgraph.const_sink_widget)

        return self._build_fl_window(
            "VECTOR SCOPE — CONSTELLATION",
            "IQ MAP",
            COLORS['fl_orange'],
            container,
            "In-Phase vs Quadrature"
        )

    def _build_analyzer_window(self):
        container = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(container)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.setSpacing(8)

        # Signal Parameter Cards
        param_grid = QtWidgets.QGridLayout()
        param_grid.setSpacing(6)

        self.p_center_freq = self._create_rack_card("Center Freq", "--", COLORS['fl_cyan'])
        self.p_bandwidth = self._create_rack_card("Occupied BW", "--", COLORS['fl_lime'])
        self.p_peak_freq = self._create_rack_card("Peak Frequency", "--", COLORS['fl_magenta'])
        self.p_power = self._create_rack_card("Signal Power", "--", COLORS['fl_orange'])

        self.p_noise_floor = self._create_rack_card("Noise Floor", "--")
        self.p_snr = self._create_rack_card("SNR Ratio", "--", COLORS['fl_lime'])
        self.p_rms = self._create_rack_card("RMS Amplitude", "--")
        self.p_peak_amp = self._create_rack_card("Peak Amplitude", "--")

        param_grid.addWidget(self.p_center_freq[0], 0, 0)
        param_grid.addWidget(self.p_bandwidth[0], 0, 1)
        param_grid.addWidget(self.p_peak_freq[0], 0, 2)
        param_grid.addWidget(self.p_power[0], 0, 3)

        param_grid.addWidget(self.p_noise_floor[0], 1, 0)
        param_grid.addWidget(self.p_snr[0], 1, 1)
        param_grid.addWidget(self.p_rms[0], 1, 2)
        param_grid.addWidget(self.p_peak_amp[0], 1, 3)

        lay.addLayout(param_grid)

        # Modulation Classification Rack Unit
        mod_box = QtWidgets.QFrame()
        mod_box.setProperty("class", "FLTrackCard")
        mod_lay = QtWidgets.QVBoxLayout(mod_box)
        mod_lay.setContentsMargins(10, 8, 10, 8)
        mod_lay.setSpacing(6)

        row_mod = QtWidgets.QHBoxLayout()
        lbl_m = QtWidgets.QLabel("CLASSIFIED MODULATION:")
        lbl_m.setProperty("class", "FLTrackLabel")
        row_mod.addWidget(lbl_m)

        self.lbl_mod_val = QtWidgets.QLabel("Not analyzed")
        self.lbl_mod_val.setStyleSheet(
            f"background-color: rgba(255, 170, 0, 0.2); color: {COLORS['fl_amber']}; "
            f"border: 1px solid {COLORS['fl_amber']}; border-radius: 3px; "
            f"padding: 3px 10px; font-weight: 800; font-size: 11px;"
        )
        row_mod.addWidget(self.lbl_mod_val)

        row_mod.addSpacing(12)
        lbl_conf = QtWidgets.QLabel("CONFIDENCE:")
        lbl_conf.setProperty("class", "FLTrackLabel")
        row_mod.addWidget(lbl_conf)

        self.lbl_conf_val = QtWidgets.QLabel("--")
        self.lbl_conf_val.setProperty("class", "FLTrackValue")
        self.lbl_conf_val.setStyleSheet(f"color: {COLORS['fl_lime']}; font-weight: bold;")
        row_mod.addWidget(self.lbl_conf_val)
        row_mod.addStretch(1)

        mod_lay.addLayout(row_mod)

        # Targets Strip
        cand_label = QtWidgets.QLabel("TARGETS:  AM  •  FM  •  ASK  •  FSK  •  BPSK  •  QPSK  •  8PSK  •  QAM")
        cand_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 9px; font-weight: 700; letter-spacing: 0.5px;")
        mod_lay.addWidget(cand_label)

        lay.addWidget(mod_box)

        return self._build_fl_window(
            "EDISON ANALYZER — TELEMETRY",
            "CLASSIFIER",
            COLORS['fl_purple'],
            container,
            "AUTOMATIC ESTIMATOR"
        )

    # =========================================================================
    # 4. Bottom Mixer FX Insert Rack
    # =========================================================================
    def _build_mixer_rack(self):
        frame = QtWidgets.QFrame()
        frame.setProperty("class", "FLWindow")
        layout = QtWidgets.QVBoxLayout(frame)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)

        header_lay = QtWidgets.QHBoxLayout()
        t = QtWidgets.QLabel("MIXER FX INSERT CHAIN")
        t.setProperty("class", "FLWindowTitle")
        header_lay.addWidget(t)

        badge = QtWidgets.QLabel("ROUTING")
        badge.setProperty("class", "FLWindowBadge")
        badge.setStyleSheet(f"background-color: {COLORS['fl_orange']}; color: #000000;")
        header_lay.addWidget(badge)

        legend = QtWidgets.QLabel("✓ Insert Loaded  |  ◉ Active Core DSP  |  ○ Standby Module")
        legend.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 10px;")
        header_lay.addStretch(1)
        header_lay.addWidget(legend)
        layout.addLayout(header_lay)

        # Mixer slots
        stages_lay = QtWidgets.QHBoxLayout()
        stages_lay.setSpacing(4)

        slots = [
            ("01", "INPUT", "✓", "done", COLORS['fl_purple']),
            ("02", "IQ PARSER", "✓", "done", COLORS['fl_purple']),
            ("03", "DSP CORE", "◉", "active", COLORS['fl_orange']),
            ("04", "FFT ENGINE", "✓", "done", COLORS['fl_lime']),
            ("05", "SPECTRUM", "✓", "done", COLORS['fl_lime']),
            ("06", "CONSTELL", "✓", "done", COLORS['fl_cyan']),
            ("07", "FEATURES", "○", "pending", COLORS['border_light']),
            ("08", "MOD CLASSIF", "○", "pending", COLORS['border_light']),
            ("09", "DEMOD", "○", "pending", COLORS['border_light']),
            ("10", "BITSTREAM", "○", "pending", COLORS['border_light']),
        ]

        for i, (num, name, symbol, status, color) in enumerate(slots):
            block = QtWidgets.QFrame()
            block.setProperty("class", "FLTrackCard")

            if status == "active":
                block.setStyleSheet(f"border: 1px solid {COLORS['fl_orange']}; background-color: rgba(255, 140, 0, 0.15);")
            elif status == "done":
                block.setStyleSheet(f"border: 1px solid {COLORS['border_light']}; background-color: {COLORS['bg_rack']};")
            else:
                block.setStyleSheet(f"border: 1px solid {COLORS['border_dark']}; background-color: {COLORS['bg_surface_dark']}; opacity: 0.6;")

            b_lay = QtWidgets.QVBoxLayout(block)
            b_lay.setContentsMargins(4, 3, 4, 3)
            b_lay.setSpacing(1)
            b_lay.setAlignment(Qt.AlignCenter)

            num_lbl = QtWidgets.QLabel(f"SLOT {num}")
            num_lbl.setStyleSheet(f"font-size: 8px; font-weight: 800; color: {color};")
            b_lay.addWidget(num_lbl, 0, Qt.AlignCenter)

            sym_lbl = QtWidgets.QLabel(symbol)
            sym_lbl.setStyleSheet(f"font-size: 11px; font-weight: 800; color: {color};")
            b_lay.addWidget(sym_lbl, 0, Qt.AlignCenter)

            name_lbl = QtWidgets.QLabel(name)
            name_lbl.setStyleSheet(f"font-size: 9px; font-weight: 700; color: {COLORS['text_primary'] if status != 'pending' else COLORS['text_muted']};")
            b_lay.addWidget(name_lbl, 0, Qt.AlignCenter)

            stages_lay.addWidget(block, 1)

            if i < len(slots) - 1:
                arr = QtWidgets.QLabel("›")
                arr.setStyleSheet(f"color: {COLORS['border_light']}; font-weight: bold; font-size: 14px;")
                stages_lay.addWidget(arr, 0, Qt.AlignCenter)

        layout.addLayout(stages_lay)
        return frame

    # =========================================================================
    # Helpers & Handlers
    # =========================================================================
    def _make_label(self, text, style_class):
        lbl = QtWidgets.QLabel(text)
        lbl.setProperty("class", style_class)
        return lbl

    def _make_vsep(self):
        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.VLine)
        sep.setStyleSheet(f"color: {COLORS['border']}; margin: 2px 4px;")
        return sep

    def _animate_live_meters(self):
        """Micro-animation loop for master VU level meters and LCD displays."""
        if not self.is_running:
            self.vu_meter.is_active = False
            self.vu_meter.set_level(0.0, 0.0)
            self.lbl_vu_peak.setText("-∞ dB")
            return

        self.vu_meter.is_active = True
        # Base level between 0.65 and 0.88 with occasional peaks
        jitter = random.uniform(-0.06, 0.06)
        lvl = max(0.40, min(0.95, 0.76 + jitter))
        self.vu_meter.set_level(lvl)
        db_val = (1.0 - lvl) * -30.0
        self.lbl_vu_peak.setText(f"{db_val:+.1f} dB")

    def _update_all_displays(self):
        """Refreshes all metadata and UI card telemetry with real values."""
        m = self.metadata

        # Input panel
        self.lbl_in_file.setText(m.filename)
        self.lbl_in_type.setText(m.datatype)
        self.lbl_in_samples.setText(f"{m.num_samples:,}" if m.num_samples > 0 else "--")
        self.lbl_in_duration.setText(f"{m.duration_str} ({m.filesize_str})")

        # Overview cards
        cf_str = f"{self.center_freq / 1e6:.3f} MHz" if abs(self.center_freq) >= 1e6 else f"{self.center_freq / 1e3:.1f} kHz"
        sr_str = f"{self.samp_rate / 1e6:.2f} MSPS" if self.samp_rate >= 1e6 else f"{self.samp_rate / 1e3:.1f} kSPS"

        self.card_center_freq[1].setText(cf_str)
        self.card_samp_rate[1].setText(sr_str)
        self.card_bandwidth[1].setText(m.occupied_bandwidth)
        self.card_signal_power[1].setText(m.signal_power_dbfs)
        self.card_noise_floor[1].setText(m.noise_floor)
        self.card_snr[1].setText(m.snr)
        self.card_peak_freq[1].setText(m.peak_frequency)
        self.card_duration[1].setText(m.duration_str)

        # LCD Displays on Transport bar
        self.lbl_lcd_rate.setText(sr_str)
        self.lbl_lcd_freq.setText(cf_str)
        self.lbl_lcd_time.setText(f"00:00:{m.duration_str.replace(' ms', '').zfill(5)}" if m.duration_str != "--" else "00:00:50.00")

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
            self._force_stop()
        else:
            self.flowgraph.start()
            self.is_running = True
            self.btn_play.setText("▶ PLAY")
            self.btn_play.setProperty("class", "FLTransportBtn FLPlayActive")
            self.status_pill.setText("● ONLINE")
            self.status_pill.setProperty("class", "FLLedOnline")
            self.btn_play.style().unpolish(self.btn_play)
            self.btn_play.style().polish(self.btn_play)
            self.status_pill.style().unpolish(self.status_pill)
            self.status_pill.style().polish(self.status_pill)

    def _force_stop(self):
        if self.is_running:
            self.flowgraph.stop()
            self.flowgraph.wait()
            self.is_running = False
            self.btn_play.setText("▶ PLAY")
            self.btn_play.setProperty("class", "FLTransportBtn")
            self.status_pill.setText("○ PAUSED")
            self.status_pill.setProperty("class", "FLLedOffline")
            self.btn_play.style().unpolish(self.btn_play)
            self.btn_play.style().polish(self.btn_play)
            self.status_pill.style().unpolish(self.status_pill)
            self.status_pill.style().polish(self.status_pill)

    def _toggle_loop(self):
        self.is_looping = not self.is_looping
        if self.is_looping:
            self.btn_loop.setText("🔁 SONG LOOP")
            self.btn_loop.setStyleSheet(f"color: {COLORS['fl_orange']};")
        else:
            self.btn_loop.setText("🔁 PAT SINGLE")
            self.btn_loop.setStyleSheet(f"color: {COLORS['text_secondary']};")
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
                "FL SDR Studio — Audio Demuxer",
                f"Selected WAV file:\n{os.path.basename(path)}\n\n"
                "SIGMA WAV Demuxer is registered for Mixer Insert Slot 01. "
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
            self.anim_timer.stop()
            self.flowgraph.stop()
            self.flowgraph.wait()
        except Exception:
            pass
        event.accept()
