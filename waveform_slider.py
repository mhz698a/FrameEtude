import sys
import subprocess
import numpy as np
import imageio_ffmpeg
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QHBoxLayout, QPushButton, QFileDialog, QLabel
)
from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QThread
from PyQt6.QtGui import QPainter, QColor, QBrush
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget

class WaveformWorker(QThread):
    """Hilo secundario para extraer el audio del video sin congelar la interfaz."""
    pass

class WaveformSlider(QWidget):
    """
    Widget personalizado que dibuja la onda y actúa como slider.
    """
    pass