from PyQt5 import QtGui, QtWidgets

def set_dark_theme(app: QtWidgets.QApplication):
    p = QtGui.QPalette()
    p.setColor(QtGui.QPalette.Window, QtGui.QColor(30, 30, 30))
    p.setColor(QtGui.QPalette.WindowText, QtGui.QColor(220, 220, 220))
    p.setColor(QtGui.QPalette.Base, QtGui.QColor(25, 25, 25))
    p.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(35, 35, 35))
    p.setColor(QtGui.QPalette.ToolTipBase, QtGui.QColor(220, 220, 220))
    p.setColor(QtGui.QPalette.ToolTipText, QtGui.QColor(220, 220, 220))
    p.setColor(QtGui.QPalette.Text, QtGui.QColor(220, 220, 220))
    p.setColor(QtGui.QPalette.Button, QtGui.QColor(45, 45, 48))
    p.setColor(QtGui.QPalette.ButtonText, QtGui.QColor(220, 220, 220))
    p.setColor(QtGui.QPalette.BrightText, QtGui.QColor(255, 0, 0))
    p.setColor(QtGui.QPalette.Highlight, QtGui.QColor(64, 120, 240))
    p.setColor(QtGui.QPalette.HighlightedText, QtGui.QColor(255, 255, 255))
    app.setPalette(p)
    app.setStyleSheet("""
        QLabel { color: #e6e6e6; }
        QPushButton { background-color: #3a3a3c; border: 1px solid #2b2b2d; padding: 6px 10px; border-radius: 6px; color: #e6e6e6; }
        QPushButton:hover { background-color: #4a4a4c; }
        QPushButton:pressed { background-color: #2e88ff; color: white; }
        QPushButton:disabled { background-color: #2a2a2a; color: #888888; }
        QLineEdit { background-color: #1e1e1f; border: 1px solid #2b2b2d; padding: 4px; color: #e6e6e6; border-radius: 4px; }
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
    """)

def format_time(seconds=None, frame_num=None, fps=None):
    if frame_num is not None and fps is not None:
        total_ms = int(frame_num * 1000 / fps)
        h = total_ms // 3600000
        m = (total_ms % 3600000) // 60000
        s = (total_ms % 60000) // 1000
        ms = total_ms % 1000
        return f"{h:02}:{m:02}:{s:02}.{ms:03}"
    else:
        if seconds is None:
            seconds = 0.0
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{h:02}:{m:02}:{s:02}.{ms:03}"

def parse_time_to_seconds(s: str) -> float:
    """
    Parse string hh:mm:ss.mmm or hh:mm:ss to seconds (float).
    If fails, raises ValueError.
    """
    s = s.strip()
    parts = s.split(':')
    if len(parts) != 3:
        raise ValueError("Formato de tiempo incorrecto")
    h = int(parts[0])
    m = int(parts[1])
    sec_ms = parts[2].split('.')
    sec = int(sec_ms[0])
    ms = int(sec_ms[1]) if len(sec_ms) > 1 else 0
    return h * 3600 + m * 60 + sec + ms / 1000.0



#