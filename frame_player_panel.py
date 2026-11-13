# frame_player_panel.py
from PyQt6 import QtCore, QtWidgets

from curtain_lib import CurtainOverlay
from ocr_lib import SelectionOverlay
import config


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
                background-color: #3a3a3c; 
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
                qproperty-alignment: 'AlignCenter'; /* <--- Esto centra tanto el texto como el placeholder */
            }
        """)

        main.right_layout = layout

        main.info_label = QtWidgets.QLabel("Nombre - Duración")
        main.info_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(main.info_label)

        main.thumb_container = QtWidgets.QWidget()
        main.thumb_layout = QtWidgets.QHBoxLayout(main.thumb_container)
        main.thumb_layout.setContentsMargins(0, 0, 0, 0)
        main.thumb_layout.setSpacing(config.THUMB_SPACING)
        main.thumb_container.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        layout.addWidget(main.thumb_container)

        main.thumb_labels = []
        for _ in range(config.NUM_THUMBS):
            lbl = QtWidgets.QLabel()
            lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("background-color: rgb(18,18,18); border: 1px solid #2b2b2b;")
            lbl.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Fixed,
                QtWidgets.QSizePolicy.Policy.Fixed,
            )
            main.thumb_labels.append(lbl)

        main.curtain = CurtainOverlay(main.thumb_container)
        main.curtain.hide()

        main.selection_overlay = SelectionOverlay(main.thumb_container)
        main.selection_overlay.setGeometry(0, 0, 800, 200)
        main.selection_overlay.selection_made.connect(main._on_selection_made)

        main.video_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        main.video_slider.sliderReleased.connect(main.on_slider_released)
        main.video_slider.valueChanged.connect(main.on_slider_value_changed)
        layout.addWidget(main.video_slider)

        # Layout único para todos los controles en una sola línea horizontal
        controls_layout = QtWidgets.QHBoxLayout()
        controls_layout.setSpacing(6)

        # Checkboxes lógicos requeridos por la ventana principal por compatibilidad
        if not hasattr(main, "check_adjacent") or main.check_adjacent is None:
            main.check_adjacent = QtWidgets.QCheckBox()
            main.check_adjacent.hide()
            main.check_adjacent.setChecked(False)

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

        action_adj = menu_options.addAction("Mostrar adyacentes")
        action_adj.setCheckable(True)
        action_adj.setChecked(main.check_adjacent.isChecked())
        action_adj.toggled.connect(lambda checked: (main.check_adjacent.setChecked(checked), main.update_thumbs_visibility()))

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
        btn_minus_fr1.clicked.connect(lambda: main.move_frame(-1))
        controls_layout.addWidget(btn_minus_fr1)

        # Campo de tiempo con placeholder
        main.entry_time = QtWidgets.QLineEdit()
        main.entry_time.setFixedWidth(120)
        main.entry_time.setPlaceholderText("hh:mm:ss:ff")
        main.entry_time.returnPressed.connect(main.go_to_time)
        controls_layout.addWidget(main.entry_time)

        # Botón +Fr1
        btn_plus_fr1 = QtWidgets.QPushButton("+Fr1")
        btn_plus_fr1.clicked.connect(lambda: main.move_frame(1))
        controls_layout.addWidget(btn_plus_fr1)

        # Botón unificado +01s con menú desplegable lateral para saltos largos
        btn_pos = QtWidgets.QToolButton()
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
        layout.addLayout(controls_layout)

        main.status = QtWidgets.QLabel("")
        layout.addWidget(main.status)