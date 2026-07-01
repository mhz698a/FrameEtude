import ctypes, sys
from PyQt6 import QtGui, QtWidgets
from video_main import VideoEtude
from utils import set_dark_theme
import config

def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon(config.ICON_PATH))
    set_dark_theme(app)
    window = VideoEtude(); window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(config.ID_APP)
    main()
