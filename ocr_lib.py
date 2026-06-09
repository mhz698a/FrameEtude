from PyQt6 import QtCore, QtWidgets
import numpy as np
import cv2

# OCR deps
import pytesseract
import re
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# -----------------------
# OCR Worker (runs in background QThread)
# -----------------------
class OCRWorker(QtCore.QObject):
    finished = QtCore.pyqtSignal(str)
    error = QtCore.pyqtSignal(str)

    @QtCore.pyqtSlot(object, dict)
    def process(self, arr_rgb, params):
        """
        arr_rgb: numpy RGB array
        params: dict with flags
        Emits finished(text) on success, error(msg) on failure.
        """
        try:
            # convert to uint8 numpy
            img = arr_rgb.copy()
            if img.dtype != np.uint8:
                img = (img * 255).astype(np.uint8)

            # scale
            scale = float(params.get('scale', 1))
            if scale != 1.0:
                img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

            # RGB -> gray
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

            # CLAHE
            if params.get('clahe', False):
                clahe = cv2.createCLAHE(clipLimit=float(params.get('clahe_clip', 2.0)), tileGridSize=(8,8))
                gray = clahe.apply(gray)

            # denoise (median)
            k = int(params.get('denoise_ksize', 3))
            if k >= 3:
                gray = cv2.medianBlur(gray, k)

            # binarize (OTSU)
            if params.get('binarize', True):
                _, gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # invert
            if params.get('invert', False):
                gray = cv2.bitwise_not(gray)

            # dilation
            dil_iter = int(params.get('dilate_iter', 0))
            if dil_iter > 0:
                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2,2))
                gray = cv2.dilate(gray, kernel, iterations=dil_iter)

            # final pass: ensure uint8
            proc = gray

            # try pytesseract
            try:
                # ensure tesseract present
                _ = pytesseract.get_tesseract_version()
            except Exception as e:
                self.error.emit('Tesseract no está disponible o no está en PATH. ' + str(e))
                return

            # config = f'--psm {int(params.get("psm", 6))}'
            lang = params.get('lang', 'spa')
            psm = int(params.get("psm", 6))

            whitelist = (
                "abcdefghijklmnopqrstuvwxyz"
                "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                "áéíóúÁÉÍÓÚñÑüÜ"
                "0123456789"
                " .,!?¿¡:-—'()"
            )

            # 
            config = (
                # f'--oem 3 '
                f'--psm {psm} '
                f'-c tessedit_char_whitelist="{whitelist}"'
            )

            text = pytesseract.image_to_string(proc, lang=lang, config=config)
            self.finished.emit(text)
        except Exception as e:
            self.error.emit(str(e))

# -----------------------
# Selection overlay (rubberband) placed over thumb_container
# -----------------------
class SelectionOverlay(QtWidgets.QWidget):
    selection_made = QtCore.pyqtSignal(QtCore.QRect)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setWindowFlags(QtCore.Qt.WindowType.Widget | QtCore.Qt.WindowType.FramelessWindowHint)
        self.setMouseTracking(True)
        self.rubber = QtWidgets.QRubberBand(QtWidgets.QRubberBand.Shape.Rectangle, self)
        self.origin = None
        self.hide()

    def start(self):
        self.setCursor(QtCore.Qt.CursorShape.CrossCursor)
        self.origin = None
        self.rubber.hide()
        self.show()
        self.raise_()

    def stop(self):
        self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
        self.origin = None
        self.rubber.hide()
        self.hide()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.origin = event.position().toPoint()
            self.rubber.setGeometry(QtCore.QRect(self.origin, QtCore.QSize()))
            self.rubber.show()

    def mouseMoveEvent(self, event):
        if self.origin is not None:
            rect = QtCore.QRect(self.origin, event.position().toPoint()).normalized()
            self.rubber.setGeometry(rect)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton and self.origin is not None:
            rect = self.rubber.geometry()
            self.rubber.hide()
            self.origin = None
            self.selection_made.emit(rect)
            self.hide()
