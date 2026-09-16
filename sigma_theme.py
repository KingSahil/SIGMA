"""
SIGMA - Signal Intelligence & Generalized Modulation Analyzer
FL Studio Inspired DAW / SDR Theme and Styling System (QSS)
"""

# FL Studio signature color palette
COLORS = {
    # Backgrounds
    "bg_main": "#1e2227",          # FL Studio main workspace gunmetal
    "bg_window": "#272d35",        # FL Studio window/panel background
    "bg_window_header": "#313842", # FL Studio window title bar
    "bg_surface_dark": "#16191d",  # Recessed LCD displays, mixer wells, plot canvases
    "bg_rack": "#20252b",          # Channel rack & mixer background
    "bg_track_header": "#2b323b",  # Track header background
    
    # Borders & Dividers
    "border_dark": "#15181b",
    "border": "#353d48",           # Standard panel border
    "border_light": "#444f5e",     # Bevel highlight border
    "border_focus": "#ff9800",     # FL Studio orange selection/focus
    
    # Typography
    "text_primary": "#e1e7ec",     # Crisp bright text
    "text_secondary": "#9aa6b2",   # Slate label text
    "text_muted": "#606d7b",       # Disabled / muted text
    "text_lcd": "#39ff14",         # Neon lime green LCD display
    "text_lcd_amber": "#ffaa00",   # Amber digital readout
    "text_lcd_cyan": "#00f0ff",    # Cyan digital readout
    
    # FL Studio Signature Channel / Track Pastels & Neons
    "fl_lime": "#4ced7a",          # Audio / Time domain / Play
    "fl_cyan": "#00e5ff",          # In-Phase (I) / FFT Peak
    "fl_magenta": "#ff2d87",       # Quadrature (Q) / Synth
    "fl_orange": "#ff8c00",        # Transport / Pattern / Loop
    "fl_amber": "#ffb703",         # Confidence / Warning / Caution
    "fl_purple": "#9d5b8f",        # Track purple / Modulation
    "fl_blue": "#3a86ff",          # Secondary channel / DSP
    "fl_red": "#ff4757",           # Stop / Clip / Peak overload
    "fl_sage": "#589c74",          # Percussion / Input
    "fl_violet": "#7b4f8d",        # Ambience / Advanced
    "fl_brown": "#a8784d",         # Bass / RF Channel
}

FL_STUDIO_QSS = f"""
/* =========================================================================
   FL STUDIO MASTER THEME
   ========================================================================= */

QMainWindow, QWidget#CentralWidget {{
    background-color: {COLORS['bg_main']};
    color: {COLORS['text_primary']};
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, "Roboto", sans-serif;
    font-size: 12px;
}}

/* Top Menu Bar */
QMenuBar {{
    background-color: {COLORS['bg_window_header']};
    color: {COLORS['text_secondary']};
    border-bottom: 1px solid {COLORS['border_dark']};
    padding: 2px 6px;
    font-weight: 600;
    font-size: 11px;
    letter-spacing: 0.8px;
}}

QMenuBar::item {{
    background: transparent;
    padding: 3px 10px;
    border-radius: 2px;
}}

QMenuBar::item:selected {{
    background-color: {COLORS['border_light']};
    color: #ffffff;
}}

QMenu {{
    background-color: {COLORS['bg_window']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border_light']};
    padding: 4px;
}}

QMenu::item {{
    padding: 5px 22px 5px 14px;
    border-radius: 2px;
}}

QMenu::item:selected {{
    background-color: {COLORS['fl_orange']};
    color: #000000;
    font-weight: bold;
}}

/* FL Studio Window / Dock Panel Container */
QFrame.FLWindow {{
    background-color: {COLORS['bg_window']};
    border: 1px solid {COLORS['border']};
    border-top: 1px solid {COLORS['border_light']};
    border-radius: 5px;
}}

/* FL Studio Window Header */
QFrame.FLWindowHeader {{
    background-color: {COLORS['bg_window_header']};
    border-bottom: 1px solid {COLORS['border_dark']};
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    padding: 3px 8px;
    min-height: 22px;
}}

QLabel.FLWindowTitle {{
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.8px;
    color: {COLORS['text_primary']};
    text-transform: uppercase;
}}

QLabel.FLWindowBadge {{
    font-size: 9px;
    font-weight: 700;
    color: #ffffff;
    border-radius: 2px;
    padding: 1px 5px;
}}

/* Digital LCD Display Boxes */
QFrame.FLLcdBox {{
    background-color: {COLORS['bg_surface_dark']};
    border: 1px solid {COLORS['border_dark']};
    border-top: 1px solid #0d0f12;
    border-radius: 4px;
    padding: 4px 8px;
}}

QLabel.FLLcdLabel {{
    font-size: 9px;
    font-weight: 700;
    color: {COLORS['text_secondary']};
    letter-spacing: 0.8px;
    text-transform: uppercase;
}}

QLabel.FLLcdValue {{
    font-family: "Consolas", "Courier New", monospace;
    font-size: 14px;
    font-weight: 700;
    color: {COLORS['text_lcd']};
    letter-spacing: 1px;
}}

QLabel.FLLcdValueAmber {{
    font-family: "Consolas", "Courier New", monospace;
    font-size: 14px;
    font-weight: 700;
    color: {COLORS['text_lcd_amber']};
    letter-spacing: 1px;
}}

QLabel.FLLcdValueCyan {{
    font-family: "Consolas", "Courier New", monospace;
    font-size: 14px;
    font-weight: 700;
    color: {COLORS['text_lcd_cyan']};
    letter-spacing: 1px;
}}

/* FL Studio Track Headers & Channel Rack Cards */
QFrame.FLTrackCard {{
    background-color: {COLORS['bg_rack']};
    border: 1px solid {COLORS['border']};
    border-radius: 3px;
    padding: 4px 6px;
}}

QFrame.FLTrackCard:hover {{
    border-color: {COLORS['border_light']};
    background-color: #242a32;
}}

QLabel.FLTrackLabel {{
    font-size: 9px;
    font-weight: 700;
    color: {COLORS['text_secondary']};
    letter-spacing: 0.5px;
    text-transform: uppercase;
}}

QLabel.FLTrackValue {{
    font-size: 12px;
    font-weight: 700;
    color: {COLORS['text_primary']};
    font-family: "Consolas", monospace;
}}

/* FL Studio Transport Buttons */
QPushButton.FLTransportBtn {{
    background-color: {COLORS['bg_window_header']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border_light']};
    border-bottom: 2px solid {COLORS['border_dark']};
    border-radius: 3px;
    padding: 5px 12px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
}}

QPushButton.FLTransportBtn:hover {{
    background-color: #3b4450;
    border-color: {COLORS['fl_orange']};
    color: #ffffff;
}}

QPushButton.FLTransportBtn:pressed {{
    background-color: {COLORS['bg_surface_dark']};
    border-top: 2px solid {COLORS['border_dark']};
    border-bottom: 1px solid {COLORS['border_light']};
}}

QPushButton.FLPlayActive {{
    background-color: rgba(76, 237, 122, 0.2);
    color: {COLORS['fl_lime']};
    border: 1px solid {COLORS['fl_lime']};
    border-bottom: 2px solid #237b3e;
}}

QPushButton.FLPlayActive:hover {{
    background-color: rgba(76, 237, 122, 0.35);
    color: #ffffff;
}}

QPushButton.FLStopActive {{
    background-color: rgba(255, 71, 87, 0.2);
    color: {COLORS['fl_red']};
    border: 1px solid {COLORS['fl_red']};
    border-bottom: 2px solid #8b1822;
}}

QPushButton.FLActionBtn {{
    background-color: {COLORS['bg_window_header']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border_light']};
    border-radius: 3px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 600;
}}

QPushButton.FLActionBtn:hover {{
    background-color: #38414e;
    border-color: {COLORS['fl_cyan']};
    color: {COLORS['fl_cyan']};
}}

/* Channel Rack Mute / LED Pill */
QLabel.FLLedOnline {{
    background-color: {COLORS['fl_lime']};
    color: #0d1e11;
    font-size: 10px;
    font-weight: 800;
    border-radius: 3px;
    padding: 3px 8px;
    letter-spacing: 0.5px;
}}

QLabel.FLLedOffline {{
    background-color: #444c56;
    color: #9aa6b2;
    font-size: 10px;
    font-weight: 800;
    border-radius: 3px;
    padding: 3px 8px;
    letter-spacing: 0.5px;
}}

/* Form Controls */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background-color: {COLORS['bg_surface_dark']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 3px;
    padding: 4px 6px;
    font-family: "Consolas", monospace;
    font-size: 11px;
}}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border: 1px solid {COLORS['fl_orange']};
}}

/* ScrollBars */
QScrollBar:vertical {{
    border: none;
    background: {COLORS['bg_surface_dark']};
    width: 8px;
    margin: 0px;
}}

QScrollBar::handle:vertical {{
    background: {COLORS['border_light']};
    min-height: 20px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background: {COLORS['fl_orange']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    border: none;
    background: {COLORS['bg_surface_dark']};
    height: 8px;
    margin: 0px;
}}

QScrollBar::handle:horizontal {{
    background: {COLORS['border_light']};
    min-width: 20px;
    border-radius: 4px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {COLORS['fl_orange']};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* Splitters */
QSplitter::handle {{
    background-color: {COLORS['border_dark']};
}}

QSplitter::handle:hover {{
    background-color: {COLORS['fl_orange']};
}}
"""

# Backwards compatibility alias
MAIN_QSS = FL_STUDIO_QSS
