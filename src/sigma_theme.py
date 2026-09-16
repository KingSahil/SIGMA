"""
SIGMA - Signal Intelligence & Generalized Modulation Analyzer
Big, Modern, Google Stitch / Material Design 3 Dark Theme
Spacious, highly readable, large touch targets, bold typography.
"""

COLORS = {
    # Surfaces
    "bg_main": "#0d1117",          # Deep slate workspace
    "bg_card": "#161b24",          # Large container card
    "bg_card_inner": "#1d2430",    # Nested stat / metric cell
    "bg_plot": "#10141d",          # Dark plot canvas
    "bg_accent_soft": "rgba(56, 189, 248, 0.12)",
    
    # Borders
    "border": "#273142",           # Soft modern border
    "border_light": "#364359",     # Hover border
    
    # Text
    "text_primary": "#f8fafc",     # Crisp bold white
    "text_secondary": "#94a3b8",   # Soft slate gray
    "text_muted": "#64748b",       # Subdued
    
    # Material / Google Stitch Accents
    "accent_primary": "#38bdf8",   # Google Sky Blue
    "accent_blue": "#60a5fa",      # Electric blue
    "accent_success": "#34d399",   # Fresh emerald green
    "accent_audio": "#f43f5e",     # Vibrant coral for audio playback
    "accent_audio_active": "#10b981", # Emerald when audio is playing
    "accent_warn": "#fbbf24",      # Amber
    "accent_i": "#38bdf8",         # In-Phase I (Cyan)
    "accent_q": "#f472b6",         # Quadrature Q (Rose/Magenta)
}

BIG_MATERIAL_QSS = f"""
/* =========================================================================
   SIGMA — BIG, SPACIOUS, MODERN GOOGLE STITCH UI
   ========================================================================= */

QMainWindow, QWidget#CentralWidget {{
    background-color: {COLORS['bg_main']};
    color: {COLORS['text_primary']};
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Inter", "Roboto", sans-serif;
    font-size: 14px;
}}

/* Main Big Cards */
QFrame.SigmaBigCard {{
    background-color: {COLORS['bg_card']};
    border: 1px solid {COLORS['border']};
    border-radius: 12px;
    padding: 10px 14px;
}}

/* Section Titles (Big, Clean, Readable) */
QLabel.SectionTitle {{
    font-size: 11px;
    font-weight: 800;
    color: {COLORS['accent_primary']};
    letter-spacing: 1.2px;
    text-transform: uppercase;
}}

/* High-Contrast Floating HUD Overlay Badge for Plot Inspection */
QLabel.HudOverlayBadge {{
    background-color: #0b0f17;
    border: 1px solid #273142;
    border-radius: 6px;
    color: {COLORS['accent_primary']};
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 11px;
    font-weight: 700;
    padding: 3px 10px;
}}
QLabel.HudOverlayBadge:hover {{
    border-color: {COLORS['accent_primary']};
    background-color: #111722;
}}

/* Header Typography */
QLabel.AppTitle {{
    font-size: 24px;
    font-weight: 900;
    color: {COLORS['text_primary']};
    letter-spacing: 1.5px;
}}

QLabel.AppSubtitle {{
    font-size: 12px;
    color: {COLORS['text_secondary']};
    letter-spacing: 0.4px;
}}


/* Big Tactile Buttons (Google Material Style) */
QPushButton {{
    background-color: {COLORS['bg_card_inner']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border_light']};
    border-radius: 8px;
    padding: 7px 16px;
    font-size: 13px;
    font-weight: 700;
}}

QPushButton:hover {{
    background-color: #273042;
    border-color: {COLORS['accent_primary']};
    color: #ffffff;
}}

QPushButton:pressed {{
    background-color: {COLORS['bg_plot']};
}}

QPushButton.PrimaryBtn {{
    background-color: {COLORS['accent_primary']};
    color: #0b111a;
    border: none;
    border-radius: 8px;
    padding: 7px 18px;
    font-weight: 800;
}}

QPushButton.PrimaryBtn:hover {{
    background-color: #60cdfa;
    color: #000000;
}}

/* View Mode Selector Segmented Buttons */
QPushButton.ViewToggleBtn {{
    background-color: {COLORS['bg_card_inner']};
    color: {COLORS['text_secondary']};
    border: 1px solid {COLORS['border']};
    border-radius: 7px;
    padding: 5px 12px;
    font-size: 11px;
    font-weight: 700;
}}

QPushButton.ViewToggleBtn:hover {{
    background-color: #222b3a;
    color: #ffffff;
    border-color: {COLORS['accent_primary']};
}}

QPushButton.ViewToggleBtnActive {{
    background-color: rgba(56, 189, 248, 0.18);
    color: {COLORS['accent_primary']};
    border: 1.5px solid {COLORS['accent_primary']};
    border-radius: 7px;
    padding: 5px 12px;
    font-size: 11px;
    font-weight: 800;
}}

/* Audio Playback Button (Special Large Accent) */
QPushButton.AudioBtnIdle {{
    background-color: rgba(244, 63, 94, 0.15);
    color: #fb7185;
    border: 1.5px solid rgba(244, 63, 94, 0.45);
    border-radius: 8px;
    padding: 7px 16px;
    font-size: 13px;
    font-weight: 800;
}}

QPushButton.AudioBtnIdle:hover {{
    background-color: rgba(244, 63, 94, 0.3);
    color: #ffffff;
    border-color: #f43f5e;
}}

QPushButton.AudioBtnPlaying {{
    background-color: rgba(52, 211, 153, 0.25);
    color: #34d399;
    border: 1.5px solid #34d399;
    border-radius: 8px;
    padding: 7px 16px;
    font-size: 13px;
    font-weight: 800;
}}

QPushButton.AudioBtnPlaying:hover {{
    background-color: rgba(52, 211, 153, 0.4);
    color: #ffffff;
}}

/* File Display (Big & Prominent) */
QLabel.FileName {{
    font-size: 17px;
    font-weight: 800;
    color: {COLORS['accent_primary']};
    font-family: "Consolas", monospace;
}}

QLabel.FileDetailBadge {{
    background-color: {COLORS['bg_card_inner']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 600;
    color: {COLORS['text_secondary']};
}}

/* Big Metric Cards (Massive readability) */
QFrame.BigMetricCell {{
    background-color: {COLORS['bg_card_inner']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 6px 10px;
}}

QFrame.BigMetricCell:hover {{
    border-color: {COLORS['border_light']};
}}

QLabel.BigMetricLabel {{
    font-size: 10px;
    font-weight: 700;
    color: {COLORS['text_secondary']};
    letter-spacing: 0.6px;
    text-transform: uppercase;
}}

QLabel.BigMetricValue {{
    font-family: "Consolas", "JetBrains Mono", monospace;
    font-size: 16px;
    font-weight: 800;
    color: {COLORS['text_primary']};
}}

QLabel.BigMetricValueHighlight {{
    font-family: "Consolas", "JetBrains Mono", monospace;
    font-size: 16px;
    font-weight: 800;
    color: {COLORS['accent_primary']};
}}

/* Big Modulation Card */
QFrame.BigModulationBox {{
    background-color: {COLORS['bg_card_inner']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 8px 12px;
}}

QLabel.BigModulationState {{
    font-size: 18px;
    font-weight: 900;
    color: {COLORS['accent_warn']};
    letter-spacing: 0.5px;
}}

QLabel.BigModulationConfidence {{
    font-size: 12px;
    color: {COLORS['text_secondary']};
    font-family: "Consolas", monospace;
    font-weight: 600;
}}

/* Bottom Big Pipeline Stepper */
QFrame.BigPipelineBar {{
    background-color: {COLORS['bg_card']};
    border: 1px solid {COLORS['border']};
    border-radius: 12px;
    padding: 10px 20px;
}}

QLabel.BigPipelineStepDone {{
    color: {COLORS['accent_success']};
    font-size: 13px;
    font-weight: 800;
    letter-spacing: 0.5px;
}}

QLabel.BigPipelineStepPending {{
    color: {COLORS['text_muted']};
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.5px;
}}

QLabel.BigPipelineArrow {{
    color: {COLORS['border_light']};
    font-size: 16px;
    font-weight: bold;
    padding: 0 10px;
}}

/* Dialog & Input fields */
QDialog {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['text_primary']};
}}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background-color: {COLORS['bg_plot']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border_light']};
    border-radius: 8px;
    padding: 8px 12px;
    font-family: "Consolas", monospace;
    font-size: 14px;
}}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border-color: {COLORS['accent_primary']};
}}

/* Splitter */
QSplitter::handle {{
    background-color: {COLORS['bg_main']};
    height: 10px;
}}

QSplitter::handle:hover {{
    background-color: {COLORS['accent_primary']};
}}

/* ScrollArea and Sleek Modern Scrollbars */
QScrollArea {{
    background-color: transparent;
    border: none;
}}

QScrollBar:vertical {{
    background-color: {COLORS['bg_main']};
    width: 8px;
    margin: 0px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical {{
    background-color: {COLORS['border']};
    min-height: 30px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {COLORS['accent_primary']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background-color: {COLORS['bg_main']};
    height: 8px;
    margin: 0px;
    border-radius: 4px;
}}

QScrollBar::handle:horizontal {{
    background-color: {COLORS['border']};
    min-width: 30px;
    border-radius: 4px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {COLORS['accent_primary']};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}
"""

MAIN_QSS = BIG_MATERIAL_QSS


def create_sigma_icon():
    """Generates a modern, high-resolution SIGMA brand icon."""
    try:
        from PyQt5 import QtGui, QtCore
        icon = QtGui.QIcon()
        for size in (16, 24, 32, 48, 64, 128, 256):
            pix = QtGui.QPixmap(size, size)
            pix.fill(QtCore.Qt.transparent)
            p = QtGui.QPainter(pix)
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            # Rounded background tile
            p.setBrush(QtGui.QBrush(QtGui.QColor("#10141d")))
            pen_w = max(1.0, size / 32.0)
            p.setPen(QtGui.QPen(QtGui.QColor("#38bdf8"), pen_w))
            radius = max(2.0, size * 0.22)
            margin = max(1.0, size * 0.04)
            p.drawRoundedRect(QtCore.QRectF(margin, margin, size - 2 * margin, size - 2 * margin), radius, radius)
            # Greek letter Sigma (bold electric blue)
            font = QtGui.QFont("Segoe UI", int(size * 0.52), QtGui.QFont.Bold)
            p.setFont(font)
            p.setPen(QtGui.QColor("#38bdf8"))
            p.drawText(QtCore.QRectF(0, 0, size, size), QtCore.Qt.AlignCenter, "Σ")
            p.end()
            icon.addPixmap(pix)
        return icon
    except Exception:
        from PyQt5 import QtGui
        return QtGui.QIcon()
