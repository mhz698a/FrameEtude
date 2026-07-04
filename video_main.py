import os, re, struct, datetime, cv2, win32clipboard, subprocess, sys
from PyQt6 import QtCore, QtGui, QtWidgets
from ocr_lib import OCRWorker
from settings_dialog import SettingsDialog
from vidwk_lib import VideoWorker
from cut_dialog_ex import CutDialog
from file_table_widget import FileTableWidget
from smb_dialog import SMBDialog
from PIL import Image
import config
from utils import *
from infoutils import get_overwrite_data
from frame_player_panel import FramePlayerPanel
from lyric_vision_panel import LyricVisionPanel
from about_season_dialog import AboutSeasonDialog
from year_selector_bar import YearSelectorBar
from folder_selector_bar import FolderSelectorBar
import year_creator

class VideoEtude(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FrameEtude")
        screen = QtWidgets.QApplication.primaryScreen().availableGeometry()
        screen_w = screen.width()
        screen_h = screen.height()
        self.setMaximumSize(screen_w, screen_h)
        self.resize(1300, 620)

        # central layout: left panel + right main area
        w = QtWidgets.QWidget()
        self.setCentralWidget(w)
        self.main_layout = QtWidgets.QHBoxLayout(w)
        self.main_layout.setContentsMargins(8,8,8,8)
        self.main_layout.setSpacing(8)

        # ---------------- Left panel ----------------
        self.left_panel = QtWidgets.QWidget()
        self.left_panel.setFixedWidth(660)
        left_layout = QtWidgets.QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(4,4,4,4)
        left_layout.setSpacing(6)
        
        h1_master = QtWidgets.QHBoxLayout()
        
        self.combo_year = QtWidgets.QComboBox()
        self.combo_year.setFixedWidth(60)
        self.combo_year.currentIndexChanged.connect(self.on_year_changed)
        self.combo_year.setVisible(False)
        
        self.year_selector_bar = YearSelectorBar()
        self.year_selector_bar.yearSelected.connect(self.on_year_bar_selected)
        self.year_selector_bar.hiddenYearSelected.connect(self.on_hidden_year_selected)
        self.year_selector_bar.createNewYearRequested.connect(self.on_create_new_year_requested)
        
        self.folder_selector_bar = FolderSelectorBar()
        self.folder_selector_bar.folderSelected.connect(self.on_master_changed)
        self.folder_selector_bar.folderChanged.connect(
            lambda: self.on_year_changed(self.combo_year.currentIndex())
            )
        
        h2_master = QtWidgets.QHBoxLayout()
        self.base_label = QtWidgets.QLabel('<b>E:\\_Internal\\...\\___[...]\\...\\...</b>')
        
        self.btn_about = QtWidgets.QPushButton("About")
        self.btn_about.clicked.connect(self.open_about_dialog)
        
        self.btn_rescan = QtWidgets.QPushButton("Refresh")
        self.btn_rescan.clicked.connect(self.rescan_current_master_folder)
        
        self.btn_settings = QtWidgets.QPushButton("Settings")
        self.btn_settings.clicked.connect(self.open_settings_dialog)
                
        self.btn_etude = QtWidgets.QPushButton("Etude")
        self.btn_etude.clicked.connect(self.open_etude_file)
        
        self.btn_ovreg1 = QtWidgets.QPushButton("Get Ov1 Reg")
        self.btn_ovreg1.clicked.connect(lambda: self.get_reg_ov_temp("1"))
        
        self.btn_ovreg2 = QtWidgets.QPushButton("Get Ov2 Reg")
        self.btn_ovreg2.clicked.connect(lambda: self.get_reg_ov_temp("2"))
        
        self.btn_eptmp = QtWidgets.QPushButton("Get Titles Ep")
        self.btn_eptmp.clicked.connect(self.get_episode_titles_temp)
        
        self.btn_check = QtWidgets.QPushButton("Check")
        self.btn_check.clicked.connect(self.open_lyrics_manager)
        self.btn_check.hide()
        
        h1_master.addWidget(self.base_label, 1)
        h1_master.addWidget(self.btn_about)
        h1_master.addWidget(self.btn_rescan)
        
        h2_master.addWidget(self.btn_settings)
        h2_master.addWidget(self.btn_etude)
        h2_master.addWidget(self.btn_ovreg1)
        h2_master.addWidget(self.btn_ovreg2)        
        h2_master.addWidget(self.btn_eptmp)
        h2_master.addWidget(self.btn_check)
        
        left_layout.addLayout(h1_master)
        left_layout.addLayout(h2_master)
        
        self.folder_count_label = QtWidgets.QLabel("0 archivos multimedia detectados en esta carpeta")
        left_layout.addWidget(self.folder_count_label)
        
        self.chk_lyric = QtWidgets.QCheckBox("Es lirica")
        self.chk_lyric.setChecked(False)
        self.chk_lyric.hide()
        self.chk_lyric.toggled.connect(self.on_lyric_checkbox_toggled)
        left_layout.addWidget(self.chk_lyric)
        
        self.file_table = FileTableWidget()
        self.file_table.itemSelectionChanged.connect(self.on_file_selected)
        self.file_table.row_count_changed.connect(self.on_file_count_changed)
        # left_layout.addWidget(self.file_table, 1)
        
        files_row = QtWidgets.QHBoxLayout()
        files_row.setSpacing(6)
        
        files_row.addWidget(self.year_selector_bar)
        files_row.addWidget(self.folder_selector_bar)
        files_row.addWidget(self.file_table, 1)
        left_layout.addLayout(files_row, 1)
        
        self.metadata_progress_label = QtWidgets.QLabel("0/0")
        left_layout.addWidget(self.metadata_progress_label)

        self.metadata_progress_bar = QtWidgets.QProgressBar()
        self.metadata_progress_bar.setRange(0, 100)
        self.metadata_progress_bar.setValue(0)
        left_layout.addWidget(self.metadata_progress_bar)
        
        self.file_table.set_progress_widgets(
            self.metadata_progress_bar,
            self.metadata_progress_label,
        )
        
        overwrite_btns = QtWidgets.QHBoxLayout()
        botones_config = [
            ('Overwrite P', "ov_0"),
            ('Overwrite I', "ov_1"),
            ('Overwrite II', "ov_2"),
            ('Overwrite III', "ov_3")
        ]

        for texto, key in botones_config:
            btn = QtWidgets.QPushButton(texto)
            btn.clicked.connect(lambda checked, k=key: self.showOverwriteInfo(k))
            overwrite_btns.addWidget(btn)

        left_layout.addLayout(overwrite_btns)
        
        btns_left = QtWidgets.QHBoxLayout()
        self.btn_load_selected = QtWidgets.QPushButton('Load Selected')
        self.btn_load_selected.clicked.connect(self.load_selected_file)
        self.btn_load_selected.setEnabled(False)
        btns_left.addWidget(self.btn_load_selected)
                
        self.btn_open_file = QtWidgets.QPushButton('Open other video')
        self.btn_open_file.clicked.connect(self.open_video_dialog)
        btns_left.addWidget(self.btn_open_file)
        
        self.btn_check_smb = QtWidgets.QPushButton('Check SMB')
        self.btn_check_smb.clicked.connect(self.open_smb_dialog)
        btns_left.addWidget(self.btn_check_smb)
        
        self.btn_toggle_workframe = QtWidgets.QPushButton('Hide/Show Workframe')
        self.btn_toggle_workframe.clicked.connect(self.toggle_workframe_visibility)
        btns_left.addWidget(self.btn_toggle_workframe)
        
        left_layout.addLayout(btns_left)
        self.main_layout.addWidget(self.left_panel, 0)

        # ---------------- Right main area ----------------
        self.right_widget = QtWidgets.QWidget()
        self.right_stack = QtWidgets.QStackedLayout(self.right_widget)

        self.frame_player_panel = FramePlayerPanel(self)
        self.lyric_panel = LyricVisionPanel(self)

        self.right_stack.addWidget(self.frame_player_panel)
        self.right_stack.addWidget(self.lyric_panel)
        self.right_stack.setCurrentWidget(self.frame_player_panel)

        self.main_layout.addWidget(self.right_widget, 1)
        self.lyric_mode = False

        # ----------------- video state ----------------------
        self.cap = None
        self.fps = 25.0
        self.frame_count = 0
        self.frame_actual = 0
        self.video_name = ""

        # worker thread setup (created when opening video)
        self.worker = None
        self.worker_thread = None

        # OCR thread holders
        self.ocr_thread = None
        self.ocr_worker = None

        # Cut dialog holder
        self._cut_dialog = None

        # keyboard shortcuts
        left = QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_Left), self)
        left.activated.connect(lambda: self.move_seconds(-1))

        right = QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_Right), self)
        right.activated.connect(lambda: self.move_seconds(1))

        # initial layout build (no video yet)
        self.rebuild_thumb_layout()
        self.update_thumbs_visibility()

        # populate left panel combos
        try:
            self.populate_years()
            self.update_lyrics_check_button_visibility()
        except Exception:
            pass

    def showOverwriteInfo(self, key: str):
        times_num = get_overwrite_data(key)
        QtWidgets.QMessageBox.information(
            self, f"Overwrite {times_num[0]} Review: {times_num[1]}", times_num[2]
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # keep overlay sized to thumb_container
        try:
            self.selection_overlay.setGeometry(0, 0, self.thumb_container.width(), self.thumb_container.height())
            self.update_curtain_geometry()
        except Exception:
            pass

    def update_always_on_top(self, state):
        flags = self.windowFlags()
        if state == QtCore.Qt.CheckState.Checked:
            self.setWindowFlags(flags | QtCore.Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(flags & ~QtCore.Qt.WindowType.WindowStaysOnTopHint)
        self.show()

    # ---------------- Left panel helpers ----------------
    def populate_years(self, select_year_str: str = None):
        # List actual folders in BASE_INTERNAL_ROOT that are numeric years >= 2004
        years = []
        try:
            for name in os.listdir(config.BASE_INTERNAL_ROOT):
                # Verifica que sea número, tenga 4 dígitos y sea igual o mayor a 2004
                if name.isdigit() and len(name) == 4 and int(name) >= 2004:
                    years.append(name)
            years.sort()
        except Exception:
            years = [str(y) for y in range(2004, datetime.date.today().year + 1)]

        self.combo_year.blockSignals(True)
        try:
            self.combo_year.clear()
            self.combo_year.addItems(years)
        finally:
            self.combo_year.blockSignals(False)

        self.year_selector_bar.set_years(years)

        target_year = select_year_str if select_year_str else str(datetime.date.today().year)
        idx = self.combo_year.findText(target_year)
        if idx >= 0:
            self.combo_year.setCurrentIndex(idx)
            self.year_selector_bar.select_year(target_year, emit=False)
            self.on_year_changed(idx)
    
    def on_year_bar_selected(self, year: str):
        idx = self.combo_year.findText(year)
        if idx < 0:
            return

        old = self.combo_year.blockSignals(True)
        try:
            self.combo_year.setCurrentIndex(idx)
        finally:
            self.combo_year.blockSignals(old)

        self.on_year_changed(idx)
        
    def on_hidden_year_selected(self, year: str):
        self.year_selector_bar.select_year("", emit=False)
        self.load_year_data(year)
        
    def on_create_new_year_requested(self):
        # Get the highest year currently in the interface
        years = [self.combo_year.itemText(i) for i in range(self.combo_year.count())]
        if not years:
            return

        last_year = max(years)
        next_year = int(last_year) + 1

        msg = f"el siguiente año es {next_year} y se creara con la estrucutura del año pasado, ¿Desea continuar?"
        confirm = QtWidgets.QMessageBox.question(
            self, "Crear nuevo año", msg,
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
        )

        if confirm == QtWidgets.QMessageBox.StandardButton.Yes:
            success, result = year_creator.create_new_year_folder(config.BASE_INTERNAL_ROOT, last_year)
            if success:
                self.populate_years(select_year_str=result)
            else:
                QtWidgets.QMessageBox.warning(self, "Error", result)

    def on_year_changed(self, idx):
        year = self.combo_year.currentText()
        self.load_year_data(year)
        
    def load_year_data(self, year: str):
        self.exit_lyric_mode(uncheck=True)
        self.chk_lyric.hide()
        self.folder_selector_bar.set_folders([])
        self.btn_check.hide()
        
        if not year or year == "(no encontrado)":
            return
        
        year_path = os.path.join(config.BASE_INTERNAL_ROOT, year)
        
        # buscar carpeta que contenga "___[" en su nombre
        found = None
        try:
            for name in os.listdir(year_path):
                full = os.path.join(year_path, name)
                if os.path.isdir(full) and "___[" in name:
                    found = full
                    break
        except Exception:
            found = None
        
        if not found:
            return
        
        try:
            hide_overwrite_1 = int(year) >= 2026
        except ValueError:
            hide_overwrite_1 = False

        self.file_table.set_overwrite_1_hidden(hide_overwrite_1)
        
        # listar subcarpetas de found
        try:
            subs = [os.path.join(found, d) for d in os.listdir(found) if os.path.isdir(os.path.join(found, d))]
            subs_sorted = sorted(subs, key=lambda x: os.path.basename(x))
            self.folder_selector_bar.set_folders(subs_sorted)
            if subs_sorted:
                self.folder_selector_bar.setCurrentRow(0)
        except Exception:
            pass

    def on_master_changed(self, path: str):
        self.exit_lyric_mode(uncheck=True)

        self.update_lyrics_check_button_visibility()

        if not path or path == '(no encontrado)':
            self.file_table.load_folder("")
            self.btn_load_selected.setEnabled(False)
            self._sync_lyric_checkbox_for_folder("")
            return

        base = path
        if not os.path.isdir(base):
            base = os.path.dirname(path)

        self.file_table.load_folder(base)
        self.btn_load_selected.setEnabled(False)
        self._sync_lyric_checkbox_for_folder(base)

    def rescan_current_master_folder(self):
        path = self.folder_selector_bar.current_folder_path()
        if not path or path == '(no encontrado)':
            return

        base = path
        if not os.path.isdir(base):
            base = os.path.dirname(path)

        self.file_table.invalidate_folder(base)
        self.on_master_changed(path)

    def open_etude_file(self):
        year = self.combo_year.currentText()
        px = f"{int(year) - 2003:02d}"
        os.startfile(f"{'E:/_Internal'}/{year}/{px}. identity/{px}. le_etude.overwrite.xlsx")


    def get_reg_ov_temp(self, ov_ver: str):
        py_execute = sys.executable
        cur_fr_script = os.path.dirname(os.path.abspath(__file__))
        child_script = os.path.join(cur_fr_script, "temp_ov_dtrng.pyw")
        year = self.combo_year.currentText()
        CREATE_NO_WINDOW = 0x08000000

        subprocess.Popen(
            [py_execute, child_script, year, ov_ver],
            creationflags=CREATE_NO_WINDOW
        )

    def get_episode_titles_temp(self):
        py_execute = sys.executable  
        cur_fr_script = os.path.dirname(os.path.abspath(__file__))
        child_script = os.path.join(cur_fr_script, "temp_eps_list_get.pyw")
        year = self.combo_year.currentText()
        CREATE_NO_WINDOW = 0x08000000

        subprocess.Popen(
            [py_execute, child_script, year],
            creationflags=CREATE_NO_WINDOW
        )

    def open_about_dialog(self):
        year = self.combo_year.currentText().strip()
        if not year or year == "(no encontrado)":
            QtWidgets.QMessageBox.information(self, "About", "No hay un año válido seleccionado.")
            return

        master_path = self.folder_selector_bar.current_folder_path().strip()
        master_folder_name = ""
        if master_path and master_path != "(no encontrado)":
            master_folder_name = os.path.basename(master_path)

        dlg = AboutSeasonDialog(
            self,
            year=year,
            master_folder_name=master_folder_name,
        )
        dlg.exec()

    def on_file_selected(self):
        has_file = bool(self.file_table.current_file_path())
        self.btn_load_selected.setEnabled(has_file)
        
        if self.lyric_mode and has_file:
            self.load_current_lyric_entry()
        
    def load_selected_file(self):
        self.exit_lyric_mode(uncheck=True)
        video_path = self.file_table.current_file_path()
        if not video_path:
            return

        if not os.path.exists(video_path):
            QtWidgets.QMessageBox.critical(self, 'Error', f'No se encontró: {video_path}')
            return

        self.ensure_workframe_visible()
        self.start_worker_and_open(video_path)
        self.check_curtain.setChecked(True)

    
    def rescan_selected_row(self):
        row = self.file_table.currentRow()

        if row < 0:
            return

        video_path = self.file_table.current_file_path()

        if not video_path:
            return

        try:
            folder = os.path.dirname(video_path)

            if folder in self.file_table._folder_cache:
                cached_rows = self.file_table._folder_cache[folder]

                for i, cached in enumerate(cached_rows):
                    if cached.get("full_path") == video_path:
                        cached_rows[i] = self.file_table._read_file_row(video_path)
                        row_data = cached_rows[i]
                        break
                else:
                    row_data = self.file_table._read_file_row(video_path)
            else:
                row_data = self.file_table._read_file_row(video_path)

            for column, (_, key) in enumerate(self.file_table.COLUMNS):
                item = self.file_table.item(row, column)
                if item is None:
                    item = QtWidgets.QTableWidgetItem()
                    self.file_table.setItem(row, column, item)

                value = str(row_data.get(key, ""))
                if key == "duration" and not value and item.text():
                    value = item.text()

                item.setText(value)

                if key == "filename":
                    item.setData(
                        QtCore.Qt.ItemDataRole.UserRole,
                        row_data.get("full_path", "")
                    )

        except Exception:
            pass

    # ---------------- UI <-> Worker lifecycle ----------------
    def open_video_dialog(self):
        self.exit_lyric_mode(uncheck=True)
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open Video", "", "Video files (*.mp4 *.avi *.mov *.mkv *.wmv *.flv)"
            )
        if not path:
            return
        self.ensure_workframe_visible()
        self.start_worker_and_open(path)
        self.check_curtain.setChecked(True)

    def start_worker_and_open(self, path):
        if self.worker_thread is not None:
            try:
                self.worker.close()
            except Exception:
                pass
            self.worker_thread.quit()
            self.worker_thread.wait()
            self.worker = None
            self.worker_thread = None

        self.worker = VideoWorker(cache_size=config.CACHE_SIZE)
        self.worker_thread = QtCore.QThread()
        self.worker.moveToThread(self.worker_thread)
        self.worker.frames_ready.connect(self.on_frames_ready)
        self.worker.opened.connect(self.on_worker_opened)
        self.worker.error.connect(self.on_worker_error)
        self.worker_thread.started.connect(lambda: self.worker.open(path))
        self.worker_thread.start()

    def on_worker_opened(self, fps, frame_count):
        self.fps = fps
        self.frame_count = frame_count
        self.video_name = os.path.basename(self.worker.path) if hasattr(self.worker, "path") else ""
        self.info_label.setText(f"{self.video_name} - {format_time(self.frame_count / (self.fps or 25.0))}")
        self.frame_actual = 0
        self.rebuild_thumb_layout()
        self.request_current_frames()

    def on_worker_error(self, msg):
        QtWidgets.QMessageBox.critical(self, "Worker error", msg)

    # ---------------- Requests ----------------
    def request_current_frames(self):
        if self.worker is None:
            return
        show_adj = bool(self.check_adjacent.isChecked())
        QtCore.QMetaObject.invokeMethod(self.worker, "request_frames", QtCore.Qt.ConnectionType.QueuedConnection,
                                        QtCore.Q_ARG(int, self.frame_actual), QtCore.Q_ARG(bool, show_adj))

    @QtCore.pyqtSlot(object)
    def on_frames_ready(self, frames_dict):
        visible_indices = list(range(config.NUM_THUMBS)) if self.check_adjacent.isChecked() else [2]
        for idx, arr in frames_dict.items():
            if not (0 <= idx < self.frame_count):
                continue
            rel = idx - self.frame_actual
            label_index = 2 + rel
            if label_index < 0 or label_index >= config.NUM_THUMBS:
                if idx == self.frame_actual:
                    label_index = 2
                else:
                    continue
            if label_index not in visible_indices and not self.check_adjacent.isChecked():
                continue
            try:
                h, w, _ = arr.shape
                qimg = QtGui.QImage(arr.data, w, h, arr.strides[0], QtGui.QImage.Format.Format_RGB888)
                pix = QtGui.QPixmap.fromImage(qimg).scaled(
                    self.thumb_labels[label_index].size(), 
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio, 
                    QtCore.Qt.TransformationMode.SmoothTransformation
                    )
            except Exception:
                pix = QtGui.QPixmap(self.thumb_labels[label_index].width(), self.thumb_labels[label_index].height())
                pix.fill(QtGui.QColor(18,18,18))
            self.thumb_labels[label_index].setPixmap(pix)

        self.rebuild_thumb_layout(apply_cached_sizes=True)

    # ---------------- Layout & rendering ----------------
    def available_thumb_area_width(self):
        container_w = max(200, self.thumb_container.width())
        return container_w

    def compute_thumb_size_for(self, visible_count):
        avail = self.available_thumb_area_width()
        if visible_count <= 0:
            visible_count = 1
        total_spacing = config.THUMB_SPACING * (visible_count - 1)
        w = (avail - total_spacing) / visible_count
        w = int(max(config.MIN_THUMB_WIDTH, min(config.DEFAULT_THUMB_WIDTH, w)))
        h = int(w * config.THUMB_ASPECT)
        return w, h

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                layout.removeWidget(widget)

    def rebuild_thumb_layout(self, apply_cached_sizes=False):
        visible_indices = list(range(config.NUM_THUMBS)) if self.check_adjacent.isChecked() else [2]
        visible_count = len(visible_indices)
        # clear current labels from layout
        while self.thumb_layout.count():
            it = self.thumb_layout.takeAt(0)
            w = it.widget()
            if w:
                self.thumb_layout.removeWidget(w)

        if visible_count == 1:
            self.thumb_layout.addStretch(1)
            self.thumb_layout.addWidget(self.thumb_labels[visible_indices[0]])
            self.thumb_layout.addStretch(1)
        else:
            for i in visible_indices:
                self.thumb_layout.addWidget(self.thumb_labels[i])

        w, h = self.compute_thumb_size_for(visible_count)
        for i, lbl in enumerate(self.thumb_labels):
            if i in visible_indices:
                lbl.setFixedSize(w, h)
                lbl.show()
            else:
                lbl.hide()
        self.thumb_container.update()
        self.update_curtain_geometry()

    def update_thumbs_visibility(self):
        self.rebuild_thumb_layout()
        self.request_current_frames()

    def update_curtain_geometry(self):
        visible_count = config.NUM_THUMBS if self.check_adjacent.isChecked() else 1
        thumb_w, thumb_h = self.compute_thumb_size_for(visible_count)
        w = max(self.thumb_container.width(), 10)
        self.curtain.set_geometry_height(0, 0, w, thumb_h)
        if self.check_curtain.isChecked():
            self.curtain.show()
            self.curtain.raise_()
        else:
            self.curtain.hide()
            
    def update_curtain_visibility(self):
        try:
            self.update_curtain_geometry()
        except Exception:
            if hasattr(self, 'curtain') and hasattr(self, 'thumb_container'):
                vis_count = config.NUM_THUMBS if getattr(self, 'check_adjacent', None) and self.check_adjacent.isChecked() else 1
                w, h = self.compute_thumb_size_for(vis_count) if hasattr(self, 'compute_thumb_size_for') else (config.MIN_THUMB_WIDTH, int(config.MIN_THUMB_WIDTH * config.THUMB_ASPECT))
                self.curtain.set_geometry_height(0, 0, max(self.thumb_container.width(), 10), h)
                if getattr(self, 'check_curtain', None) and self.check_curtain.isChecked():
                    self.curtain.show()
                    self.curtain.raise_()
                else:
                    self.curtain.hide()
        else:
            if hasattr(self, 'curtain') and self.check_curtain.isChecked():
                self.curtain.raise_()

    # ---------------- Navigation ----------------
    def show_frames(self, frame_num):
        self.frame_actual = max(0, min(frame_num, max(0, self.frame_count-1)))
        self.entry_time.setText(format_time(None, frame_num=self.frame_actual, fps=self.fps or 25.0))
        self.request_current_frames()

    def move_frame(self, cantidad):
        if self.worker is None:
            return
        self.frame_actual = max(0, min(self.frame_actual + cantidad, max(0, self.frame_count - 1)))
        self.show_frames(self.frame_actual)

    def move_seconds(self, cantidad):
        if self.worker is None:
            return
        fps = self.fps or 25.0
        self.frame_actual = max(0, min(self.frame_actual + int(fps * cantidad), max(0, self.frame_count - 1)))
        self.show_frames(self.frame_actual)

    def go_to_time(self):
        if self.worker is None:
            return
        s = self.entry_time.text().strip()
        try:
            parts = s.split(':')
            if len(parts) != 3:
                raise ValueError
            h = int(parts[0]); m = int(parts[1])
            sec_ms = parts[2].split('.')
            sec = int(sec_ms[0]); ms = int(sec_ms[1]) if len(sec_ms) > 1 else 0
            time_seconds = h*3600 + m*60 + sec + ms/1000.0
            fps = self.fps or 25.0
            frame = int(time_seconds * fps)
            self.frame_actual = max(0, min(frame, max(0, self.frame_count - 1)))
            self.show_frames(self.frame_actual)
        except Exception:
            QtWidgets.QMessageBox.critical(self, "Error", "Formato de tiempo incorrecto. Use hh:mm:ss.mmm")

    # ---------------- Clipboard / Export (unchanged) ----------------
    def pil_to_dib(self, img_pil: Image.Image) -> bytes:
        img = img_pil.convert("RGB")
        width, height = img.size
        raw = img.tobytes()
        row_bytes_unpadded = width * 3
        row_bytes_padded = (row_bytes_unpadded + 3) & ~3
        padded = bytearray()
        for row in range(height-1, -1, -1):
            start = row * row_bytes_unpadded
            rowdata = raw[start:start + row_bytes_unpadded]
            bgr = bytearray()
            for i in range(0, len(rowdata), 3):
                r, g, b = rowdata[i:i+3]
                bgr.extend((b, g, r))
            bgr.extend(b'\x00' * (row_bytes_padded - row_bytes_unpadded))
            padded += bgr
        header = struct.pack('<IiiHHIIiiII', 40, width, height, 1, 24, 0, len(padded), 2835, 2835, 0, 0)
        return header + bytes(padded)

    def capture_exact_frame(self, frame_num):
        if self.worker is None:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Seleccione un video primero.")
            return None

        got = {}
        loop = QtCore.QEventLoop()
        def _on(frames_dict):
            got.update(frames_dict)
            loop.quit()
        self.worker.frames_ready.connect(_on)
        QtCore.QMetaObject.invokeMethod(
            self.worker, "request_frames", 
            QtCore.Qt.ConnectionType.QueuedConnection,
            QtCore.Q_ARG(int, frame_num), 
            QtCore.Q_ARG(bool, False)
            )
        timer = QtCore.QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(loop.quit)
        timer.start(2000)
        loop.exec()
        try:
            self.worker.frames_ready.disconnect(_on)
        except Exception:
            pass
        arr = got.get(frame_num, None)
        return arr

    def copy_frame_dib(self):
        arr = self.capture_exact_frame(self.frame_actual)
        if arr is None:
            QtWidgets.QMessageBox.warning(self, "Aviso", "No se pudo capturar el frame.")
            return
        img_pil = Image.fromarray(arr)
        dib = self.pil_to_dib(img_pil)
        try:
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_DIB, dib)
            win32clipboard.CloseClipboard()
            QtWidgets.QMessageBox.information(self, "Éxito", "Fotograma exacto copiado al portapapeles.")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"No se pudo copiar al portapapeles:\n{e}")

    def export_frame_png(self):
        arr = self.capture_exact_frame(self.frame_actual)
        if arr is None:
            QtWidgets.QMessageBox.warning(self, "Aviso", "No se pudo capturar el frame.")
            return

        img_pil = Image.fromarray(arr)

        downloads = os.path.join(os.path.expanduser("~"), "Downloads")
        now = datetime.datetime.now()
        filename_base = now.strftime("%Y%m%d_%H%M%S")
        
        tmp_path = os.path.join(downloads, filename_base + ".tmp")
        final_path = os.path.join(downloads, filename_base + ".png")

        try:
            # Guardar primero como temporal
            img_pil.save(tmp_path, "PNG")

            # Renombrar de forma atómica a .png
            os.replace(tmp_path, final_path)

            QtWidgets.QMessageBox.information(
                self,
                "Éxito",
                f"Fotograma exacto exportado como\n{final_path}"
            )

        except Exception as e:
            # Si algo falla, eliminar el temporal si existe
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except:
                    pass

            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                f"No se pudo exportar la imagen.\n{e}"
            )
            
    def copy_time_to_clipboard(self):
        t = self.entry_time.text().strip()
        if t:
            cb = QtWidgets.QApplication.clipboard()
            cb.setText(t)
            QtWidgets.QMessageBox.information(self, "Éxito", "Tiempo copiado al portapapeles.")
        else:
            QtWidgets.QMessageBox.warning(self, "Aviso", "El campo de tiempo está vacío.")

    # ---------------- OCR selection flow ----------------
    def activate_ocr_selection(self):
        # only allowed when adyacentes desactivado
        if self.check_adjacent.isChecked():
            QtWidgets.QMessageBox.warning(self, "Aviso", "Desactive 'Mostrar adyacentes' para usar CCR en la miniatura central.")
            return
        # ensure we have a frame
        if self.worker is None:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Seleccione un video primero.")
            return
        # show overlay and let user select
        self.status.setText('Modo CCR: selecciona el área con el cursor (cruz).')
        self.selection_overlay.start()

    def _on_selection_made(self, rect: QtCore.QRect):
        """
        rect está en coordenadas del overlay (mismo tamaño que thumb_container).
        Mapear al frame original (usar capture_exact_frame para obtener arr de alta resolución)
        """
        # hide overlay cursor
        self.selection_overlay.stop()
        self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
        # get full resolution frame
        arr = self.capture_exact_frame(self.frame_actual)
        if arr is None:
            self.status.setText('No se pudo obtener el fotograma para OCR.')
            return

        # central label geometry
        lbl = self.thumb_labels[2]
        lbl_geom = lbl.geometry()
        # convert rect to label-local coords
        sel_x = rect.x() - lbl_geom.x()
        sel_y = rect.y() - lbl_geom.y()
        sel_w = rect.width()
        sel_h = rect.height()

        if sel_w <= 2 or sel_h <= 2 or sel_x + sel_w < 0 or sel_y + sel_h < 0:
            self.status.setText('Selección inválida.')
            return

        # clamp selection to label area
        sel_x = max(0, sel_x)
        sel_y = max(0, sel_y)
        sel_w = min(sel_w, lbl_geom.width() - sel_x)
        sel_h = min(sel_h, lbl_geom.height() - sel_y)
        if sel_w <= 2 or sel_h <= 2:
            self.status.setText('Selección demasiado pequeña.')
            return

        # map selection pixels from label to original frame
        img_h, img_w, _ = arr.shape
        lbl_w = lbl_geom.width()
        lbl_h = lbl_geom.height()
        # The displayed pixmap uses KeepAspectRatioByExpanding; compute scale and crop offsets
        scale = max(lbl_w / img_w, lbl_h / img_h)
        new_w = img_w * scale
        new_h = img_h * scale
        offset_x = (new_w - lbl_w) / 2.0
        offset_y = (new_h - lbl_h) / 2.0

        # map: image_x = (sel_x + offset_x)/scale
        img_x = int(max(0, min(img_w - 1, (sel_x + offset_x) / scale)))
        img_y = int(max(0, min(img_h - 1, (sel_y + offset_y) / scale)))
        img_x2 = int(max(0, min(img_w, ((sel_x + offset_x) + sel_w) / scale)))
        img_y2 = int(max(0, min(img_h, ((sel_y + offset_y) + sel_h) / scale)))

        if img_x2 - img_x < 2 or img_y2 - img_y < 2:
            self.status.setText('Selección mapeada demasiado pequeña en el fotograma original.')
            return

        crop = arr[img_y:img_y2, img_x:img_x2].copy()
        if crop.size == 0:
            self.status.setText('No se pudo recortar la selección.')
            return

        # prepare params
        params = {
            'scale': config.OCR_SCALE,
            'clahe': config.OCR_USE_CLAHE,
            'clahe_clip': config.OCR_CLAHE_CLIP,
            'denoise_ksize': config.OCR_DENOISE_KSIZE,
            'dilate_iter': config.OCR_DILATE_ITER,
            'invert': config.OCR_INVERT,
            'binarize': config.OCR_BINARIZE,
            'psm': config.OCR_PSM,
            'lang': config.OCR_LANG,
        }

        # run OCR in background
        self.status.setText('Procesando OCR...')
        self._start_ocr_thread(crop, params)

    def _start_ocr_thread(self, crop_arr, params):
        # create worker and thread per job (simple lifecycle)
        worker = OCRWorker()
        thread = QtCore.QThread()
        worker.moveToThread(thread)
        worker.finished.connect(self._on_ocr_finished)
        worker.error.connect(self._on_ocr_error)
        thread.started.connect(lambda: worker.process(crop_arr, params))
        # cleanup when done
        def _cleanup():
            try:
                worker.deleteLater()
            except Exception:
                pass
            try:
                thread.quit()
                thread.wait(1000)
                thread.deleteLater()
            except Exception:
                pass
        worker.finished.connect(_cleanup)
        worker.error.connect(_cleanup)
        thread.start()
        # keep references briefly to avoid GC
        self.ocr_thread = thread
        self.ocr_worker = worker

    @QtCore.pyqtSlot(str)
    def _on_ocr_finished(self, text):
        # clean text: eliminar saltos de línea, normalizar espacios, mantener may/min
        if text is None:
            text = ''
        text_clean = re.sub(r'\s+', ' ', text).strip()
        wrapped = f'“{text_clean}”'
        try:
            QtWidgets.QApplication.clipboard().setText(wrapped)
            self.status.setText('OCR terminado — texto copiado al portapapeles.')
        except Exception as e:
            self.status.setText('OCR terminado pero no se pudo copiar al portapapeles.')
            QtWidgets.QMessageBox.information(self, 'Resultado OCR', wrapped)

    @QtCore.pyqtSlot(str)
    def _on_ocr_error(self, msg):
        self.status.setText('Error en OCR: ' + str(msg))
        QtWidgets.QMessageBox.critical(self, 'Error OCR', str(msg))

    # ---------------- Cut dialog launcher ----------------
    def show_cut_dialog(self):
        if self.worker is None or not hasattr(self.worker, 'path') or not self.worker.path:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Seleccione un video primero.")
            return
        # default start = current entry_time, default end = video duration
        default_start = self.entry_time.text() if self.entry_time.text() else "00:00:00.000"
        try:
            duration_seconds = (self.frame_count / (self.fps or 25.0)) if self.frame_count and self.fps else 0.0
            default_end = format_time(duration_seconds)
        except Exception:
            default_end = "00:00:00.000"

        # get video dims via cv2 (best-effort)
        width = 0
        height = 0
        fps = self.fps or 25.0
        try:
            cap = cv2.VideoCapture(self.worker.path)
            if cap.isOpened():
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
                fps = cap.get(cv2.CAP_PROP_FPS) or fps
            try:
                cap.release()
            except Exception:
                pass
        except Exception:
            pass

        dlg = CutDialog(self, self.worker.path, default_start, default_end, fps, width, height)
        dlg.show()

    
    def edit_selected_metadata(self):
        video_path = self.file_table.current_file_path()
        if not video_path:
            return

        command = ["pythonw", config.RENAME_DIALOG_SCRIPT, video_path]

        try:
            subprocess.Popen(command)
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                f"No se pudo abrir el editor de metadatos.\n\n{e}",
            )

    def ensure_workframe_visible(self):
        if not self.right_widget.isVisible():
            self.toggle_workframe_visibility()

    def toggle_workframe_visibility(self):
        self.right_widget.setVisible(not self.right_widget.isVisible())
        self._set_workframe_visible(self.right_widget.isVisible())

    def _set_workframe_visible(self, visible: bool):
        
        if visible:
            self.left_panel.setFixedWidth(550)
            self.left_panel.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Fixed,
                QtWidgets.QSizePolicy.Policy.Preferred,
            )
            self.main_layout.setStretch(0, 0)
            self.main_layout.setStretch(1, 1)
        else:
            self.left_panel.setMinimumWidth(0)
            self.left_panel.setMaximumWidth(16777215)
            self.left_panel.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Expanding,
                QtWidgets.QSizePolicy.Policy.Preferred,
            )
            self.main_layout.setStretch(0, 1)
            self.main_layout.setStretch(1, 0)
            

        self.left_panel.updateGeometry()
        self.right_widget.updateGeometry()
        self.main_layout.invalidate()
        self.centralWidget().updateGeometry()

    def update_lyrics_check_button_visibility(self):
        path = self.folder_selector_bar.current_folder_path().strip()
        base = path if os.path.isdir(path) else os.path.dirname(path)
        show = bool(base and os.path.basename(base.rstrip("\\/")).lower().endswith("lyrics"))
        self.btn_check.setVisible(show)

    def open_lyrics_manager(self):
        path = self.folder_selector_bar.current_folder_path().strip()
        if not path or path == '(no encontrado)':
            return

        base = path if os.path.isdir(path) else os.path.dirname(path)
        if not os.path.basename(base.rstrip("\\/")).lower().endswith("lyrics"):
            return

        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lirycs_mgr.pyw")
        if not os.path.exists(script_path):
            QtWidgets.QMessageBox.critical(self, "Error", f"No se encontró: {script_path}")
            return

        script_dir = os.path.dirname(script_path)
        pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        launcher = pythonw if os.path.exists(pythonw) else sys.executable

        subprocess.Popen([launcher, script_path, base], cwd=script_dir, close_fds=True)

    def current_smb_folder(self):
        folder = self.file_table.current_folder_path()
        if folder:
            return folder
        video_path = self.file_table.current_file_path()
        return os.path.dirname(video_path) if video_path else ""

    def open_smb_dialog(self):
        folder = self.current_smb_folder()
        if not folder:
            QtWidgets.QMessageBox.information(self, "Check SMB", "No hay carpeta activa.")
            return

        dialog = SMBDialog(folder, self)
        dialog.exec()

    def on_file_count_changed(self, count):
        self.folder_count_label.setText(f"{count} archivos multimedia detectados en esta carpeta")

    def _current_master_folder(self) -> str:
        path = self.folder_selector_bar.current_folder_path().strip()
        if not path or path == '(no encontrado)':
            return ""
        return path if os.path.isdir(path) else os.path.dirname(path)

    def _folder_is_vocal(self, folder: str) -> bool:
        if not folder:
            return False
        return os.path.basename(folder.rstrip("\\/")).lower().endswith("vocals")

    def _sync_lyric_checkbox_for_folder(self, folder: str):
        show = self._folder_is_vocal(folder)

        if not show:
            self.exit_lyric_mode(uncheck=True)
            self.chk_lyric.blockSignals(True)
            self.chk_lyric.setChecked(False)
            self.chk_lyric.blockSignals(False)
            self.chk_lyric.hide()
            return

        self.chk_lyric.show()

    def on_lyric_checkbox_toggled(self, checked: bool):
        if checked:
            if not self._folder_is_vocal(self._current_master_folder()):
                self.chk_lyric.blockSignals(True)
                self.chk_lyric.setChecked(False)
                self.chk_lyric.blockSignals(False)
                return
            self.enter_lyric_mode()
        else:
            self.exit_lyric_mode(uncheck=False)

    def enter_lyric_mode(self):
        folder = self._current_master_folder()
        if not self._folder_is_vocal(folder):
            self.exit_lyric_mode(uncheck=True)
            return

        if self.file_table.rowCount() <= 0:
            self.lyric_panel.clear()
            self.ensure_workframe_visible()
            self.right_stack.setCurrentWidget(self.lyric_panel)
            return

        if self.file_table.currentRow() < 0:
            self.file_table.setCurrentCell(0, 0)

        self.lyric_mode = True
        self.ensure_workframe_visible()
        self.right_stack.setCurrentWidget(self.lyric_panel)
        self.load_current_lyric_entry()

    def exit_lyric_mode(self, uncheck: bool = False):
        self.lyric_mode = False

        if hasattr(self, "right_stack"):
            self.right_stack.setCurrentWidget(self.frame_player_panel)

        if uncheck and hasattr(self, "chk_lyric"):
            self.chk_lyric.blockSignals(True)
            self.chk_lyric.setChecked(False)
            self.chk_lyric.blockSignals(False)

    def _selected_row_index_for_lyrics(self) -> int:
        row = self.file_table.currentRow()
        if row < 0 and self.file_table.rowCount() > 0:
            row = 0
            self.file_table.setCurrentCell(0, 0)
        return row

    def load_current_lyric_entry(self):
        if not self.lyric_mode:
            return

        row = self._selected_row_index_for_lyrics()
        if row < 0:
            self.lyric_panel.clear()
            return

        video_path = self.file_table.current_file_path()
        if not video_path:
            return

        indirect_path = self.lyric_panel.build_indirect_path(video_path)
        total = self.file_table.rowCount()
        name = os.path.basename(indirect_path)

        if os.path.exists(indirect_path):
            try:
                text = self.lyric_panel.read_utf8(indirect_path)
                self.lyric_panel.set_document(video_path, indirect_path, text, row + 1, total)
            except Exception:
                self.lyric_panel.set_missing_document(video_path, indirect_path, row + 1, total)
        else:
            self.lyric_panel.set_missing_document(video_path, indirect_path, row + 1, total)

    def next_lyric_entry(self):
        if self.file_table.rowCount() <= 0:
            return

        row = self._selected_row_index_for_lyrics()
        next_row = 0 if row + 1 >= self.file_table.rowCount() else row + 1
        self.file_table.setCurrentCell(next_row, 0)
        self.load_current_lyric_entry()
        
    def prev_lyric_entry(self):
        if self.file_table.rowCount() <= 0:
            return

        row = self._selected_row_index_for_lyrics()
        # Si la fila actual es 0 o menor (ninguna selección), va a la última fila, si no, resta 1.
        prev_row = self.file_table.rowCount() - 1 if row <= 0 else row - 1
        
        self.file_table.setCurrentCell(prev_row, 0)
        self.load_current_lyric_entry()
    
    def open_settings_dialog(self):
        dlg = SettingsDialog(self)
        if dlg.exec():
            # Update thumb labels list if NUM_THUMBS changed
            if len(self.thumb_labels) != config.NUM_THUMBS:
                # Remove old labels
                for lbl in self.thumb_labels:
                    lbl.setParent(None)
                    lbl.deleteLater()
                self.thumb_labels.clear()

                # Create new labels
                for _ in range(config.NUM_THUMBS):
                    lbl = QtWidgets.QLabel()
                    lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                    lbl.setStyleSheet("background-color: rgb(18,18,18); border: 1px solid #2b2b2b;")
                    lbl.setSizePolicy(
                        QtWidgets.QSizePolicy.Policy.Fixed,
                        QtWidgets.QSizePolicy.Policy.Fixed,
                    )
                    self.thumb_labels.append(lbl)
            
            # Update spacing
            self.thumb_layout.setSpacing(config.THUMB_SPACING)

            # Update worker cache size
            if self.worker:
                self.worker.cache_size = config.CACHE_SIZE

            # Apply immediate UI updates
            self.rebuild_thumb_layout()
            self.update_thumbs_visibility()