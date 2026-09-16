"""
SIGMA - Signal Intelligence & Generalized Modulation Analyzer
GNU Radio Flowgraph Module (gr.top_block wrapper)
Preserves the exact DSP pipeline with FL Studio DAW dark-theme styling.
"""

import os
import sys
import threading
from PyQt5 import Qt, QtCore, QtGui, QtWidgets
import sip

from gnuradio import gr
from gnuradio import blocks
from gnuradio import qtgui
from gnuradio.fft import window
from gnuradio.filter import firdes
import pmt


def apply_fl_studio_sink_theme(widget):
    """Recursively styles GNU Radio QtGUI / Qwt widgets to match FL Studio aesthetics."""
    if not widget:
        return
    for child in widget.findChildren(QtWidgets.QWidget):
        cname = child.metaObject().className()
        if "PlotCanvas" in cname or "DisplayPlot" in cname:
            child.setStyleSheet("background-color: #15181d; border: 1px solid #282f37; border-radius: 3px;")
            pal = child.palette()
            pal.setColor(QtGui.QPalette.Window, QtGui.QColor("#15181d"))
            pal.setColor(QtGui.QPalette.Base, QtGui.QColor("#15181d"))
            child.setPalette(pal)
        elif "Scale" in cname:
            pal = child.palette()
            pal.setColor(QtGui.QPalette.WindowText, QtGui.QColor("#8e9aa8"))
            pal.setColor(QtGui.QPalette.Text, QtGui.QColor("#8e9aa8"))
            child.setPalette(pal)
            child.setStyleSheet("color: #8e9aa8; font-family: 'Consolas', monospace; font-size: 10px;")
        elif "TextLabel" in cname:
            child.setStyleSheet("color: #cfd8dc; font-weight: 700; background: transparent; font-size: 11px;")
        elif "Legend" in cname:
            child.setStyleSheet("background-color: #191d23; color: #b0bec5; border: 1px solid #2c343f; border-radius: 2px;")


class SigmaFlowgraph(gr.top_block):
    """
    Encapsulates the GNU Radio signal processing graph.
    Exposes real PyQt5 widgets for Time Domain, Frequency Spectrum, and Constellation.
    """

    def __init__(self, filepath="signal.iq", samp_rate=1000000, center_freq=0.0, repeat=True):
        super().__init__("SIGMA Flowgraph", catch_exceptions=True)

        self.filepath = filepath
        self.samp_rate = samp_rate
        self.center_freq = center_freq
        self.repeat = repeat
        self.flowgraph_started = threading.Event()

        ##################################################
        # 1. Blocks Initialization
        ##################################################
        # Time Sink (Complex IQ)
        self.time_sink = qtgui.time_sink_c(
            1024,                # Buffer size
            self.samp_rate,      # Sample rate
            "WAVE CANDY — TIME DOMAIN (I / Q)",    # Title
            1,                   # Inputs
            None                 # Parent
        )
        self.time_sink.set_update_time(0.05)
        self.time_sink.set_y_axis(-1.5, 1.5)
        self.time_sink.set_y_label("Amplitude", "")
        self.time_sink.enable_tags(True)
        self.time_sink.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.time_sink.enable_autoscale(True)
        self.time_sink.enable_grid(True)
        self.time_sink.enable_axis_labels(True)
        self.time_sink.enable_control_panel(False)
        self.time_sink.enable_stem_plot(False)

        # Labels for I (FL Cyan) and Q (FL Magenta)
        self.time_sink.set_line_label(0, "I (In-Phase)")
        self.time_sink.set_line_color(0, "cyan")
        self.time_sink.set_line_width(0, 1)

        self.time_sink.set_line_label(1, "Q (Quadrature)")
        self.time_sink.set_line_color(1, "magenta")
        self.time_sink.set_line_width(1, 1)

        # Frequency Sink (FFT / Spectrum)
        self.freq_sink = qtgui.freq_sink_c(
            1024,                        # FFT size
            window.WIN_BLACKMAN_hARRIS,  # Window type
            self.center_freq,            # Center frequency
            self.samp_rate,              # Bandwidth
            "FRUITY PARAMETRIC — SPECTRUM / PSD",  # Title
            1,                           # Inputs
            None                         # Parent
        )
        self.freq_sink.set_update_time(0.05)
        self.freq_sink.set_y_axis(-140, 10)
        self.freq_sink.set_y_label("Relative Gain", "dB")
        self.freq_sink.set_trigger_mode(qtgui.TRIG_MODE_FREE, 0.0, 0, "")
        self.freq_sink.enable_autoscale(True)
        self.freq_sink.enable_grid(True)
        self.freq_sink.set_fft_average(0.2)
        self.freq_sink.enable_axis_labels(True)
        self.freq_sink.enable_control_panel(False)
        self.freq_sink.set_fft_window_normalized(False)
        self.freq_sink.set_line_label(0, "IQ Spectrum")
        self.freq_sink.set_line_color(0, "green")
        self.freq_sink.set_line_width(0, 1)

        # Constellation Sink
        self.constellation_sink = qtgui.const_sink_c(
            1024,             # Display size
            "VECTOR SCOPE — CONSTELLATION",  # Title
            1,                # Inputs
            None              # Parent
        )
        self.constellation_sink.set_update_time(0.05)
        self.constellation_sink.set_y_axis(-2, 2)
        self.constellation_sink.set_x_axis(-2, 2)
        self.constellation_sink.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, "")
        self.constellation_sink.enable_autoscale(True)
        self.constellation_sink.enable_grid(True)
        self.constellation_sink.enable_axis_labels(True)
        self.constellation_sink.disable_legend()
        self.constellation_sink.set_line_label(0, "IQ Samples")
        self.constellation_sink.set_line_color(0, "cyan")
        self.constellation_sink.set_line_marker(0, 0)
        self.constellation_sink.set_line_width(0, 1)

        # Convert to QWidget instances
        self.time_sink_widget = sip.wrapinstance(self.time_sink.qwidget(), Qt.QWidget)
        self.freq_sink_widget = sip.wrapinstance(self.freq_sink.qwidget(), Qt.QWidget)
        self.const_sink_widget = sip.wrapinstance(self.constellation_sink.qwidget(), Qt.QWidget)

        # Apply FL Studio styling to the sinks
        apply_fl_studio_sink_theme(self.time_sink_widget)
        apply_fl_studio_sink_theme(self.freq_sink_widget)
        apply_fl_studio_sink_theme(self.const_sink_widget)

        ##################################################
        # 2. File Source & Connections
        ##################################################
        self.file_source = None
        self._build_pipeline()

    def _build_pipeline(self):
        """Creates or updates the file source and connects it to the 3 sinks."""
        safe_path = self.filepath if (self.filepath and os.path.exists(self.filepath)) else "signal.iq"

        if os.path.exists(safe_path):
            self.file_source = blocks.file_source(gr.sizeof_gr_complex * 1, safe_path, self.repeat, 0, 0)
            self.file_source.set_begin_tag(pmt.PMT_NIL)
            self.connect((self.file_source, 0), (self.time_sink, 0))
            self.connect((self.file_source, 0), (self.freq_sink, 0))
            self.connect((self.file_source, 0), (self.constellation_sink, 0))
        else:
            print(f"[SIGMA DSP] Warning: File not found at {safe_path}. Flowgraph initialized idle.")

    def set_samp_rate(self, samp_rate):
        """Updates sample rate across all sinks."""
        self.samp_rate = samp_rate
        self.time_sink.set_samp_rate(self.samp_rate)
        self.freq_sink.set_frequency_range(self.center_freq, self.samp_rate)

    def set_center_freq(self, center_freq):
        """Updates center frequency for frequency sink."""
        self.center_freq = center_freq
        self.freq_sink.set_frequency_range(self.center_freq, self.samp_rate)

    def reload_file(self, filepath, repeat=True):
        """Safely reloads a new IQ file into the running flowgraph."""
        if not os.path.exists(filepath):
            return False

        try:
            self.lock()
            self.disconnect((self.file_source, 0), (self.time_sink, 0))
            self.disconnect((self.file_source, 0), (self.freq_sink, 0))
            self.disconnect((self.file_source, 0), (self.constellation_sink, 0))

            self.filepath = filepath
            self.repeat = repeat
            self.file_source = blocks.file_source(gr.sizeof_gr_complex * 1, filepath, self.repeat, 0, 0)
            self.file_source.set_begin_tag(pmt.PMT_NIL)

            self.connect((self.file_source, 0), (self.time_sink, 0))
            self.connect((self.file_source, 0), (self.freq_sink, 0))
            self.connect((self.file_source, 0), (self.constellation_sink, 0))
            self.unlock()
            return True
        except Exception as e:
            print(f"[SIGMA DSP] Error reloading file: {e}")
            try:
                self.unlock()
            except Exception:
                pass
            return False
