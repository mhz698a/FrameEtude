# frame_player_panel.py
from PyQt6 import QtCore, QtGui, QtWidgets

from curtain_lib import CurtainOverlay
from ocr_lib import SelectionOverlay
import config

class FrameViewport(QtWidgets.QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main = main_window

    def resizeEvent(self, event):
        super().resizeEvent(event)
        overlay = getattr(self.main, "selection_overlay", None)
        if overlay is not None:
            overlay.setGeometry(self.rect())

        if getattr(self.main, "curtain", None) is not None:
            self.main.update_curtain_geometry()


class FrameCanvas(QtWidgets.QWidget):
    """QSS-aware frame canvas that paints the video image after its styled background."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._frame_image = QtGui.QImage()
        self.setMinimumSize(0, 0)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("background-color: black; border: none;")
        
        # Estado de la cortina
        self.curtain_enabled = False
        self.curtain_top = 0
        self.curtain_bottom = 0
        self.min_curtain_height = 10
        self.dragging_curtain = None
        self.setMouseTracking(True)

    def set_frame_image(self, image):
        self._frame_image = image.copy() if image is not None else QtGui.QImage()
        self.update()

    def clear_frame(self):
        self._frame_image = QtGui.QImage()
        self.update()

    def displayed_image_rect(self):
        if self._frame_image.isNull():
            return QtCore.QRect()

        area = self.contentsRect()
        if area.width() <= 0 or area.height() <= 0:
            return QtCore.QRect()

        scaled_size = self._frame_image.size().scaled(
            area.size(),
            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
        )
        if scaled_size.isEmpty():
            return QtCore.QRect()

        return QtCore.QRect(
            area.x() + (area.width() - scaled_size.width()) // 2,
            area.y() + (area.height() - scaled_size.height()) // 2,
            scaled_size.width(),
            scaled_size.height(),
        )

    def set_curtain_enabled(self, enabled: bool):
        self.curtain_enabled = enabled
        self.update()

    def update_curtain_geometry(self):
        target = self.displayed_image_rect()
        if target.isEmpty():
            return
        h = target.height()
        if h <= 0:
            return
        if self.curtain_bottom <= 0:
            default_height = min(150, h // 2)
            self.curtain_top = (h - default_height) // 2
            self.curtain_bottom = self.curtain_top + default_height
        
        self.curtain_top = max(0, min(self.curtain_top, h - self.min_curtain_height))
        self.curtain_bottom = max(self.curtain_top + self.min_curtain_height, min(self.curtain_bottom, h))
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_curtain_geometry()
        viewport = self.parentWidget()
        main_window = getattr(viewport, "main", None)
        if main_window is not None:
            main_window.update_curtain_geometry()

    def paintEvent(self, event):
        option = QtWidgets.QStyleOption()
        option.initFrom(self)

        painter = QtGui.QPainter(self)
        self.style().drawPrimitive(
            QtWidgets.QStyle.PrimitiveElement.PE_Widget,
            option,
            painter,
            self,
        )

        target = self.displayed_image_rect()
        if target.isEmpty():
            return

        painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.drawImage(target, self._frame_image)

        # Dibujar cortina integrada si está activa
        if self.curtain_enabled:
            h = target.height()
            if h > 0 and self.curtain_bottom > self.curtain_top:
                painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
                
                curtain_rect = QtCore.QRect(
                    target.x(),
                    target.y() + self.curtain_top,
                    target.width(),
                    self.curtain_bottom - self.curtain_top
                )
                
                # Color de la cortina (Negro sólido u opaco)
                painter.fillRect(curtain_rect, QtGui.QColor(0, 0, 0, 255))
                
                # Líneas divisorias superior e inferior de la cortina
                pen = QtGui.QPen(QtGui.QColor(140, 140, 140, 220))
                pen.setWidth(2)
                painter.setPen(pen)
                painter.drawLine(target.x(), target.y() + self.curtain_top, target.x() + target.width(), target.y() + self.curtain_top)
                painter.drawLine(target.x(), target.y() + self.curtain_bottom, target.x() + target.width(), target.y() + self.curtain_bottom)

    def mousePressEvent(self, event):
        if not self.curtain_enabled:
            super().mousePressEvent(event)
            return
        
        target = self.displayed_image_rect()
        if target.isEmpty():
            return
        
        y_local = event.position().y() - target.y()
        if abs(y_local - self.curtain_top) < 10:
            self.dragging_curtain = 'top'
        elif abs(y_local - self.curtain_bottom) < 10:
            self.dragging_curtain = 'bottom'
        else:
            self.dragging_curtain = None

    def mouseMoveEvent(self, event):
        if not self.curtain_enabled:
            super().mouseMoveEvent(event)
            return
        
        target = self.displayed_image_rect()
        if target.isEmpty():
            return
        
        y_local = event.position().y() - target.y()
        h = target.height()
        
        if self.dragging_curtain == 'top':
            self.curtain_top = max(0, min(self.curtain_bottom - self.min_curtain_height, int(y_local)))
            self.update()
        elif self.dragging_curtain == 'bottom':
            self.curtain_bottom = min(h, max(self.curtain_top + self.min_curtain_height, int(y_local)))
            self.update()
        else:
            if abs(y_local - self.curtain_top) < 20 or abs(y_local - self.curtain_bottom) < 20:
                self.setCursor(QtCore.Qt.CursorShape.SizeVerCursor)
            else:
                self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)

    def mouseReleaseEvent(self, event):
        self.dragging_curtain = None
        super().mouseReleaseEvent(event)


class FramePlayerPanel(QtWidgets.QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main = main_window
        self._build()

    def _build(self):
        main = self.main
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)
        
        self.setStyleSheet("""
            QPushButton, QToolButton { 
                background-color: transparent; 
                border: 1px solid #2b2b2d; 
                padding: 6px 10px; 
                border-radius: 6px; 
                color: #e6e6e6; 
            }

            QPushButton:hover, QToolButton::hover { background-color: #4a4a4c; }
            QPushButton:pressed, QToolButton::pressed { background-color: #2e88ff; color: white; }
            QPushButton:disabled, QToolButton::disabled { background-color: #2a2a2a; color: #888888; }

            QToolButton::menu-button {
                border-left: 1px solid #3c3c3c;
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
                width: 16px;
            }
            
            QLineEdit { 
                background-color: #1e1e1f; 
                border: 1px solid #2b2b2d; 
                padding: 4px; 
                color: #e6e6e6; 
                border-radius: 4px; 
                qproperty-alignment: 'AlignCenter'; 
            }
        """)

        main.right_layout = layout

        # --- Contenedor unificado: Título + Video + Slider + Controles ---
        video_box_layout = QtWidgets.QVBoxLayout()
        video_box_layout.setContentsMargins(0, 0, 0, 0)
        video_box_layout.setSpacing(0)

        # Etiqueta de nombre y duración con fondo negro y texto blanco
        main.info_label = QtWidgets.QLabel("FrameEtude - 00:00:00.000")
        main.info_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        main.info_label.setStyleSheet("""
            background-color: black;
            color: white;
            padding: 6px;
            font-weight: bold;
            border: none;
        """)
        video_box_layout.addWidget(main.info_label)

        main.frame_viewport = FrameViewport(main)
        main.frame_viewport.setStyleSheet(
            "background-color: black; border: none;"
        )
        main.frame_layout = QtWidgets.QHBoxLayout(main.frame_viewport)
        main.frame_layout.setContentsMargins(0, 0, 0, 0)
        main.frame_layout.setSpacing(0)
        main.frame_viewport.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        main.frame_canvas = FrameCanvas(main.frame_viewport)
        main.frame_layout.addWidget(main.frame_canvas, 1)
        video_box_layout.addWidget(main.frame_viewport, 1)

        # Contenedor del slider con fondo negro y estilo azul
        slider_wrapper = QtWidgets.QWidget()
        slider_wrapper.setStyleSheet("background-color: black; border: none")
        slider_layout = QtWidgets.QHBoxLayout(slider_wrapper)
        slider_layout.setContentsMargins(10, 8, 10, 8)

        main.video_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        main.video_slider.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        main.video_slider.setStyleSheet("""
            QSlider {
                border: none;
                background: transparent;
            }
            QSlider::groove:horizontal {
                background: #2b2b2b;
                height: 6px;
                border-radius: 3px;
                border: none;
            }
            QSlider::sub-page:horizontal {
                background: #2e88ff;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal:hover {
                background: #5ca2ff;
            }
            QSlider::sub-page:horizontal:pressed {
                background: #80b8ff;
            }
            QSlider::add-page:horizontal {
                background: #1e1e1f;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #ffffff;
                border: 1px solid #2e88ff;
                width: 14px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 7px;
            }
            QSlider::handle:horizontal:hover {
                background: #5ca2ff;
                border: 1px solid #5ca2ff;
            }
            QSlider::handle:horizontal:pressed {
                background: #80b8ff;
                border: 1px solid #80b8ff;
            }
        """)
        main.video_slider.sliderReleased.connect(main.on_slider_released)
        main.video_slider.valueChanged.connect(main.on_slider_value_changed)
        slider_layout.addWidget(main.video_slider)
        video_box_layout.addWidget(slider_wrapper)

        # --- Contenedor de botones centrados con fondo negro ---
        controls_wrapper = QtWidgets.QWidget()
        controls_wrapper.setObjectName("ControlsWrapper")
        controls_wrapper.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
        controls_wrapper.setStyleSheet("""
            #ControlsWrapper {
                background-color: black;
            }
        """)
        controls_layout = QtWidgets.QHBoxLayout(controls_wrapper)
        controls_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignVCenter)
        controls_layout.setContentsMargins(10, 8, 10, 8)
        controls_layout.setSpacing(6)

        controls_layout.addStretch(1) # Centrar a la izquierda

        if not hasattr(main, "check_curtain") or main.check_curtain is None:
            main.check_curtain = QtWidgets.QCheckBox()
            main.check_curtain.hide()
            main.check_curtain.setChecked(config.START_WITH_CURTAIN)


        # Botón de opciones (QToolButton para soportar menú instantáneo)
        btn_options = QtWidgets.QToolButton()
        btn_options.setText("Opciones")
        btn_options.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
        menu_options = QtWidgets.QMenu(btn_options)
        
        menu_options.addAction("Copy Frame to Clipboard", main.copy_frame_dib)
        menu_options.addAction("Copy Timestamp", main.copy_time_to_clipboard)
        menu_options.addAction("Extract Frame", main.export_frame_png)
        menu_options.addAction("CCR", main.activate_ocr_selection)
        menu_options.addAction("Cut", main.show_cut_dialog)
        
        menu_options.addSeparator()

        action_curt = menu_options.addAction("Hide")
        action_curt.setCheckable(True)
        action_curt.setChecked(main.check_curtain.isChecked())
        action_curt.toggled.connect(main.check_curtain.setChecked)

        action_top = menu_options.addAction("Always on top")
        action_top.setCheckable(True)
        action_top.setChecked(main.is_always_on_top())
        main.always_on_top_action = action_top
        action_top.toggled.connect(main.update_always_on_top)

        btn_options.setMenu(menu_options)
        controls_layout.addWidget(btn_options)

        # Botón unificado -01s con menú desplegable lateral para saltos largos
        btn_neg = QtWidgets.QToolButton()
        btn_neg.setText("-01s")
        btn_neg.setMinimumWidth(70)
        btn_neg.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        btn_neg.clicked.connect(lambda: main.move_seconds(-1))
        
        menu_neg = QtWidgets.QMenu(btn_neg)
        menu_neg.addAction("-90s", lambda: main.move_seconds(-90))
        menu_neg.addAction("-60s", lambda: main.move_seconds(-60))
        menu_neg.addAction("-30s", lambda: main.move_seconds(-30))
        btn_neg.setMenu(menu_neg)
        controls_layout.addWidget(btn_neg)

        # Botón -Fr1
        btn_minus_fr1 = QtWidgets.QPushButton("-Fr1")
        btn_minus_fr1.setMinimumHeight(35)
        btn_minus_fr1.clicked.connect(lambda: main.move_frame(-1))
        controls_layout.addWidget(btn_minus_fr1)

        # Campo de tiempo con placeholder
        main.entry_time = QtWidgets.QLineEdit()
        main.entry_time.setFixedWidth(120)
        main.entry_time.setMinimumHeight(35)
        main.entry_time.setPlaceholderText("hh:mm:ss:ff")
        main.entry_time.returnPressed.connect(main.go_to_time)
        controls_layout.addWidget(main.entry_time)

        # Botón +Fr1
        btn_plus_fr1 = QtWidgets.QPushButton("+Fr1")
        btn_plus_fr1.setMinimumHeight(35)
        btn_plus_fr1.clicked.connect(lambda: main.move_frame(1))
        controls_layout.addWidget(btn_plus_fr1)

        # Botón unificado +01s con menú desplegable lateral para saltos largos
        btn_pos = QtWidgets.QToolButton()
        btn_pos.setMinimumWidth(70)
        btn_pos.setText("+01s")
        btn_pos.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        btn_pos.clicked.connect(lambda: main.move_seconds(1))
        
        menu_pos = QtWidgets.QMenu(btn_pos)
        menu_pos.addAction("+30s", lambda: main.move_seconds(30))
        menu_pos.addAction("+60s", lambda: main.move_seconds(60))
        menu_pos.addAction("+90s", lambda: main.move_seconds(90))
        btn_pos.setMenu(menu_pos)
        controls_layout.addWidget(btn_pos)

        controls_layout.addStretch(1)
        video_box_layout.addWidget(controls_wrapper)

        layout.addLayout(video_box_layout, 1)

        main.curtain = CurtainOverlay(main.frame_viewport)
        main.curtain.hide()

        main.selection_overlay = SelectionOverlay(main.frame_viewport)
        main.selection_overlay.setGeometry(main.frame_viewport.rect())
        main.selection_overlay.selection_made.connect(main._on_selection_made)

        main.check_curtain.toggled.connect(main.update_curtain_visibility)
        main.update_curtain_visibility()