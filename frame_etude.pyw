import ctypes, sys
from PyQt6 import QtGui, QtWidgets
from video_main import VideoEtude
from utils import set_dark_theme
from config import ICON_PATH, ID_APP
9
def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon(ICON_PATH))
    set_dark_theme(app)
    window = VideoEtude(); window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(ID_APP)
    main()
