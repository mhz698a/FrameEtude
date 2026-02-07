# videoetude_pyqt_workered_with_ocr_v2.py
import ctypes, sys, os, re, struct, datetime, cv2, win32clipboard, pywinstyles
# Windows AppID (taskbar icon grouping)
myappid = 'etude_video.FrameEtude.VideoFramesInspector.v2'
try: ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception: pass
from PIL import Image
from PyQt5 import QtCore, QtGui, QtWidgets
from config import *
from utils import *
from ocr_lib import OCRWorker, SelectionOverlay
from cut_lib import FFmpegWorker
from curtain_lib import CurtainOverlay
from vidwk_lib import VideoWorker

# -----------------------
# Cut Dialog (no bloqueante)
# -----------------------
class CutDialog(QtWidgets.QDialog):
    start_cut_signal = QtCore.pyqtSignal(dict)

    def __init__(self, parent: 'VideoEtude', video_path: str, default_start: str, default_end: str, fps: float, width: int, height: int):
        super().__init__(parent)
        self.setWindowTitle("Recortar video")
        self.setModal(False)
        self.setWindowModality(QtCore.Qt.NonModal)
        self.resize(560, 240)
        self.video_path = video_path
        self.fps = fps
        self.width = width
        self.height = height

        layout = QtWidgets.QVBoxLayout(self)

        form = QtWidgets.QFormLayout()

        # Start input + button to use current timestamp
        h_start = QtWidgets.QHBoxLayout()
        self.input_start = QtWidgets.QLineEdit(default_start)
        self.input_start.setToolTip("Inicio del recorte (hh:mm:ss.mmm)")
        h_start.addWidget(self.input_start)
        btn_start_now = QtWidgets.QPushButton("⤴")
        btn_start_now.setFixedWidth(36)
        btn_start_now.setToolTip("Usar timestamp actual del video")
        btn_start_now.clicked.connect(self._use_current_as_start)
        h_start.addWidget(btn_start_now)
        form.addRow("Inicio (hh:mm:ss.mmm):", h_start)

        # End input + button to use current timestamp
        h_end = QtWidgets.QHBoxLayout()
        self.input_end = QtWidgets.QLineEdit(default_end)
        self.input_end.setToolTip("Fin del recorte (hh:mm:ss.mmm)")
        h_end.addWidget(self.input_end)
        btn_end_now = QtWidgets.QPushButton("⤴")
        btn_end_now.setFixedWidth(36)
        btn_end_now.setToolTip("Usar timestamp actual del video")
        btn_end_now.clicked.connect(self._use_current_as_end)
        h_end.addWidget(btn_end_now)
        form.addRow("Final (hh:mm:ss.mmm):", h_end)

        # checkboxes
        self.chk_opt = QtWidgets.QCheckBox("Optimizar para compartir")
        self.chk_black = QtWidgets.QCheckBox("Añadir pantalla negra de 5 segundos al final")

        # path selection with browse and quick-open
        hbox_path = QtWidgets.QHBoxLayout()
        self.line_out = QtWidgets.QLineEdit()
        base_dir = os.path.dirname(video_path) or os.path.expanduser("~")
        default_name = os.path.splitext(os.path.basename(video_path))[0] + "_cut.mp4"
        default_out = os.path.join(base_dir, default_name)
        self.line_out.setText(default_out)
        self.line_out.setToolTip("Ruta de salida para el recorte")
        btn_browse = QtWidgets.QPushButton("...")
        btn_browse.setFixedWidth(36)
        btn_browse.setToolTip("Seleccionar ruta de salida")
        btn_browse.clicked.connect(self.on_browse_out)
        btn_open_folder = QtWidgets.QPushButton("_")
        btn_open_folder.setFixedWidth(36)
        btn_open_folder.setToolTip("Abrir carpeta de salida en el Explorador")
        btn_open_folder.clicked.connect(self.on_open_out_folder)
        hbox_path.addWidget(self.line_out)
        hbox_path.addWidget(btn_browse)
        hbox_path.addWidget(btn_open_folder)

        form.addRow("Guardar en:", hbox_path)

        layout.addLayout(form)

        layout.addWidget(self.chk_opt)
        layout.addWidget(self.chk_black)

        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        # footer buttons
        btns = QtWidgets.QHBoxLayout()
        btns.addStretch(1)
        self.btn_cut = QtWidgets.QPushButton("Cut")
        self.btn_cancel = QtWidgets.QPushButton("Cancel")

        # size and styles
        self.btn_cut.setFixedWidth(80)
        self.btn_cancel.setFixedWidth(80)

        # ensure disabled style slightly darker (also set earlier in app stylesheet, but keep here for local override)
        btn_style = """
            QPushButton { background-color: #3a3a3c; border: 1px solid #2b2b2d; padding: 6px 10px; border-radius: 6px; color: #e6e6e6; }
            QPushButton:disabled { background-color: #262626; color: #777777; }
        """
        self.btn_cut.setStyleSheet(btn_style)
        self.btn_cancel.setStyleSheet(btn_style)
        btn_browse.setStyleSheet("QPushButton:disabled { background-color: #262626; color: #777777; }")
        btn_open_folder.setStyleSheet("QPushButton:disabled { background-color: #262626; color: #777777; }")

        self.btn_cut.clicked.connect(self.on_cut_clicked)
        self.btn_cancel.clicked.connect(self.on_cancel_clicked)
        btns.addWidget(self.btn_cut)
        btns.addWidget(self.btn_cancel)
        layout.addLayout(btns)

        # Worker and thread placeholders
        self._ff_thread = None
        self._ff_worker = None
        self._cut_started = False

        # signals
        self.start_cut_signal.connect(self._start_ff_worker)

    def _use_current_as_start(self):
        p = self.parent()
        if p is None:
            return
        cur = p.entry_time.text().strip() if getattr(p, 'entry_time', None) and p.entry_time.text().strip() else None
        if cur:
            self.input_start.setText(cur)
            return
        # fallback compute from frame
        try:
            frm = getattr(p, 'frame_actual', 0)
            fps = getattr(p, 'fps', 25.0) or 25.0
            s = format_time(None, frame_num=frm, fps=fps)
            self.input_start.setText(s)
        except Exception:
            pass

    def _use_current_as_end(self):
        p = self.parent()
        if p is None:
            return
        cur = p.entry_time.text().strip() if getattr(p, 'entry_time', None) and p.entry_time.text().strip() else None
        if cur:
            self.input_end.setText(cur)
            return
        # fallback compute from frame
        try:
            frm = getattr(p, 'frame_actual', 0)
            fps = getattr(p, 'fps', 25.0) or 25.0
            s = format_time(None, frame_num=frm, fps=fps)
            self.input_end.setText(s)
        except Exception:
            pass

    def on_browse_out(self):
        start_dir = os.path.dirname(self.line_out.text()) if self.line_out.text() else os.path.dirname(self.video_path) or os.path.expanduser("~")
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Guardar recorte como", start_dir, "Video MP4 (*.mp4);;All files (*)")
        if path:
            self.line_out.setText(path)

    def on_open_out_folder(self):
        path = self.line_out.text().strip()
        if not path:
            # open default folder (video folder)
            target = os.path.dirname(self.video_path) or os.path.expanduser("~")
        else:
            # if path is a file path, get dirname; if directory, use it
            if os.path.isdir(path):
                target = path
            else:
                target = os.path.dirname(path) or os.path.expanduser("~")
        try:
            if not os.path.exists(target):
                QtWidgets.QMessageBox.warning(self, "Aviso", f"No existe la carpeta: {target}")
                return
            os.startfile(target)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"No se pudo abrir la carpeta:\n{e}")

    def on_cut_clicked(self):
        if self._cut_started:
            return
        try:
            s = self.input_start.text().strip()
            e = self.input_end.text().strip()
            start_sec = parse_time_to_seconds(s)
            end_sec = parse_time_to_seconds(e)
            out_path = self.line_out.text().strip()
            if not out_path:
                QtWidgets.QMessageBox.warning(self, "Aviso", "Selecciona una ruta de salida.")
                return
            params = {
                'in_path': self.video_path,
                'out_path': out_path,
                'start_sec': start_sec,
                'end_sec': end_sec,
                'optimize_for_share': self.chk_opt.isChecked(),
                'add_black': self.chk_black.isChecked(),
                'fps': self.fps,
                'width': self.width,
                'height': self.height
            }
        except Exception:
            QtWidgets.QMessageBox.critical(self, "Error", "Formato de tiempo inválido. Use hh:mm:ss.mmm")
            return

        self.btn_cut.setEnabled(False)
        self._cut_started = True
        self.progress.setValue(0)
        self.start_cut_signal.emit(params)

    def on_cancel_clicked(self):
        # behavior: if cutting not started -> close dialog
        # if cutting started -> request cancel
        if not self._cut_started:
            self.close()
            return
        # request cancel on worker
        if self._ff_worker is not None:
            try:
                self._ff_worker.cancel()
            except Exception:
                pass
        self.btn_cancel.setEnabled(False)
        self.progress.setFormat("Cancelando...")

    @QtCore.pyqtSlot(dict)
    def _start_ff_worker(self, params):
        # create worker and thread
        worker = FFmpegWorker()
        thread = QtCore.QThread()
        worker.moveToThread(thread)
        worker.progress.connect(self.progress.setValue)
        worker.finished.connect(self._on_finished)
        worker.error.connect(self._on_error)
        thread.started.connect(lambda: worker.run_cut(params))

        # cleanup
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

        # keep refs
        self._ff_thread = thread
        self._ff_worker = worker
        thread.start()

    @QtCore.pyqtSlot(str)
    def _on_finished(self, out_path):
        self.progress.setValue(100)
        QtWidgets.QMessageBox.information(self, "Recorte completado", f"Recorte guardado en:\n{out_path}")
        self.btn_cut.setEnabled(True)
        self.btn_cancel.setEnabled(True)
        self._cut_started = False

    @QtCore.pyqtSlot(str)
    def _on_error(self, tb):
        QtWidgets.QMessageBox.critical(self, "Error en recorte", f"Ocurrió un error:\n\n{tb}")
        self.btn_cut.setEnabled(True)
        self.btn_cancel.setEnabled(True)
        self._cut_started = False

# -----------------------
# UI: VideoEtude main window
# -----------------------
class VideoEtude(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FrameEtude")
        screen = QtWidgets.QApplication.primaryScreen().availableGeometry()
        screen_w = screen.width()
        screen_h = screen.height()
        self.setMaximumSize(screen_w, screen_h)
        init_w = min(int(DEFAULT_THUMB_WIDTH * 1.6) + CONTROL_WIDTH_ESTIMATE, screen_w - 80)
        init_h = min(820, screen_h - 80)
        self.resize(915, 500)
        pywinstyles.change_header_color(self, color="#232629")

        # central layout: left panel + right main area
        w = QtWidgets.QWidget()
        self.setCentralWidget(w)
        self.main_layout = QtWidgets.QHBoxLayout(w)
        self.main_layout.setContentsMargins(8,8,8,8)
        self.main_layout.setSpacing(8)

        # ---------------- Left panel ----------------
        self.left_panel = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(4,4,4,4)
        left_layout.setSpacing(6)

        left_layout.addWidget(QtWidgets.QLabel('<b>Explorador E:\\_Internal</b>'))
        self.combo_year = QtWidgets.QComboBox(); left_layout.addWidget(self.combo_year)
        self.combo_year.currentIndexChanged.connect(self.on_year_changed)

        left_layout.addWidget(QtWidgets.QLabel('Carpeta maestra (___[...])'))
        self.combo_master = QtWidgets.QComboBox(); left_layout.addWidget(self.combo_master)
        self.combo_master.currentIndexChanged.connect(self.on_master_changed)

        left_layout.addWidget(QtWidgets.QLabel('Archivos (selección única)'))
        self.list_files = QtWidgets.QListWidget()
        self.list_files.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.list_files.itemSelectionChanged.connect(self.on_file_selected)
        left_layout.addWidget(self.list_files, 1)
        
        btns_left = QtWidgets.QHBoxLayout()
        self.btn_load_selected = QtWidgets.QPushButton('Load Selected')
        self.btn_load_selected.clicked.connect(self.load_selected_file)
        self.btn_load_selected.setEnabled(False)
        btns_left.addWidget(self.btn_load_selected)
        
        self.btn_open_file = QtWidgets.QPushButton('Open other video')
        self.btn_open_file.clicked.connect(self.open_video_dialog)
        btns_left.addWidget(self.btn_open_file)
        left_layout.addLayout(btns_left)
        
        # Asegurarse de que el espacio debajo de los botones se distribuye correctamente
        left_layout.setStretch(0, 0)  # El primer elemento (etiqueta) no se expande
        left_layout.setStretch(1, 1)  # El QListWidget debe ocupar todo el espacio disponible
        
        # move original "Open Video" into left panel for backwards compatibility label
        # (we already have btn_open_file above)

        self.main_layout.addWidget(self.left_panel, 0)

        # ---------------- Right main area ----------------
        self.right_widget = QtWidgets.QWidget()
        self.right_layout = QtWidgets.QVBoxLayout(self.right_widget)
        self.right_layout.setContentsMargins(0,0,0,0)
        self.right_layout.setSpacing(8)

        # Info (label)
        self.info_label = QtWidgets.QLabel("Nombre - Duración")
        self.right_layout.addWidget(self.info_label)

        # thumbnail container
        self.thumb_container = QtWidgets.QWidget()
        self.thumb_layout = QtWidgets.QHBoxLayout(self.thumb_container)
        self.thumb_layout.setContentsMargins(0,0,0,0)
        self.thumb_layout.setSpacing(THUMB_SPACING)
        self.thumb_container.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.right_layout.addWidget(self.thumb_container)

        # labels
        self.thumb_labels = []
        for _ in range(NUM_THUMBS):
            lbl = QtWidgets.QLabel()
            lbl.setAlignment(QtCore.Qt.AlignCenter)
            lbl.setStyleSheet("background-color: rgb(18,18,18); border: 1px solid #2b2b2b;")
            lbl.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
            self.thumb_labels.append(lbl)

        # curtain overlay
        self.curtain = CurtainOverlay(self.thumb_container)
        self.curtain.hide()

        # Selection overlay (for OCR selection)
        self.selection_overlay = SelectionOverlay(self.thumb_container)
        self.selection_overlay.setGeometry(0, 0, 800, 200)  # will be updated in resize
        self.selection_overlay.selection_made.connect(self._on_selection_made)

        # controls: navigation (first row)
        controls_nav = QtWidgets.QHBoxLayout()
        btn_fc = QtWidgets.QPushButton("Fc"); btn_fc.clicked.connect(self.copy_frame_dib); controls_nav.addWidget(btn_fc)
        for txt, func in [("-90", lambda: self.move_seconds(-90)), 
                          ("-60", lambda: self.move_seconds(-60)), 
                          ("-30", lambda: self.move_seconds(-30)),
                          ("-01", lambda: self.move_seconds(-1)), 
                          ("-Fr1", lambda: self.move_frame(-1))]:
            b = QtWidgets.QPushButton(txt); b.clicked.connect(func); controls_nav.addWidget(b)
        self.entry_time = QtWidgets.QLineEdit(); self.entry_time.setFixedWidth(140); self.entry_time.returnPressed.connect(self.go_to_time)
        controls_nav.addWidget(self.entry_time)
        for txt, func in [("+Fr1", lambda: self.move_frame(1)), 
                          ("+01", lambda: self.move_seconds(1)),
                          ("+30", lambda: self.move_seconds(30)), 
                          ("+60", lambda: self.move_seconds(60)),
                          ("+90", lambda: self.move_seconds(90))]:
            b = QtWidgets.QPushButton(txt); b.clicked.connect(func); controls_nav.addWidget(b)

        self.right_layout.addLayout(controls_nav)

        # controls: actions (second row) -> here go Tm, Ex, CCR and checkboxes
        controls_actions = QtWidgets.QHBoxLayout()
        btn_copy_time = QtWidgets.QPushButton("Copy Timestamp"); btn_copy_time.clicked.connect(self.copy_time_to_clipboard); controls_actions.addWidget(btn_copy_time)
        btn_export = QtWidgets.QPushButton("Ex"); btn_export.clicked.connect(self.export_frame_png); controls_actions.addWidget(btn_export)

        # OCR CCR button
        btn_ccr = QtWidgets.QPushButton("CCR")
        btn_ccr.clicked.connect(self.activate_ocr_selection)
        controls_actions.addWidget(btn_ccr)

        # New Cut button
        btn_cut_main = QtWidgets.QPushButton("Cut")
        btn_cut_main.clicked.connect(self.show_cut_dialog)
        controls_actions.addWidget(btn_cut_main)

        # show adjacent + hide curtain
        self.check_adjacent = QtWidgets.QCheckBox("Mostrar adyacentes")
        self.check_adjacent.setChecked(False)
        self.check_adjacent.stateChanged.connect(self.update_thumbs_visibility)
        controls_actions.addWidget(self.check_adjacent)
        
        self.check_curtain = QtWidgets.QCheckBox("Hide"); self.check_curtain.setChecked(False)
        self.check_curtain.stateChanged.connect(self.update_curtain_visibility)
        controls_actions.addWidget(self.check_curtain)
        
        self.check_always_on_top = QtWidgets.QCheckBox("Always on top")
        self.check_always_on_top.setChecked(False)
        self.check_always_on_top.stateChanged.connect(self.update_always_on_top)
        controls_actions.addWidget(self.check_always_on_top)


        # align remaining to left and add stretch
        controls_actions.addStretch(1)
        self.right_layout.addLayout(controls_actions)

        self.status = QtWidgets.QLabel(""); self.right_layout.addWidget(self.status)

        self.main_layout.addWidget(self.right_widget, 1)

        # video state
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
        left = QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Left), self); left.activated.connect(lambda: self.move_seconds(-1))
        right = QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Right), self); right.activated.connect(lambda: self.move_seconds(1))

        # initial layout build (no video yet)
        self.rebuild_thumb_layout()
        self.update_thumbs_visibility()

        # populate left panel combos
        try:
            self.populate_years()
        except Exception:
            pass

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
        if state == QtCore.Qt.Checked:
            self.setWindowFlags(flags | QtCore.Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(flags & ~QtCore.Qt.WindowStaysOnTopHint)
        self.show()

    # ---------------- Left panel helpers ----------------
    def populate_years(self):
        self.combo_year.clear()
        if not os.path.exists(BASE_INTERNAL_ROOT):
            self.combo_year.addItem('(no encontrado)')
            return
        try:
            entries = [d for d in os.listdir(BASE_INTERNAL_ROOT) if os.path.isdir(os.path.join(BASE_INTERNAL_ROOT, d))]
            entries_sorted = sorted(entries)
            for e in entries_sorted:
                self.combo_year.addItem(e)
        except Exception:
            pass

    def on_year_changed(self, idx):
        self.combo_master.clear()
        year = self.combo_year.currentText()
        if not year or year == '(no encontrado)':
            return
        year_path = os.path.join(BASE_INTERNAL_ROOT, year)
        # buscar carpeta que contenga '___[' en su nombre
        found = None
        try:
            for name in os.listdir(year_path):
                full = os.path.join(year_path, name)
                if os.path.isdir(full) and '___[' in name:
                    found = full
                    break
        except Exception:
            found = None
        if not found:
            self.combo_master.addItem('(no encontrado)')
            return
        # listar subcarpetas de found
        try:
            subs = [d for d in os.listdir(found) if os.path.isdir(os.path.join(found, d))]
            subs_sorted = sorted(subs)
            for s in subs_sorted:
                self.combo_master.addItem(os.path.join(found, s))
        except Exception:
            self.combo_master.addItem('(no encontrado)')

    def on_master_changed(self, idx):
        self.list_files.clear()
        path = self.combo_master.currentText()
        if not path or path == '(no encontrado)':
            return
        # if the combo contains full paths, use them
        base = path
        if not os.path.isdir(base):
            # try splitting if stored as joined path
            base = os.path.dirname(path)
        try:
            files = [f for f in os.listdir(base) if os.path.isfile(os.path.join(base, f)) and os.path.splitext(f)[1].lower() in VIDEO_EXTS]
            files_sorted = sorted(files)
            for f in files_sorted:
                item = QtWidgets.QListWidgetItem(f)
                self.list_files.addItem(item)
        except Exception:
            pass

    def on_file_selected(self):
        sel = self.list_files.selectedItems()
        self.btn_load_selected.setEnabled(len(sel) == 1)

    def load_selected_file(self):
        sel = self.list_files.selectedItems()
        if not sel:
            return
        filename = sel[0].text()
        base = self.combo_master.currentText()
        video_path = os.path.join(base, filename) if os.path.isdir(base) else os.path.join(os.path.dirname(base), filename)
        if not os.path.exists(video_path):
            QtWidgets.QMessageBox.critical(self, 'Error', f'No se encontró: {video_path}')
            return
        self.start_worker_and_open(video_path)
        # ensure curtain visible
        self.check_curtain.setChecked(True)

    # ---------------- UI <-> Worker lifecycle ----------------
    def open_video_dialog(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open Video", "", "Video files (*.mp4 *.avi *.mov *.mkv *.wmv *.flv)")
        if not path:
            return
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

        self.worker = VideoWorker(cache_size=CACHE_SIZE)
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
        QtCore.QMetaObject.invokeMethod(self.worker, "request_frames", QtCore.Qt.QueuedConnection,
                                        QtCore.Q_ARG(int, self.frame_actual), QtCore.Q_ARG(bool, show_adj))

    @QtCore.pyqtSlot(object)
    def on_frames_ready(self, frames_dict):
        visible_indices = list(range(NUM_THUMBS)) if self.check_adjacent.isChecked() else [2]
        for idx, arr in frames_dict.items():
            if not (0 <= idx < self.frame_count):
                continue
            rel = idx - self.frame_actual
            label_index = 2 + rel
            if label_index < 0 or label_index >= NUM_THUMBS:
                if idx == self.frame_actual:
                    label_index = 2
                else:
                    continue
            if label_index not in visible_indices and not self.check_adjacent.isChecked():
                continue
            try:
                h, w, _ = arr.shape
                qimg = QtGui.QImage(arr.data, w, h, arr.strides[0], QtGui.QImage.Format_RGB888)
                pix = QtGui.QPixmap.fromImage(qimg).scaled(self.thumb_labels[label_index].size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
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
        total_spacing = THUMB_SPACING * (visible_count - 1)
        w = (avail - total_spacing) / visible_count
        w = int(max(MIN_THUMB_WIDTH, min(DEFAULT_THUMB_WIDTH, w)))
        h = int(w * THUMB_ASPECT)
        return w, h

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                layout.removeWidget(widget)

    def rebuild_thumb_layout(self, apply_cached_sizes=False):
        visible_indices = list(range(NUM_THUMBS)) if self.check_adjacent.isChecked() else [2]
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
        visible_count = NUM_THUMBS if self.check_adjacent.isChecked() else 1
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
                vis_count = NUM_THUMBS if getattr(self, 'check_adjacent', None) and self.check_adjacent.isChecked() else 1
                w, h = self.compute_thumb_size_for(vis_count) if hasattr(self, 'compute_thumb_size_for') else (MIN_THUMB_WIDTH, int(MIN_THUMB_WIDTH * THUMB_ASPECT))
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
        QtCore.QMetaObject.invokeMethod(self.worker, "request_frames", QtCore.Qt.QueuedConnection,
                                        QtCore.Q_ARG(int, frame_num), QtCore.Q_ARG(bool, False))
        timer = QtCore.QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(loop.quit)
        timer.start(2000)
        loop.exec_()
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
        filename = now.strftime("%Y%m%d_%H%M%S") + ".png"
        full = os.path.join(downloads, filename)
        try:
            img_pil.save(full, "PNG")
            QtWidgets.QMessageBox.information(self, "Éxito", f"Fotograma exacto exportado como\n{full}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"No se pudo exportar la imagen.\n{e}")

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
        self.setCursor(QtCore.Qt.ArrowCursor)
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
            'scale': OCR_SCALE,
            'clahe': OCR_USE_CLAHE,
            'clahe_clip': OCR_CLAHE_CLIP,
            'denoise_ksize': OCR_DENOISE_KSIZE,
            'dilate_iter': OCR_DILATE_ITER,
            'invert': OCR_INVERT,
            'binarize': OCR_BINARIZE,
            'psm': OCR_PSM,
            'lang': OCR_LANG,
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

# -----------------------
def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon(ICON_PATH))
    
    set_dark_theme(app)
    window = VideoEtude()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
