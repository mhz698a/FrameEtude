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
from master_toolbar import MasterToolBar
import year_creator

class VideoEtude(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.lyric_mode = False
        self.setWindowTitle("FrameEtude")
        self.resize(1300, 620)
        self._build_ui()
        
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

        # The single-frame viewer is initialized by FramePlayerPanel.

        # populate left panel combos
        try:
            self.populate_years()
            self.update_lyrics_check_button_visibility()
        except Exception:
            pass

    def _build_ui(self):
        # 1. LAYOUT PRINCIPAL VERTICAL (Ventana entera)
        w = QtWidgets.QWidget()
        self.setCentralWidget(w)
        self.main_layout = QtWidgets.QVBoxLayout(w)
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.main_layout.setSpacing(6)
        
        # ---------------- ARRIBA: MasterToolBar Global ----------------
        self.master_toolbar = MasterToolBar(self)
        
        self.master_toolbar.add_simplified_action("Settings", self.open_settings_dialog)
        self.master_toolbar.add_simplified_action("Open other video", self.open_video_dialog)
        self.master_toolbar.add_simplified_action("Refresh", self.rescan_current_master_folder)
        self.master_toolbar.add_simplified_action("Backup", self.run_backup_csv)
        self.master_toolbar.add_simplified_action("Etude", self.open_etude_file)
        self.master_toolbar.add_dropdown_button("Get Ov Reg",
            [
                ("Get Ov1 Reg", lambda: self.get_reg_ov_temp("1")),
                ("Get Ov2 Reg", lambda: self.get_reg_ov_temp("2")),
            ]
        )
        self.master_toolbar.add_simplified_action("Get Titles Ep", self.get_episode_titles_temp)
        self.master_toolbar.add_simplified_action("Gen Plan.md", self.phase_gen_exec)
        self.btn_check = self.master_toolbar.add_simplified_action(
            "Check MD", self.open_lyrics_manager, object_name="CheckMDButton", enabled=False
        )
        self.master_toolbar.add_dropdown_button("Overwrite",
            [
                ("Overwrite P", lambda: self.showOverwriteInfo("ov_0")),
                ("Overwrite I", lambda: self.showOverwriteInfo("ov_1")),
                ("Overwrite II", lambda: self.showOverwriteInfo("ov_2")),
                ("Overwrite III", lambda: self.showOverwriteInfo("ov_3")),
                ("Anachronic Overwrite", lambda: self.showOverwriteInfo(
                    "ov_0", database_path=config.A_OVERWRITE_DATABASE,
                    label="Anachronic Overwrite",
                )),
            ]
        )
        self.action_load_selected = self.master_toolbar.add_simplified_action(
            "Load to Workframe", self.load_selected_file, enabled=False
        )
        self.master_toolbar.add_simplified_action("Check SMB", self.open_smb_dialog)
        self.master_toolbar.add_simplified_action("About", self.open_about_dialog)
        self.chk_lyric = self.master_toolbar.add_simplified_action(
            "View Lyrics?", self.on_lyric_checkbox_toggled, checkable=True, enabled=False
        )
        
        # Añadir la barra arriba de todo en la ventana principal
        self.main_layout.addWidget(self.master_toolbar)

        # ---------------- CENTRO: Splitter (Panel Izquierdo + Reproductor) ----------------
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(6)
        self.splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #2b2b2b;
            }
            QSplitter::handle:hover {
                background-color: #05478a;
            }
        """)
        self.main_layout.addWidget(self.splitter, 1) # Stretch para que ocupe el espacio central

        # --- Panel Izquierdo (Selectores y tabla) ---
        self.left_panel = QtWidgets.QWidget()
        self.left_panel.setMinimumWidth(400)
        left_layout = QtWidgets.QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(4, 4, 4, 4)
        left_layout.setSpacing(6)
        
        self.year_selector_bar = YearSelectorBar()
        self.year_selector_bar.yearSelected.connect(self.on_year_bar_selected)
        self.year_selector_bar.hiddenYearSelected.connect(self.on_hidden_year_selected)
        self.year_selector_bar.createNewYearRequested.connect(self.on_create_new_year_requested)
        
        self.folder_selector_bar = FolderSelectorBar()
        self.folder_selector_bar.folderSelected.connect(self.on_master_changed)
        self.folder_selector_bar.folderChanged.connect(
            lambda: self.load_year_data(self.year_selector_bar.current_year())
        )
        
        self.file_table = FileTableWidget()
        self.file_table.itemSelectionChanged.connect(self.on_file_selected)
        self.file_table.row_count_changed.connect(self.on_file_count_changed)
        
        files_row = QtWidgets.QHBoxLayout()
        files_row.setSpacing(6)
        files_row.addWidget(self.year_selector_bar)
        files_row.addWidget(self.folder_selector_bar)
        files_row.addWidget(self.file_table, 1)
        
        left_layout.addLayout(files_row, 1)

        # --- Right main area (Reproductor / Panel derecho) ---
        self.right_widget = QtWidgets.QWidget()
        self.right_stack = QtWidgets.QStackedLayout(self.right_widget)

        self.frame_player_panel = FramePlayerPanel(self)
        self.lyric_panel = LyricVisionPanel(self)

        self.right_stack.addWidget(self.frame_player_panel)
        self.right_stack.addWidget(self.lyric_panel)
        self.right_stack.setCurrentWidget(self.frame_player_panel)
        
        # Agregar paneles al splitter
        self.right_widget.setMinimumWidth(0)
        self.frame_player_panel.setMinimumWidth(0)
        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.right_widget)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([660, 640])

        # ---------------- ABAJO: Progress Row Global ----------------
        progress_row = QtWidgets.QHBoxLayout()
        progress_row.setContentsMargins(5, 5, 5, 5)
        progress_row.setSpacing(8)
        
        self.folder_count_label = QtWidgets.QLabel("0 MediaFiles")
        self.folder_count_label.setStyleSheet("""
            color: white;
            background: #4f4f4f;
            border-radius: 4px;
            padding: 4px 8px;
            font-style: italic;
        """)
        progress_row.addWidget(self.folder_count_label)
        
        self.metadata_progress_label = QtWidgets.QLabel("0/0")
        progress_row.addWidget(self.metadata_progress_label)

        self.metadata_progress_bar = QtWidgets.QProgressBar()
        self.metadata_progress_bar.setRange(0, 100)
        self.metadata_progress_bar.setValue(0)
        progress_row.addWidget(self.metadata_progress_bar, 1)
        
        # Añadir la barra de progreso abajo del todo en la ventana principal
        self.main_layout.addLayout(progress_row)
        
        self.file_table.set_progress_widgets(
            self.metadata_progress_bar,
            self.metadata_progress_label,
        )
        
        self.status = QtWidgets.QLabel("FrameEtude Loaded Resources")
        self.main_layout.addWidget(self.status)
        

    def showOverwriteInfo(self, key: str, database_path: str | None = None,
                          label: str = "Overwrite"):
        if database_path is None:
            times_num = get_overwrite_data(key)
        else:
            times_num = get_overwrite_data(
                key, database_path=database_path, database_label=label
            )
        QtWidgets.QMessageBox.information(
            self, f"{label} {times_num[0]} Review: {times_num[1]}", times_num[2]
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # keep overlay sized to thumb_container
        try:
            self.selection_overlay.setGeometry(0, 0, self.frame_viewport.width(), self.frame_viewport.height())
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
        # Listar carpetas reales en BASE_INTERNAL_ROOT que sean años numéricos >= 2004
        years = []
        try:
            for name in os.listdir(config.BASE_INTERNAL_ROOT):
                if name.isdigit() and len(name) == 4 and int(name) >= 2004:
                    years.append(name)
            years.sort()
        except Exception:
            years = [str(y) for y in range(2004, datetime.date.today().year + 1)]

        self.year_selector_bar.set_years(years)

        target_year = select_year_str if select_year_str else (years[-1] if years else str(datetime.date.today().year))
        
        self.year_selector_bar.select_year(target_year, emit=False)
        self.load_year_data(target_year)
    
    def on_year_bar_selected(self, year: str):
        if not year:
            return
        self.load_year_data(year)
        
    def on_hidden_year_selected(self, year: str):
        self.year_selector_bar.select_year("", emit=False)
        self.load_year_data(year)
        
    def on_create_new_year_requested(self):
        # Get the highest year currently in the interface
        years = self.year_selector_bar.get_years()
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
        
    def load_year_data(self, year: str):
        self.exit_lyric_mode(uncheck=True)
        self.chk_lyric.setEnabled(False)
        self.folder_selector_bar.set_folders([])
        self.btn_check.setEnabled(False)
        
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
            self.action_load_selected.setEnabled(False)
            self._sync_lyric_checkbox_for_folder("")
            return

        base = path
        if not os.path.isdir(base):
            base = os.path.dirname(path)

        self.file_table.load_folder(base)
        self.action_load_selected.setEnabled(False)
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
        year = self.year_selector_bar.current_year()
        px = f"{int(year) - 2003:02d}"
        os.startfile(f"{'E:/_Internal'}/{year}/{px}. identity/{px}. le_etude.overwrite.xlsx")

    def phase_gen_exec(self):
        py_execute = sys.executable
        year = self.year_selector_bar.current_year()
        cur_fr_script = os.path.dirname(os.path.abspath(__file__))
        child_script = os.path.join(cur_fr_script, "phase_gen.pyw")
        CREATE_NO_WINDOW = 0x08000000
        
        subprocess.Popen(
            [py_execute, child_script, year],
            creationflags=CREATE_NO_WINDOW
        )

    def get_reg_ov_temp(self, ov_ver: str):
        py_execute = sys.executable
        cur_fr_script = os.path.dirname(os.path.abspath(__file__))
        child_script = os.path.join(cur_fr_script, "temp_ov_dtrng.pyw")
        year = self.year_selector_bar.current_year()
        CREATE_NO_WINDOW = 0x08000000

        subprocess.Popen(
            [py_execute, child_script, year, ov_ver],
            creationflags=CREATE_NO_WINDOW
        )

    def get_episode_titles_temp(self):
        py_execute = sys.executable  
        cur_fr_script = os.path.dirname(os.path.abspath(__file__))
        child_script = os.path.join(cur_fr_script, "temp_eps_list_get.pyw")
        year = self.year_selector_bar.current_year()
        CREATE_NO_WINDOW = 0x08000000

        subprocess.Popen(
            [py_execute, child_script, year],
            creationflags=CREATE_NO_WINDOW
        )

    def open_about_dialog(self):
        year = self.year_selector_bar.current_year().strip()
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
        self.action_load_selected.setEnabled(has_file)

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

        self.frame_canvas.clear_frame()
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
        
        self.video_slider.blockSignals(True)
        self.video_slider.setRange(0, self.frame_count - 1)
        self.video_slider.setValue(0)
        self.video_slider.blockSignals(False)
        
        self.request_current_frames()

    def on_worker_error(self, msg):
        QtWidgets.QMessageBox.critical(self, "Worker error", msg)

    # ---------------- Requests ----------------
    def request_current_frames(self):
        if self.worker is None:
            return
        QtCore.QMetaObject.invokeMethod(
            self.worker,
            "request_frames",
            QtCore.Qt.ConnectionType.QueuedConnection,
            QtCore.Q_ARG(int, self.frame_actual),
            QtCore.Q_ARG(bool, False),
        )

    @QtCore.pyqtSlot(object)
    def on_frames_ready(self, frames_dict):
        arr = frames_dict.get(self.frame_actual)
        if arr is None:
            return

        try:
            height, width, _ = arr.shape
            image = QtGui.QImage(
                arr.data,
                width,
                height,
                arr.strides[0],
                QtGui.QImage.Format.Format_RGB888,
            )
            self.frame_canvas.set_frame_image(image)
            self.update_curtain_geometry()
        except Exception as error:
            self.frame_canvas.clear_frame()
            self.status.setText(f"No se pudo mostrar el fotograma: {error}")

    # ---------------- Single-frame layout & curtain ----------------
    def update_curtain_geometry(self):
        if not hasattr(self, "frame_canvas"):
            return
        self.frame_canvas.update_curtain_geometry()

    def update_curtain_visibility(self):
        if hasattr(self, "frame_canvas") and hasattr(self, "check_curtain"):
            self.frame_canvas.set_curtain_enabled(self.check_curtain.isChecked())
            self.update_curtain_geometry()

    # ---------------- Navigation ----------------
    def show_frames(self, frame_num):
        self.frame_actual = max(0, min(frame_num, max(0, self.frame_count-1)))
        self.entry_time.setText(format_time(None, frame_num=self.frame_actual, fps=self.fps or 25.0))
        
        self.video_slider.blockSignals(True)
        self.video_slider.setValue(self.frame_actual)
        self.video_slider.blockSignals(False)
        
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

    def on_slider_released(self):
        if self.worker is None:
            return
        self.show_frames(self.video_slider.value())

    def on_slider_value_changed(self, value):
        if self.worker is None:
            return
        # Solo actualizar el texto del tiempo mientras se arrastra para rendimiento
        self.entry_time.setText(format_time(None, frame_num=value, fps=self.fps or 25.0))

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
        lbl = self.frame_canvas
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

        # Map the selected area against the image fitted inside the label (KeepAspectRatio).
        img_h, img_w, _ = arr.shape
        lbl_w = lbl_geom.width()
        lbl_h = lbl_geom.height()
        if lbl_w <= 0 or lbl_h <= 0:
            self.status.setText('El área del visor no tiene un tamaño válido.')
            return

        scale = min(lbl_w / img_w, lbl_h / img_h)
        rendered_w = img_w * scale
        rendered_h = img_h * scale
        offset_x = (lbl_w - rendered_w) / 2.0
        offset_y = (lbl_h - rendered_h) / 2.0

        selection_left = max(float(sel_x), offset_x)
        selection_top = max(float(sel_y), offset_y)
        selection_right = min(float(sel_x + sel_w), offset_x + rendered_w)
        selection_bottom = min(float(sel_y + sel_h), offset_y + rendered_h)

        if selection_right - selection_left <= 2 or selection_bottom - selection_top <= 2:
            self.status.setText('La selección no contiene área visible del fotograma.')
            return

        img_x = int(max(0, min(img_w - 1, (selection_left - offset_x) / scale)))
        img_y = int(max(0, min(img_h - 1, (selection_top - offset_y) / scale)))
        img_x2 = int(max(0, min(img_w, (selection_right - offset_x) / scale)))
        img_y2 = int(max(0, min(img_h, (selection_bottom - offset_y) / scale)))

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

        self.file_table.launch_rename_dialog(video_path)

    def ensure_workframe_visible(self):
        if not self.right_widget.isVisible():
            self.toggle_workframe_visibility()

    def toggle_workframe_visibility(self):
        visible = not self.right_widget.isVisible()
        self.right_widget.setVisible(visible)
        self._set_workframe_visible(visible)

    def _set_workframe_visible(self, visible: bool):
        self.right_widget.setVisible(visible)
        if visible:
            total_w = self.splitter.width()
            if total_w > 700:
                self.splitter.setSizes([660, total_w - 660])
            else:
                self.splitter.setSizes([660, 640])
        
        self.left_panel.updateGeometry()
        self.right_widget.updateGeometry()
        self.splitter.updateGeometry()
            

        self.left_panel.updateGeometry()
        self.right_widget.updateGeometry()
        self.main_layout.invalidate()
        self.centralWidget().updateGeometry()

    def _get_valid_lyrics_base_path(self):
        path = self.folder_selector_bar.current_folder_path().strip()
        
        # Ignorar rutas vacías o el placeholder de error
        if not path or path == '(no encontrado)':
            return None

        # Obtener el directorio base
        base = path if os.path.isdir(path) else os.path.dirname(path)
        if not base:
            return None

        # Verificar si el nombre de la carpeta termina en los sufijos permitidos
        folder_name = os.path.basename(base.rstrip("\\/")).lower()
        
        if folder_name.endswith(config.VALID_FOLDER_SUFFIXES):
            return base
            
        return None

    def update_lyrics_check_button_visibility(self):
        is_valid = self._get_valid_lyrics_base_path() is not None
        self.btn_check.setEnabled(is_valid)

    def open_lyrics_manager(self):
        base = self._get_valid_lyrics_base_path()
        if not base:
            return

        script_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(script_dir, "lirycs_mgr.pyw") 

        if not os.path.exists(script_path):
            QtWidgets.QMessageBox.critical(self, "Error", f"No se encontró el archivo:\n{script_path}")
            return

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
        self.folder_count_label.setText(f"{count} MediaFiles")

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
            self.chk_lyric.setEnabled(False)
            return

        self.chk_lyric.setEnabled(True)

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
    
    def run_backup_csv(self):
        py_execute = sys.executable
        cur_fr_script = os.path.dirname(os.path.abspath(__file__))
        child_script = os.path.join(cur_fr_script, "backup_csv.pyw")
        CREATE_NO_WINDOW = 0x08000000
        
        subprocess.Popen(
            [py_execute, child_script],
            creationflags=CREATE_NO_WINDOW
        )
    
    def open_settings_dialog(self):
        dlg = SettingsDialog(self)
        if dlg.exec() and self.worker:
            self.worker.cache_size = config.CACHE_SIZE
