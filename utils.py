from PyQt6 import QtGui, QtWidgets
from qss import QSS_SHEET

def set_dark_theme(app: QtWidgets.QApplication):
    p = QtGui.QPalette()
    p.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor(30, 30, 30))
    p.setColor(QtGui.QPalette.ColorRole.WindowText, QtGui.QColor(220, 220, 220))
    p.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor(25, 25, 25))
    p.setColor(QtGui.QPalette.ColorRole.AlternateBase, QtGui.QColor(35, 35, 35))
    p.setColor(QtGui.QPalette.ColorRole.ToolTipBase, QtGui.QColor(220, 220, 220))
    p.setColor(QtGui.QPalette.ColorRole.ToolTipText, QtGui.QColor(220, 220, 220))
    p.setColor(QtGui.QPalette.ColorRole.Text, QtGui.QColor(220, 220, 220))
    p.setColor(QtGui.QPalette.ColorRole.Button, QtGui.QColor(45, 45, 48))
    p.setColor(QtGui.QPalette.ColorRole.ButtonText, QtGui.QColor(220, 220, 220))
    p.setColor(QtGui.QPalette.ColorRole.BrightText, QtGui.QColor(255, 0, 0))
    p.setColor(QtGui.QPalette.ColorRole.Highlight, QtGui.QColor(64, 120, 240))
    p.setColor(QtGui.QPalette.ColorRole.HighlightedText, QtGui.QColor(255, 255, 255))
    app.setPalette(p)
    app.setStyleSheet(QSS_SHEET)

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
