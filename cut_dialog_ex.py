import os
from utils import format_time, parse_time_to_seconds
from cut_lib import FFmpegWorker
from PyQt6 import QtCore, QtWidgets
# from video_etude_main import VideoEtude

# -----------------------
# Cut Dialog (no bloqueante)
# -----------------------
class CutDialog(QtWidgets.QDialog):
    start_cut_signal = QtCore.pyqtSignal(dict)

    def __init__(self, parent: str, video_path: str, default_start: str, default_end: str, 
                 fps: float, width: int, height: int):
        super().__init__(parent)
        self.setWindowTitle("Recortar video")
        self.setModal(False)
        self.setWindowModality(QtCore.Qt.WindowModality.NonModal)
        self.resize(560, 240)
        self.video_path = video_path
        self.fps = fps
        self.width = width
        self.height = height

        layout = QtWidgets.QVBoxLayout(self)

        form = QtWidgets.QFormLayout()

        # Deviation input
        self.spin_deviation = QtWidgets.QDoubleSpinBox()
        self.spin_deviation.setRange(-999999.0, 999999.0)
        self.spin_deviation.setSingleStep(0.1)
        self.spin_deviation.setValue(-2.0)
        self.spin_deviation.setToolTip("Desviación de segundos para el inicio")

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
        form.addRow("Desviación inicio (seg):", self.spin_deviation)

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
            
            # Aplicar desviación (ej: -2 segundos)
            dev = self.spin_deviation.value()
            start_sec = max(0, start_sec + dev)
            
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
        self._ff_worker = FFmpegWorker()
        self._ff_thread = QtCore.QThread()
        
        self._ff_worker.moveToThread(self._ff_thread)
        
        # Connect signals
        self._ff_worker.progress.connect(self.progress.setValue)
        self._ff_worker.status.connect(self.progress.setFormat)
        self._ff_worker.finished.connect(self._on_finished)
        self._ff_worker.error.connect(self._on_error)
        
        # Connect the start signal to the worker's slot
        # Since the worker is in another thread, this will be a QueuedConnection
        self._ff_worker.run_requested.connect(self._ff_worker.run_cut)
        
        # Cleanup logic
        self._ff_worker.finished.connect(self._cleanup_ff_worker)
        self._ff_worker.error.connect(self._cleanup_ff_worker)
        
        self._ff_thread.start()
        
        # Trigger the worker via signal (never call run_cut directly)
        self._ff_worker.run_requested.emit(params)

    def _cleanup_ff_worker(self):
        if hasattr(self, '_ff_worker') and self._ff_worker:
            self._ff_worker.deleteLater()
            self._ff_worker = None
        if hasattr(self, '_ff_thread') and self._ff_thread:
            self._ff_thread.quit()
            self._ff_thread.wait(2000)
            self._ff_thread.deleteLater()
            self._ff_thread = None

    @QtCore.pyqtSlot(str)
    def _on_finished(self, out_path):
        self.progress.setValue(100)
        self.progress.setFormat("Completado")
        
        # Uso de mensaje no bloqueante (opcional, pero ayuda a que la interfaz "fluya")
        msg = QtWidgets.QMessageBox(self)
        msg.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
        msg.setWindowModality(QtCore.Qt.WindowModality.NonModal)
        msg.setWindowTitle("Recorte completado")
        msg.setText(f"Recorte guardado en:\n{out_path}")
        msg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
        msg.show()

        self.btn_cut.setEnabled(True)
        self.btn_cancel.setEnabled(True)
        self._cut_started = False

    @QtCore.pyqtSlot(str)
    def _on_error(self, tb):
        QtWidgets.QMessageBox.critical(self, "Error en recorte", f"Ocurrió un error:\n\n{tb}")
        self.btn_cut.setEnabled(True)
        self.btn_cancel.setEnabled(True)
        self._cut_started = False

#