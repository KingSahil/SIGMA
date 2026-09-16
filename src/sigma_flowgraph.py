"""
SIGMA - Signal Intelligence & Generalized Modulation Analyzer
GNU Radio Flowgraph Module (gr.top_block wrapper)
Clean, Minimal Signal Processing Pipeline
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


def apply_clean_sink_theme(widget):
    """Styles GNU Radio QtGUI / Qwt widgets with large, clear modern aesthetics."""
    if not widget:
        return
    for child in widget.findChildren(QtCore.QObject):
        cname = child.metaObject().className()
        if "Zoomer" in cname or "Picker" in cname:
            # Overwrite GNU Radio default dark red (#800000) tracker text & rubber band
            try:
                child.setProperty("trackerPen", QtGui.QPen(QtGui.QColor("#38bdf8"), 1))
                child.setProperty("trackerFont", QtGui.QFont("Consolas", 10, QtGui.QFont.Bold))
                child.setProperty("rubberBandPen", QtGui.QPen(QtGui.QColor("#38bdf8"), 2, QtCore.Qt.DashLine))
            except Exception:
                pass

        if isinstance(child, QtWidgets.QWidget):
            if "PlotCanvas" in cname:
                child.setStyleSheet("background-color: #10141d; border: 1px solid #273142; border-radius: 8px;")
                pal = child.palette()
                pal.setColor(QtGui.QPalette.Window, QtGui.QColor("#10141d"))
                pal.setColor(QtGui.QPalette.Base, QtGui.QColor("#10141d"))
                child.setPalette(pal)
            elif "DisplayPlot" in cname:
                child.setStyleSheet("background: transparent; border: none;")
            elif "Scale" in cname:
                pal = child.palette()
                pal.setColor(QtGui.QPalette.WindowText, QtGui.QColor("#94a3b8"))
                pal.setColor(QtGui.QPalette.Text, QtGui.QColor("#94a3b8"))
                child.setPalette(pal)
                child.setStyleSheet("background: transparent; border: none; color: #94a3b8; font-family: 'Consolas', monospace; font-size: 11px; font-weight: 600;")
            elif "TextLabel" in cname:
                child.setStyleSheet("color: #f8fafc; font-weight: 800; background: transparent; font-size: 12px;")
            elif "Legend" in cname:
                child.setStyleSheet("background-color: #161b24; color: #cbd5e1; border: 1px solid #273142; border-radius: 6px; padding: 2px 6px;")


class SigmaFlowgraph(gr.top_block):
    """
    Encapsulates the GNU Radio signal processing graph.
    Exposes clean PyQt5 widgets for Time Domain, Frequency Spectrum, and Constellation.
    """

    def __init__(self, filepath="signal.iq", samp_rate=1000000, center_freq=0.0, repeat=True):
        super().__init__("SIGMA Flowgraph", catch_exceptions=True)

        self.filepath = filepath
        self.samp_rate = samp_rate
        self.center_freq = center_freq
        self.repeat = repeat
        self.flowgraph_started = threading.Event()
        self._is_streaming = False
        self._preview_timer = None

        ##################################################
        # 1. Blocks Initialization
        ##################################################
        # Time Sink (Complex IQ)
        self.time_sink = qtgui.time_sink_c(
            1024,                # Buffer size
            self.samp_rate,      # Sample rate
            "",                  # Clean title
            1,                   # Inputs
            None                 # Parent
        )
        self.time_sink.set_update_time(0.05)
        self.time_sink.set_y_axis(-1.5, 1.5)
        self.time_sink.set_y_label("", "")
        self.time_sink.enable_tags(True)
        self.time_sink.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0.0, 0, "")
        self.time_sink.enable_autoscale(True)
        self.time_sink.enable_grid(True)
        self.time_sink.enable_axis_labels(False)
        self.time_sink.enable_control_panel(False)
        self.time_sink.enable_stem_plot(False)

        # Labels for I and Q
        self.time_sink.set_line_label(0, "I")
        self.time_sink.set_line_color(0, "cyan")
        self.time_sink.set_line_width(0, 1)

        self.time_sink.set_line_label(1, "Q")
        self.time_sink.set_line_color(1, "magenta")
        self.time_sink.set_line_width(1, 1)

        # Frequency Sink (FFT / Spectrum)
        self.freq_sink = qtgui.freq_sink_c(
            1024,                        # FFT size
            window.WIN_BLACKMAN_hARRIS,  # Window type
            self.center_freq,            # Center frequency
            self.samp_rate,              # Bandwidth
            "",                          # Clean title
            1,                           # Inputs
            None                         # Parent
        )
        self.freq_sink.set_update_time(0.05)
        self.freq_sink.set_y_axis(-140, 10)
        self.freq_sink.set_y_label("", "")
        self.freq_sink.set_trigger_mode(qtgui.TRIG_MODE_FREE, 0.0, 0, "")
        self.freq_sink.enable_autoscale(True)
        self.freq_sink.enable_grid(True)
        self.freq_sink.set_fft_average(0.2)
        self.freq_sink.enable_axis_labels(False)
        self.freq_sink.enable_control_panel(False)
        self.freq_sink.set_fft_window_normalized(False)
        self.freq_sink.set_line_label(0, "Spectrum")
        self.freq_sink.set_line_color(0, "cyan")
        self.freq_sink.set_line_width(0, 1)

        # Waterfall (Spectrogram) Sink
        self.waterfall_sink = qtgui.waterfall_sink_c(
            1024,                        # FFT size
            window.WIN_BLACKMAN_hARRIS,  # Window type
            self.center_freq,            # Center frequency
            self.samp_rate,              # Bandwidth
            "",                          # Clean title
            1,                           # Inputs
            None                         # Parent
        )
        self.waterfall_sink.set_update_time(0.05)
        self.waterfall_sink.enable_grid(False)
        self.waterfall_sink.enable_axis_labels(False)
        self.waterfall_sink.set_intensity_range(-140, 10)

        # Constellation Sink
        self.constellation_sink = qtgui.const_sink_c(
            1024,             # Display size
            "",               # Clean title
            1,                # Inputs
            None              # Parent
        )
        self.constellation_sink.set_update_time(0.05)
        self.constellation_sink.set_y_axis(-2, 2)
        self.constellation_sink.set_x_axis(-2, 2)
        self.constellation_sink.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, "")
        self.constellation_sink.enable_autoscale(True)
        self.constellation_sink.enable_grid(True)
        self.constellation_sink.enable_axis_labels(False)
        # Disable redundant legends to save vertical space (UI cards already have modern legends)
        self.time_sink.disable_legend()
        self.freq_sink.disable_legend()
        self.constellation_sink.disable_legend()
        self.constellation_sink.set_line_label(0, "Samples")
        self.constellation_sink.set_line_color(0, "cyan")
        self.constellation_sink.set_line_marker(0, 0)
        self.constellation_sink.set_line_width(0, 1)

        # Rate throttle block: Prevents CPU spinning at 380+ MSps and eliminates fread error on looping
        self.throttle = blocks.throttle(gr.sizeof_gr_complex, self.samp_rate)

        # Convert to QWidget instances
        self.time_sink_widget = sip.wrapinstance(self.time_sink.qwidget(), Qt.QWidget)
        self.freq_sink_widget = sip.wrapinstance(self.freq_sink.qwidget(), Qt.QWidget)
        self.waterfall_sink_widget = sip.wrapinstance(self.waterfall_sink.qwidget(), Qt.QWidget)
        self.const_sink_widget = sip.wrapinstance(self.constellation_sink.qwidget(), Qt.QWidget)

        # Allow widgets to shrink and grow responsively on any screen resolution
        for w in (self.time_sink_widget, self.freq_sink_widget, self.waterfall_sink_widget, self.const_sink_widget):
            w.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
            w.setMinimumSize(160, 130)

        # Apply Clean Theme to sinks
        apply_clean_sink_theme(self.time_sink_widget)
        apply_clean_sink_theme(self.freq_sink_widget)
        apply_clean_sink_theme(self.waterfall_sink_widget)
        apply_clean_sink_theme(self.const_sink_widget)

        ##################################################
        # 2. File Source & Connections
        ##################################################
        self.file_source = None
        self._build_pipeline()

    def _build_pipeline(self):
        """Creates the file source, passes through throttle, and connects to sinks."""
        safe_path = self.filepath
        if not safe_path or not os.path.exists(safe_path):
            candidates = [
                "data/iq/signal.iq",
                "data/signal.iq",
                "signal.iq",
                os.path.join(os.path.dirname(__file__), "..", "data", "iq", "signal.iq"),
                os.path.join(os.path.dirname(__file__), "..", "data", "signal.iq"),
                os.path.join(os.path.dirname(__file__), "..", "signal.iq"),
            ]
            for c in candidates:
                if os.path.exists(c):
                    safe_path = os.path.abspath(c)
                    break

        # Wire sinks to the throttle output
        self.connect((self.throttle, 0), (self.time_sink, 0))
        self.connect((self.throttle, 0), (self.freq_sink, 0))
        self.connect((self.throttle, 0), (self.waterfall_sink, 0))
        self.connect((self.throttle, 0), (self.constellation_sink, 0))

        if safe_path and os.path.exists(safe_path):
            self.file_source = blocks.file_source(gr.sizeof_gr_complex * 1, safe_path, self.repeat, 0, 0)
            self.file_source.set_begin_tag(pmt.PMT_NIL)
            self.connect((self.file_source, 0), (self.throttle, 0))
        else:
            print(f"[SIGMA DSP] Warning: File not found at {safe_path}. Flowgraph initialized idle.")

    def set_samp_rate(self, samp_rate):
        """Updates sample rate across throttle and all sinks."""
        self.samp_rate = samp_rate
        try:
            self.throttle.set_sample_rate(self.samp_rate)
        except Exception:
            pass
        self.time_sink.set_samp_rate(self.samp_rate)
        self.freq_sink.set_frequency_range(self.center_freq, self.samp_rate)
        self.waterfall_sink.set_frequency_range(self.center_freq, self.samp_rate)

    def set_center_freq(self, center_freq):
        """Updates center frequency for frequency and waterfall sinks."""
        self.center_freq = center_freq
        self.freq_sink.set_frequency_range(self.center_freq, self.samp_rate)
        self.waterfall_sink.set_frequency_range(self.center_freq, self.samp_rate)

    def reload_file(self, filepath, repeat=True):
        """Safely reloads a new IQ file into the flowgraph."""
        if not os.path.exists(filepath):
            return False

        if self._preview_timer is not None:
            self._preview_timer.stop()
            self._preview_timer = None

        was_streaming = self._is_streaming
        if was_streaming:
            self.stop()
            self.wait()
            self._is_streaming = False

        try:
            if self.file_source is not None:
                try:
                    self.disconnect((self.file_source, 0), (self.throttle, 0))
                except Exception:
                    pass

            self.filepath = filepath
            self.repeat = repeat
            self.file_source = blocks.file_source(gr.sizeof_gr_complex * 1, filepath, self.repeat, 0, 0)
            self.file_source.set_begin_tag(pmt.PMT_NIL)

            self.connect((self.file_source, 0), (self.throttle, 0))

            if was_streaming:
                self.start()
                self._is_streaming = True
            return True
        except Exception as e:
            print(f"[SIGMA DSP] Error reloading file: {e}")
            return False

    def start_waves(self, rewind=False):
        """Starts or resumes streaming signal samples to animate visual plots."""
        if self._preview_timer is not None:
            self._preview_timer.stop()
            self._preview_timer = None

        if rewind and self.file_source is not None:
            try:
                self.file_source.seek(0, 0)
            except Exception:
                pass

        if not self._is_streaming:
            try:
                self.start()
                self._is_streaming = True
                self.flowgraph_started.set()
            except Exception as e:
                print(f"[SIGMA DSP] Error starting wave stream: {e}")

    def stop_waves(self):
        """Stops streaming signal samples, freezing the visual wave plots."""
        if self._preview_timer is not None:
            self._preview_timer.stop()
            self._preview_timer = None

        if self._is_streaming:
            try:
                self.stop()
                self.wait()
                self._is_streaming = False
            except Exception as e:
                print(f"[SIGMA DSP] Error stopping wave stream: {e}")

    def capture_preview(self, duration_sec=0.15):
        """Streams a brief burst of samples to paint initial plots, then freezes."""
        if self._preview_timer is not None:
            self._preview_timer.stop()

        self.start_waves(rewind=True)
        self._preview_timer = QtCore.QTimer()
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self._on_preview_timeout)
        self._preview_timer.start(int(duration_sec * 1000))

    def _on_preview_timeout(self):
        self._preview_timer = None
        self.stop_waves()

    @property
    def is_streaming(self):
        return self._is_streaming

