QSS_SHEET = """
QLabel { 
    color: #e6e6e6; 
}
QPushButton { 
    background-color: #3a3a3c; 
    border: 1px solid #2b2b2d; 
    padding: 6px 10px; 
    border-radius: 6px; 
    color: #e6e6e6; 
}

QPushButton:hover { background-color: #4a4a4c; }
QPushButton:pressed { background-color: #2e88ff; color: white; }
QPushButton:disabled { background-color: #2a2a2a; color: #888888; }

QLineEdit { 
    background-color: #1e1e1f; 
    border: 1px solid #2b2b2d; 
    padding: 4px; 
    color: #e6e6e6; 
    border-radius: 4px; 
}
QCheckBox { color: #e6e6e6; }
QMessageBox {
    background-color: #2b2b2b;
    color: #dddddd;
    font-size: 14px;
}
QMessageBox QLabel {
    color: #dddddd;
}
QMessageBox QPushButton {
    background-color: #444444;
    color: #ffffff;
    padding: 6px 10px;
    border-radius: 4px;
}
QMessageBox QPushButton:hover {
    background-color: #555555;
}
QMessageBox QPushButton:pressed {
    background-color: #333333;
}
QComboBox {
    background-color: #1e1e1f;
    border: 1px solid #2b2b2d;
    padding: 4px;
    color: #e6e6e6;
    border-radius: 4px;
}
QComboBox QAbstractItemView {
    background-color: #1e1e1f;
    selection-background-color: #2e88ff;
    color: #e6e6e6;
}
QSlider::groove:horizontal {
    border: 1px solid #2b2b2d;
    height: 6px;
    background: #1e1e1f;
    margin: 2px 0;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #3a3a3c;
    border: 1px solid #5c5c5c;
    width: 18px;
    height: 18px;
    margin: -7px 0;
    border-radius: 9px;
}

QSlider::handle:horizontal:hover {
    background: #4a4a4c;
    border: 1px solid #2e88ff;
}

QSlider::sub-page:horizontal {
    background: #2e88ff;
    border-radius: 3px;
}
"""

Old_qss = """
QScrollBar:vertical {
    background: #1e1e1f;
    width: 10px;
}
QScrollBar::handle:vertical {
    background: #3a3a3c;
    min-height: 20px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #4a4a4c;
}

QSpinBox, QDoubleSpinBox {
    background-color: #1e1e1f;
    border: 1px solid #2b2b2d;
    padding-right: 18px;   /* espacio para las flechas */
    color: #e6e6e6;
    border-radius: 4px;
}

/* Botón UP */
QSpinBox::up-button, QDoubleSpinBox::up-button {
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 16px;
    background-color: #3a3a3c;
    border-left: 1px solid #2b2b2d;
    border-bottom: 1px solid #2b2b2d;
}

QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {
    background-color: #4a4a4c;
}

/* Botón DOWN */
QSpinBox::down-button, QDoubleSpinBox::down-button {
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 16px;
    background-color: #3a3a3c;
    border-left: 1px solid #2b2b2d;
}

QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
    background-color: #4a4a4c;
}

/* Flechas */
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
    image: url(none);
    width: 0;
    height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-bottom: 6px solid #e6e6e6;
}

QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
    image: url(none);
    width: 0;
    height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 6px solid #e6e6e6;
}
"""
