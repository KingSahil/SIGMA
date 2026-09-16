"""
SIGMA - Signal Intelligence & Generalized Modulation Analyzer
FL Studio Aesthetic — Clean, Minimal, Slate-Charcoal Dark Theme
"""

COLORS = {
    # FL Studio Authentic Slate & Charcoal Palette
    "bg_main": "#1f242a",          # FL Studio main workspace background
    "bg_card": "#272f38",          # FL Studio panel / window background
    "bg_card_header": "#2f3844",   # FL Studio header tone
    "bg_surface_dark": "#161a1f",  # FL Studio recessed well / plot canvas
    "bg_cell": "#1e242b",          # Metric cell background
    
    # Borders
    "border": "#35404e",           # Subtle slate border
    "border_light": "#435163",     # Border hover / divider
    "border_dark": "#14171b",      # Inset shadow line
    
    # Text
    "text_primary": "#e6edf3",     # Crisp text
    "text_secondary": "#95a3b3",   # Muted slate labels
    "text_muted": "#5d6a79",       # Subdued / pending
    
    # FL Studio Signature Accent Colors
    "fl_lime": "#54db54",          # FL Green (Active LED / Analysis)
    "fl_cyan": "#00d2ff",          # In-Phase I / Peak Frequency
    "fl_magenta": "#e056fd",       # Quadrature Q
    "fl_orange": "#ff9f1c",        # Amber / Modulation / Highlight
}

FL_CLEAN_QSS = f"""
/* =========================================================================
   SIGMA - FL STUDIO AESTHETIC THEME (CLEAN & MINIMAL)
   ========================================================================= */

QMainWindow, QWidget#CentralWidget {{
    background-color: {COLORS['bg_main']};
    color: {COLORS['text_primary']};
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", sans-serif;
    font-size: 12px;
}}

/* Cards & Panels */
QFrame.SigmaCard {{
    background-color: {COLORS['bg_card']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
}}

/* Card Header Strip */
QFrame.CardHeader {{
    background-color: {COLORS['bg_card_header']};
    border-bottom: 1px solid {COLORS['border']};
    border-top-left-radius: 3px;
    border-top-right-radius: 3px;
    padding: 5px 12px;
}}

QLabel.SectionTitle {{
    font-size: 11px;
    font-weight: 700;
    color: {COLORS['text_primary']};
    letter-spacing: 0.8px;
    text-transform: uppercase;
}}

/* Header Typography */
QLabel.AppTitle {{
    font-size: 20px;
    font-weight: 800;
    color: {COLORS['text_primary']};
    letter-spacing: 1.5px;
}}

QLabel.AppSubtitle {{
    font-size: 11px;
    color: {COLORS['text_secondary']};
    letter-spacing: 0.3px;
}}

/* Status Indicator */
QLabel.StatusAnalyzing {{
    background-color: rgba(84, 219, 84, 0.15);
    color: {COLORS['fl_lime']};
    border: 1px solid rgba(84, 219, 84, 0.4);
    border-radius: 12px;
    padding: 3px 12px;
    font-size: 11px;
    font-weight: 700;
}}

QLabel.StatusReady {{
    background-color: rgba(149, 163, 179, 0.15);
    color: {COLORS['text_secondary']};
    border: 1px solid {COLORS['border']};
    border-radius: 12px;
    padding: 3px 12px;
    font-size: 11px;
    font-weight: 600;
}}

/* FL Studio Tactile Buttons */
QPushButton {{
    background-color: #2c3540;
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border_light']};
    border-bottom: 2px solid {COLORS['border_dark']};
    border-radius: 3px;
    padding: 5px 14px;
    font-size: 11px;
    font-weight: 700;
}}

QPushButton:hover {{
    background-color: #374250;
    border-color: {COLORS['fl_cyan']};
    color: #ffffff;
}}

QPushButton:pressed {{
    background-color: {COLORS['bg_surface_dark']};
    border-top: 2px solid {COLORS['border_dark']};
    border-bottom: 1px solid {COLORS['border_light']};
}}

QPushButton.PrimaryBtn {{
    background-color: rgba(0, 210, 255, 0.14);
    color: {COLORS['fl_cyan']};
    border: 1px solid {COLORS['fl_cyan']};
    border-bottom: 2px solid #006680;
}}

QPushButton.PrimaryBtn:hover {{
    background-color: rgba(0, 210, 255, 0.28);
    color: #ffffff;
}}

/* Input Section Details */
QLabel.FileName {{
    font-size: 15px;
    font-weight: 700;
    color: {COLORS['fl_cyan']};
    font-family: "Consolas", monospace;
}}

QLabel.FileDetailText {{
    font-size: 11px;
    color: {COLORS['text_secondary']};
}}

/* Metric Cells */
QFrame.MetricCell {{
    background-color: {COLORS['bg_cell']};
    border: 1px solid {COLORS['border']};
    border-radius: 3px;
    padding: 6px 10px;
}}

QFrame.MetricCell:hover {{
    border-color: {COLORS['border_light']};
}}

QLabel.MetricLabel {{
    font-size: 9px;
    font-weight: 700;
    color: {COLORS['text_secondary']};
    letter-spacing: 0.6px;
    text-transform: uppercase;
}}

QLabel.MetricValue {{
    font-family: "Consolas", "Courier New", monospace;
    font-size: 13px;
    font-weight: 700;
    color: {COLORS['text_primary']};
}}

QLabel.MetricValueHighlight {{
    font-family: "Consolas", "Courier New", monospace;
    font-size: 13px;
    font-weight: 700;
    color: {COLORS['fl_cyan']};
}}

/* Modulation Box */
QFrame.ModulationBox {{
    background-color: {COLORS['bg_cell']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    padding: 12px 14px;
}}

QLabel.ModulationState {{
    font-size: 16px;
    font-weight: 800;
    color: {COLORS['fl_orange']};
    letter-spacing: 0.5px;
}}

QLabel.ModulationConfidence {{
    font-size: 11px;
    color: {COLORS['text_secondary']};
    font-family: "Consolas", monospace;
}}

/* Compact Bottom Pipeline */
QLabel.PipelineStepDone {{
    color: {COLORS['fl_lime']};
    font-size: 11px;
    font-weight: 700;
}}

QLabel.PipelineStepPending {{
    color: {COLORS['text_muted']};
    font-size: 11px;
    font-weight: 600;
}}

QLabel.PipelineArrow {{
    color: {COLORS['border_light']};
    font-size: 12px;
    font-weight: bold;
    padding: 0 6px;
}}

/* Dialog & Input fields */
QDialog {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['text_primary']};
}}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background-color: {COLORS['bg_surface_dark']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 3px;
    padding: 5px 8px;
    font-family: "Consolas", monospace;
    font-size: 11px;
}}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border-color: {COLORS['fl_orange']};
}}

/* Splitter */
QSplitter::handle {{
    background-color: {COLORS['bg_main']};
    height: 6px;
}}

QSplitter::handle:hover {{
    background-color: {COLORS['fl_cyan']};
}}
"""

MAIN_QSS = FL_CLEAN_QSS
