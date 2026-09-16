"""
SIGMA - Signal Intelligence & Generalized Modulation Analyzer
Theme and Styling System (QSS)
"""

COLORS = {
    "bg_dark": "#0b0e14",
    "bg_panel": "#131722",
    "bg_subpanel": "#181d2a",
    "bg_card": "#151b26",
    "bg_header": "#1a2130",
    "border": "#242c3d",
    "border_light": "#2e384d",
    "text_primary": "#e6edf3",
    "text_secondary": "#8b949e",
    "text_muted": "#545d68",
    "accent_cyan": "#00d2ff",
    "accent_blue": "#2563eb",
    "accent_green": "#10b981",
    "accent_yellow": "#f59e0b",
    "accent_red": "#ef4444",
}

MAIN_QSS = f"""
QMainWindow, QWidget#CentralWidget {{
    background-color: {COLORS['bg_dark']};
    color: {COLORS['text_primary']};
    font-family: "Segoe UI", "Roboto", sans-serif;
    font-size: 12px;
}}

/* General Panels & Frames */
QFrame.SigmaPanel {{
    background-color: {COLORS['bg_panel']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
}}

QFrame.SigmaSubPanel {{
    background-color: {COLORS['bg_subpanel']};
    border: 1px solid {COLORS['border']};
    border-radius: 3px;
}}

QFrame.SigmaCard {{
    background-color: {COLORS['bg_card']};
    border: 1px solid {COLORS['border']};
    border-radius: 3px;
    padding: 6px 8px;
}}

/* Headers */
QLabel.HeaderTitle {{
    font-size: 18px;
    font-weight: 700;
    letter-spacing: 1.5px;
    color: {COLORS['text_primary']};
}}

QLabel.HeaderSubtitle {{
    font-size: 11px;
    color: {COLORS['text_secondary']};
    letter-spacing: 0.5px;
}}

QLabel.PanelHeader {{
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1.0px;
    color: {COLORS['accent_cyan']};
    text-transform: uppercase;
    padding-bottom: 2px;
}}

QLabel.CardLabel {{
    font-size: 10px;
    font-weight: 600;
    color: {COLORS['text_secondary']};
    letter-spacing: 0.5px;
    text-transform: uppercase;
}}

QLabel.CardValue {{
    font-size: 13px;
    font-weight: 700;
    color: {COLORS['text_primary']};
    font-family: "Consolas", "Courier New", monospace;
}}

QLabel.CardValueAccent {{
    font-size: 13px;
    font-weight: 700;
    color: {COLORS['accent_cyan']};
    font-family: "Consolas", "Courier New", monospace;
}}

QLabel.StatusPillOnline {{
    background-color: rgba(16, 185, 129, 0.15);
    color: {COLORS['accent_green']};
    border: 1px solid {COLORS['accent_green']};
    border-radius: 3px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.8px;
}}

QLabel.StatusPillProcessing {{
    background-color: rgba(0, 210, 255, 0.15);
    color: {COLORS['accent_cyan']};
    border: 1px solid {COLORS['accent_cyan']};
    border-radius: 3px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.8px;
}}

QLabel.StatusPillIdle {{
    background-color: rgba(139, 148, 158, 0.15);
    color: {COLORS['text_secondary']};
    border: 1px solid {COLORS['text_secondary']};
    border-radius: 3px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.8px;
}}

/* Buttons */
QPushButton {{
    background-color: {COLORS['bg_subpanel']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border_light']};
    border-radius: 3px;
    padding: 5px 12px;
    font-size: 11px;
    font-weight: 600;
}}

QPushButton:hover {{
    background-color: {COLORS['bg_header']};
    border-color: {COLORS['accent_cyan']};
    color: {COLORS['accent_cyan']};
}}

QPushButton:pressed {{
    background-color: {COLORS['bg_dark']};
}}

QPushButton.PrimaryButton {{
    background-color: rgba(0, 210, 255, 0.12);
    color: {COLORS['accent_cyan']};
    border: 1px solid {COLORS['accent_cyan']};
}}

QPushButton.PrimaryButton:hover {{
    background-color: rgba(0, 210, 255, 0.25);
    color: #ffffff;
}}

QPushButton.StopButton {{
    background-color: rgba(239, 68, 68, 0.12);
    color: {COLORS['accent_red']};
    border: 1px solid {COLORS['accent_red']};
}}

QPushButton.StopButton:hover {{
    background-color: rgba(239, 68, 68, 0.25);
    color: #ffffff;
}}

/* Inputs & Spinners */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background-color: {COLORS['bg_dark']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border_light']};
    border-radius: 3px;
    padding: 4px 6px;
    font-family: "Consolas", monospace;
    font-size: 11px;
}}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border-color: {COLORS['accent_cyan']};
}}

/* ScrollBars */
QScrollBar:vertical {{
    border: none;
    background: {COLORS['bg_dark']};
    width: 8px;
    margin: 0px;
}}

QScrollBar::handle:vertical {{
    background: {COLORS['border_light']};
    min-height: 20px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background: {COLORS['accent_cyan']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    border: none;
    background: {COLORS['bg_dark']};
    height: 8px;
    margin: 0px;
}}

QScrollBar::handle:horizontal {{
    background: {COLORS['border_light']};
    min-width: 20px;
    border-radius: 4px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {COLORS['accent_cyan']};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* Pipeline Modules */
QFrame.PipelineStageActive {{
    background-color: rgba(0, 210, 255, 0.15);
    border: 1px solid {COLORS['accent_cyan']};
    border-radius: 3px;
    padding: 4px 6px;
}}

QFrame.PipelineStageDone {{
    background-color: rgba(16, 185, 129, 0.12);
    border: 1px solid {COLORS['accent_green']};
    border-radius: 3px;
    padding: 4px 6px;
}}

QFrame.PipelineStagePending {{
    background-color: {COLORS['bg_subpanel']};
    border: 1px solid {COLORS['border']};
    border-radius: 3px;
    padding: 4px 6px;
}}

QLabel.PipelineStageName {{
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.5px;
}}

QLabel.PipelineStageStatus {{
    font-size: 10px;
    font-weight: 700;
}}
"""
