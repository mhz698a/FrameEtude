# frame_player_panel.py
from PyQt6 import QtCore, QtGui, QtWidgets

from curtain_lib import CurtainOverlay
from ocr_lib import SelectionOverlay

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


class FrameDisplayLabel(QtWidgets.QLabel):
    """Single-frame viewer that keeps the source image and scales it on resize."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._frame_image = QtGui.QImage()
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(0, 0)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        self.setStyleSheet("background-color: rgb(18,18,18); border: none;")

    def set_frame_image(self, image):
        self._frame_image = image.copy() if image is not None else QtGui.QImage()
        self._render_frame()

    def clear_frame(self):
        self._frame_image = QtGui.QImage()
        self.clear()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._render_frame()

    def _render_frame(self):
        if self._frame_image.isNull():
            return

        target_size = self.contentsRect().size()
        if target_size.width() <= 0 or target_size.height() <= 0:
            return

        pixmap = QtGui.QPixmap.fromImage(self._frame_image).scaled(
            target_size,
            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(pixmap)


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
        main.info_label = QtWidgets.QLabel("Nombre - Duración")
        main.info_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        main.info_label.setStyleSheet("""
            background-color: black;
            color: white;
            padding: 6px;
            font-weight: bold;
            border: 1px solid #2b2b2b;
            border-bottom: none;
        """)
        video_box_layout.addWidget(main.info_label)

        main.frame_viewport = FrameViewport(main)
        main.frame_viewport.setStyleSheet(
            "background-color: rgb(18,18,18); border: none;"
        )
        main.frame_layout = QtWidgets.QHBoxLayout(main.frame_viewport)
        main.frame_layout.setContentsMargins(0, 0, 0, 0)
        main.frame_layout.setSpacing(0)
        main.frame_viewport.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        main.frame_label = FrameDisplayLabel(main.frame_viewport)
        main.frame_layout.addWidget(main.frame_label, 1)
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
            main.check_curtain.setChecked(True)

        if not hasattr(main, "check_always_on_top") or main.check_always_on_top is None:
            main.check_always_on_top = QtWidgets.QCheckBox()
            main.check_always_on_top.hide()
            main.check_always_on_top.setChecked(False)

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
        action_curt.toggled.connect(lambda checked: (main.check_curtain.setChecked(checked), main.update_curtain_visibility()))

        action_top = menu_options.addAction("Always on top")
        action_top.setCheckable(True)
        action_top.setChecked(main.check_always_on_top.isChecked())
        action_top.toggled.connect(lambda checked: (main.check_always_on_top.setChecked(checked), main.update_always_on_top(checked)))

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