from PyQt6 import QtCore, QtWidgets, QtGui

# -----------------------
# Curtain overlay and main UI
# -----------------------
class CurtainOverlay(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.min_height = 10
        self.top = 0
        self.bottom = 0
        self.dragging = None
        self.setMouseTracking(True)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        self.hide()

    def set_geometry_height(self, x, y, w, h):
        self.setGeometry(x, y, w, h)
        if self.bottom <= 0 or self.bottom > h:
            self.bottom = max(self.min_height, h - 10)
        if self.top < 0:
            self.top = 0
        if self.top > self.bottom - self.min_height:
            self.top = max(0, self.bottom - self.min_height)
        self.update()
        self.raise_()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        color = QtGui.QColor(0, 0, 0, 255)
        rect = QtCore.QRect(0, self.top, self.width(), max(0, self.bottom - self.top))
        painter.fillRect(rect, color)
        pen = QtGui.QPen(QtGui.QColor(140,140,140,220))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawLine(0, self.top, self.width(), self.top)
        painter.drawLine(0, self.bottom, self.width(), self.bottom)
        painter.end()

    def mousePressEvent(self, event):
        y = int(event.position().y())
        if abs(y - self.top) < 10:
            self.dragging = 'top'
        elif abs(y - self.bottom) < 10:
            self.dragging = 'bottom'
        else:
            self.dragging = None

    def mouseMoveEvent(self, event):
        y = int(event.position().y())
        h = self.height() or 1
        
        if self.dragging == 'top':
            new_top = max(0, min(self.bottom - self.min_height, y))
            self.top = new_top
            self.update()
        elif self.dragging == 'bottom':
            new_bottom = min(h, max(self.top + self.min_height, y))
            self.bottom = new_bottom
            self.update()
        else:
            if abs(y - self.top) < 20 or abs(y - self.bottom) < 20:
                self.setCursor(QtCore.Qt.CursorShape.SizeVerCursor)
            else:
                self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)


    def mouseReleaseEvent(self, event):
        self.dragging = None

#