# frame_player_panel.py
from PyQt6 import QtCore, QtWidgets

from curtain_lib import CurtainOverlay
from ocr_lib import SelectionOverlay
from config import NUM_THUMBS, THUMB_SPACING


class FramePlayerPanel(QtWidgets.QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main = main_window
        self._build()

    def _build(self):
        main = self.main
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        main.right_layout = layout

        main.info_label = QtWidgets.QLabel("Nombre - Duración")
        layout.addWidget(main.info_label)

        main.thumb_container = QtWidgets.QWidget()
        main.thumb_layout = QtWidgets.QHBoxLayout(main.thumb_container)
        main.thumb_layout.setContentsMargins(0, 0, 0, 0)
        main.thumb_layout.setSpacing(THUMB_SPACING)
        main.thumb_container.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        layout.addWidget(main.thumb_container)

        main.thumb_labels = []
        for _ in range(NUM_THUMBS):
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

        controls_nav = QtWidgets.QHBoxLayout()

        btn_fc = QtWidgets.QPushButton("Fc")
        btn_fc.clicked.connect(main.copy_frame_dib)
        controls_nav.addWidget(btn_fc)

        for txt, func in [
            ("-90", lambda: main.move_seconds(-90)),
            ("-60", lambda: main.move_seconds(-60)),
            ("-30", lambda: main.move_seconds(-30)),
            ("-01", lambda: main.move_seconds(-1)),
            ("-Fr1", lambda: main.move_frame(-1)),
        ]:
            b = QtWidgets.QPushButton(txt)
            b.clicked.connect(func)
            controls_nav.addWidget(b)

        main.entry_time = QtWidgets.QLineEdit()
        main.entry_time.setFixedWidth(140)
        main.entry_time.returnPressed.connect(main.go_to_time)
        controls_nav.addWidget(main.entry_time)

        for txt, func in [
            ("+Fr1", lambda: main.move_frame(1)),
            ("+01", lambda: main.move_seconds(1)),
            ("+30", lambda: main.move_seconds(30)),
            ("+60", lambda: main.move_seconds(60)),
            ("+90", lambda: main.move_seconds(90)),
        ]:
            b = QtWidgets.QPushButton(txt)
            b.clicked.connect(func)
            controls_nav.addWidget(b)

        layout.addLayout(controls_nav)

        controls_actions = QtWidgets.QHBoxLayout()

        btn_copy_time = QtWidgets.QPushButton("Copy Timestamp")
        btn_copy_time.clicked.connect(main.copy_time_to_clipboard)
        controls_actions.addWidget(btn_copy_time)

        btn_export = QtWidgets.QPushButton("Extract Frame")
        btn_export.clicked.connect(main.export_frame_png)
        controls_actions.addWidget(btn_export)

        btn_ccr = QtWidgets.QPushButton("CCR")
        btn_ccr.clicked.connect(main.activate_ocr_selection)
        controls_actions.addWidget(btn_ccr)

        btn_cut_main = QtWidgets.QPushButton("Cut")
        btn_cut_main.clicked.connect(main.show_cut_dialog)
        controls_actions.addWidget(btn_cut_main)

        main.check_adjacent = QtWidgets.QCheckBox("Mostrar adyacentes")
        main.check_adjacent.setChecked(False)
        main.check_adjacent.hide()
        main.check_adjacent.stateChanged.connect(main.update_thumbs_visibility)
        controls_actions.addWidget(main.check_adjacent)

        main.check_curtain = QtWidgets.QCheckBox("Hide")
        main.check_curtain.setChecked(False)
        main.check_curtain.stateChanged.connect(main.update_curtain_visibility)
        controls_actions.addWidget(main.check_curtain)

        main.check_always_on_top = QtWidgets.QCheckBox("Always on top")
        main.check_always_on_top.setChecked(False)
        main.check_always_on_top.stateChanged.connect(main.update_always_on_top)
        controls_actions.addWidget(main.check_always_on_top)

        controls_actions.addStretch(1)
        layout.addLayout(controls_actions)

        main.status = QtWidgets.QLabel("")
        layout.addWidget(main.status)