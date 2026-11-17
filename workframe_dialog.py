from __future__ import annotations

import datetime
import os
import re
import struct

import cv2
import win32clipboard
from PIL import Image
from PyQt6 import QtCore, QtGui, QtWidgets

import config
from cut_dialog_ex import CutDialog
from frame_player_panel import FramePlayerPanel
from ocr_lib import OCRWorker
from utils import format_time
from vidwk_lib import VideoWorker
from video_metadata_async_lib import VideoMetadataFetchThread, empty_video_metadata


class WorkframeDialog(QtWidgets.QDialog):
    """Independent, non-modal video session with its own decoder and controls."""

    def __init__(self, video_path: str):
        # Un Workframe sin ventana propietaria obtiene una entrada independiente
        # en la barra de tareas de Windows.
        super().__init__(None)
        self.video_path = os.path.abspath(video_path)
        window_flags = (
            QtCore.Qt.WindowType.Window
            | QtCore.Qt.WindowType.WindowTitleHint
            | QtCore.Qt.WindowType.WindowSystemMenuHint
            | QtCore.Qt.WindowType.WindowMinMaxButtonsHint
            | QtCore.Qt.WindowType.WindowCloseButtonHint
        )
        # El estado inicial siempre es normal (no Always on top).
        window_flags &= ~QtCore.Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(window_flags)
        self.setModal(False)
        self.setWindowModality(QtCore.Qt.WindowModality.NonModal)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.resize(1000, 620)
        if config.ICON_PATH and os.path.isfile(config.ICON_PATH):
            self.setWindowIcon(QtGui.QIcon(config.ICON_PATH))

        self.worker = None
        self.worker_thread = None
        self._video_metadata_thread = None
        self.video_metadata = empty_video_metadata(pending=True)
        self.duration_text = "00:00:00.000"
        self.fps = 25.0
        self.frame_count = 0
        self.frame_actual = 0
        self.video_name = os.path.basename(self.video_path)
        self.setWindowTitle(self.video_name)
        self.ocr_thread = None
        self.ocr_worker = None
        self._cut_dialogs = []

        self.frame_player_panel = FramePlayerPanel(self)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.frame_player_panel, 1)

        self.status = QtWidgets.QLabel("Abriendo video...")
        self.status.setContentsMargins(8, 3, 8, 3)
        layout.addWidget(self.status)

        left = QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_Left), self)
        left.activated.connect(lambda: self.move_seconds(-1))
        right = QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_Right), self)
        right.activated.connect(lambda: self.move_seconds(1))

        self.start_worker_and_open(self.video_path)

    def is_always_on_top(self) -> bool:
        return bool(
            self.windowFlags() & QtCore.Qt.WindowType.WindowStaysOnTopHint
        )

    def update_always_on_top(self, enabled: bool) -> None:
        enabled = bool(enabled)
        flags = self.windowFlags()
        current = bool(flags & QtCore.Qt.WindowType.WindowStaysOnTopHint)
        if current == enabled:
            self._sync_always_on_top_action(enabled)
            return

        was_visible = self.isVisible()
        was_minimized = self.isMinimized()
        was_maximized = self.isMaximized()

        if enabled:
            flags |= QtCore.Qt.WindowType.WindowStaysOnTopHint
        else:
            flags &= ~QtCore.Qt.WindowType.WindowStaysOnTopHint

        self.setWindowFlags(flags)
        if was_visible:
            if was_minimized:
                self.showMinimized()
            elif was_maximized:
                self.showMaximized()
            else:
                self.show()
            self.raise_()

        self._sync_always_on_top_action(enabled)

    def _sync_always_on_top_action(self, enabled: bool) -> None:
        action = getattr(self, "always_on_top_action", None)
        if action is None or action.isChecked() == enabled:
            return

        blocker = QtCore.QSignalBlocker(action)
        action.setChecked(enabled)
        del blocker

    def start_worker_and_open(self, path):
        self.status.setText("Abriendo video...")
        if self.worker_thread is not None:
            try:
                self.worker.close()
            except Exception:
                pass
            self.worker_thread.quit()
            self.worker_thread.wait()
            self.worker = None
            self.worker_thread = None

        self._start_video_metadata_fetch(path)
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
        duration_text = format_time(self.frame_count / (self.fps or 25.0))
        self.duration_text = duration_text
        self._update_info_label()
        self.setWindowTitle(f"{self.video_name} — {duration_text}")
        self.frame_actual = 0
        
        self.video_slider.blockSignals(True)
        self.video_slider.setRange(0, self.frame_count - 1)
        self.video_slider.setValue(0)
        self.video_slider.blockSignals(False)
        
        self.status.setText("Video listo")
        self.request_current_frames()

    def _start_video_metadata_fetch(self, path: str):
        self.video_metadata = empty_video_metadata(pending=True)
        self._update_info_label()

        thread = VideoMetadataFetchThread(path, self)
        thread.metadata_ready.connect(self._on_video_metadata_ready)
        self._video_metadata_thread = thread
        thread.start()

    @QtCore.pyqtSlot(str, object)
    def _on_video_metadata_ready(self, path: str, metadata: dict):
        expected_path = os.path.normcase(os.path.abspath(self.video_path))
        result_path = os.path.normcase(os.path.abspath(path))
        if result_path != expected_path:
            return

        self.video_metadata = metadata
        self._update_info_label()

    def _update_info_label(self):
        metadata = self.video_metadata or {}
        resolution = metadata.get("resolution", "N/A")
        bit_rate = metadata.get("bit_rate", "N/A")
        audio = metadata.get("audio", "N/A")
        weight = metadata.get("weight", "N/A")

        self.info_label.setText(
            f"{self.video_name} - {self.duration_text}\n"
            f"Resolution: {resolution}  |  "
            f"Bit Rate: {bit_rate}  |  "
            f"Audio?: {audio}  |  "
            f"Weight: {weight}"
        )

    def on_worker_error(self, msg):
        self.status.setText("Error al abrir el video")
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

    

    def closeEvent(self, event):
        try:
            if getattr(self, "selection_overlay", None) is not None:
                self.selection_overlay.stop()
        except Exception:
            pass

        metadata_thread = self._video_metadata_thread
        if metadata_thread is not None:
            if metadata_thread.isRunning():
                metadata_thread.requestInterruption()
                metadata_thread.wait()
            self._video_metadata_thread = None

        thread = self.worker_thread
        worker = self.worker
        if worker is not None:
            try:
                worker.close()
            except Exception:
                pass
        if thread is not None:
            try:
                thread.quit()
                thread.wait(3000)
            except Exception:
                pass
        self.worker = None
        self.worker_thread = None
        super().closeEvent(event)
