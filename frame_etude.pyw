import sys, ctypes, traceback
from PyQt6 import QtGui, QtWidgets
from video_main import VideoEtude
from utils import set_dark_theme
import config


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon(config.ICON_PATH))
    set_dark_theme(app)
    
    try:
        window = VideoEtude()
        window.show()
        sys.exit(app.exec())
        
    except Exception as e:
        error_msg = traceback.format_exc()
        
        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
        msg.setWindowTitle("Error de Ejecución")
        msg.setText("La aplicación se cerró debido a un error inesperado.")
        msg.setDetailedText(error_msg)
        msg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
        msg.exec()
        
        sys.exit(1)

if __name__ == "__main__":
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(config.ID_APP)
    main()
