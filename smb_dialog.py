from __future__ import annotations

import ctypes
import json
import os
import sys
import tempfile
from pathlib import Path
import html

from PyQt6 import QtCore, QtGui, QtWidgets

from windows_share_manager import (
    WindowsAdminRequiredError,
    WindowsShareError,
    WindowsShareManager,
    WindowsShareValidationError,
)



def _norm_path(value: str) -> str:
    return os.path.normcase(os.path.normpath(os.path.abspath(value)))


class SMBWorker(QtCore.QObject):
    log = QtCore.pyqtSignal(str, str)     # level, message
    finished = QtCore.pyqtSignal(object)  # payload
    failed = QtCore.pyqtSignal(str)

    def __init__(self, action: str, folder_path: str):
        super().__init__()
        self.action = action
        self.folder_path = folder_path

    def _append_share_info(self, share: dict):
        name = share.get("nombre") or "(sin nombre)"
        ruta = share.get("ruta") or "(sin ruta)"
        desc = share.get("descripcion") or ""
        estado = share.get("estado") or ""
        tipo = share.get("tipo") or ""

        self.log.emit("info", f"Share: {name}")
        self.log.emit("info", f"Ruta: {ruta}")
        if desc:
            self.log.emit("info", f"Descripción: {desc}")
        if estado:
            self.log.emit("info", f"Estado: {estado}")
        if tipo:
            self.log.emit("info", f"Tipo: {tipo}")

    def _find_share_by_folder(self, manager: WindowsShareManager) -> dict | None:
        target = _norm_path(self.folder_path)
        for share in manager.obtener_carpetas_compartidas():
            ruta = share.get("ruta")
            if not ruta:
                continue
            try:
                if _norm_path(str(ruta)) == target:
                    return share
            except Exception:
                continue
        return None

    @QtCore.pyqtSlot()
    def run(self):
        try:
            manager = WindowsShareManager()

            if self.action == "check":
                self._run_check(manager)
            elif self.action == "connect":
                self._run_connect(manager)
            elif self.action == "disconnect":
                self._run_disconnect(manager)
            else:
                raise WindowsShareValidationError("Acción inválida.")

            self.finished.emit(True)

        except Exception as exc:
            self.failed.emit(str(exc))

    def _run_check(self, manager: WindowsShareManager):
        self.log.emit("info", f"Carpeta activa: {self.folder_path}")
        if not os.path.isdir(self.folder_path):
            self.log.emit("error", "La carpeta no existe o no es accesible.")
            return

        share = self._find_share_by_folder(manager)
        if not share:
            self.log.emit("error", "La carpeta no aparece como recurso compartido en este equipo.")
            return

        self.log.emit("ok", "La carpeta está compartida en LAN.")
        self._append_share_info(share)

        share_name = share.get("nombre")
        if share_name:
            try:
                detalle = manager.resumen_detallado_carpeta_compartida(str(share_name))
                access = detalle.get("access", [])
                if access:
                    self.log.emit("info", "Permisos detectados:")
                    for row in access:
                        account = row.get("account_name") or "(sin cuenta)"
                        right = row.get("access_right") or "(sin permiso)"
                        self.log.emit("info", f"  - {account}: {right}")
                else:
                    self.log.emit("info", "No se detectaron permisos SMB detallados.")
            except Exception as exc:
                self.log.emit("error", f"No se pudo leer el detalle del share: {exc}")

    def _run_connect(self, manager: WindowsShareManager):
        if not os.path.isdir(self.folder_path):
            self.log.emit("error", "La carpeta no existe o no es accesible.")
            return

        existing = self._find_share_by_folder(manager)
        if existing:
            self.log.emit("ok", "La carpeta ya está compartida.")
            self._append_share_info(existing)
            return

        base_name = Path(self.folder_path).name.strip() or "SharedFolder"
        try:
            share_name = WindowsShareManager.normalizar_share_name(base_name)
        except Exception:
            share_name = "SharedFolder"

        self.log.emit("info", f"Creando recurso compartido: {share_name}")
        current_user = os.environ.get("USERNAME", "Administrador")
        manager.compartir_carpeta(self.folder_path, share_name, full_access=[current_user])
        self.log.emit("ok", "Recurso compartido creado correctamente.")

        share = self._find_share_by_folder(manager)
        if share:
            self._append_share_info(share)

    def _run_disconnect(self, manager: WindowsShareManager):
        share = self._find_share_by_folder(manager)
        if not share:
            self.log.emit("error", "La carpeta no está compartida.")
            return

        share_name = share.get("nombre")
        if not share_name:
            self.log.emit("error", "No se pudo determinar el nombre del recurso compartido.")
            return

        self.log.emit("info", f"Descompartiendo: {share_name}")
        manager.descompartir_carpeta(str(share_name))
        self.log.emit("ok", "Recurso compartido eliminado correctamente.")


class SMBDialog(QtWidgets.QDialog):
    def __init__(self, folder_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Check SMB")
        self.setModal(True)
        self.resize(860, 520)

        self.folder_path = folder_path or ""
        self._thread: QtCore.QThread | None = None
        self._worker: SMBWorker | None = None

        self._build_ui()
        self._auto_check_done = False
        
    def showEvent(self, event):
        super().showEvent(event)
        if not self._auto_check_done:
            self._auto_check_done = True
            QtCore.QTimer.singleShot(0, lambda: self._start_action("check"))

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        self.path_label = QtWidgets.QLabel(self.folder_path or "(sin carpeta)")
        self.path_label.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(self.path_label)

        self.log_view = QtWidgets.QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setAcceptRichText(True)
        self.log_view.setStyleSheet(
            "QTextEdit { background: #111; color: #fff; font-family: Consolas, monospace; }"
        )
        layout.addWidget(self.log_view, 1)
        
        self.systyle = QtWidgets.QApplication.style()
        self.uac_pixel = self.systyle.standardPixmap(QtWidgets.QStyle.StandardPixmap.SP_VistaShield)
        self.search_pixel = self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_FileDialogContentsView)
        self.icon_uac = QtGui.QIcon(self.uac_pixel)
        self.icon_search = QtGui.QIcon(self.search_pixel)

        row1 = QtWidgets.QHBoxLayout()
        self.btn_connect = QtWidgets.QPushButton(" Conectar")
        self.btn_check = QtWidgets.QPushButton(" Comprobar estado")
        self.btn_disconnect = QtWidgets.QPushButton(" Desconectar")
        self.btn_connect.setIcon(self.icon_uac)
        self.btn_check.setIcon(self.icon_search)
        self.btn_disconnect.setIcon(self.icon_uac)
        row1.addWidget(self.btn_connect)
        row1.addWidget(self.btn_check)
        row1.addWidget(self.btn_disconnect)
        layout.addLayout(row1)

        row2 = QtWidgets.QHBoxLayout()
        self.btn_clear = QtWidgets.QPushButton("Limpiar logs")
        self.btn_close = QtWidgets.QPushButton("Cerrar")
        row2.addWidget(self.btn_clear)
        row2.addStretch(1)
        row2.addWidget(self.btn_close)
        layout.addLayout(row2)

        self.btn_connect.clicked.connect(lambda: self._start_action("connect"))
        self.btn_check.clicked.connect(lambda: self._start_action("check"))
        self.btn_disconnect.clicked.connect(lambda: self._start_action("disconnect"))
        self.btn_clear.clicked.connect(self.log_view.clear)
        self.btn_close.clicked.connect(self.close)

    def _set_busy(self, busy: bool):
        self.btn_connect.setEnabled(not busy)
        self.btn_check.setEnabled(not busy)
        self.btn_disconnect.setEnabled(not busy)
        self.btn_clear.setEnabled(not busy)
        self.btn_close.setEnabled(True)

    def _append(self, level: str, text: str):
        colors = {
            "info": "#ffffff",
            "error": "#ff5b5b",
            "ok": "#35d07f",
        }
        color = colors.get(level, "#ffffff")
        escaped = html.escape(text).replace("\n", "<br>")
        self.log_view.append(f'<span style="color:{color};">{escaped}</span>')
        self.log_view.moveCursor(QtGui.QTextCursor.MoveOperation.End)

    def _append_info(self, text: str):
        self._append("info", text)

    def _append_error(self, text: str):
        self._append("error", text)

    def _append_ok(self, text: str):
        self._append("ok", text)

    def _start_action(self, action: str):
        if self._thread is not None:
            return

        if action in {"connect", "disconnect"}:
            self._start_elevated_action(action)
            return

        self._set_busy(True)
        self._thread = QtCore.QThread(self)
        self._worker = SMBWorker(action, self.folder_path)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.log.connect(self._append)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._thread.quit)
        self._worker.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup_thread)

        self._append_info("Comprobando estado...")
        self._thread.start()

    def _on_finished(self, _payload):
        pass

    def _cleanup_thread(self):
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None

        if self._thread is not None:
            self._thread.deleteLater()
            self._thread = None

        self._set_busy(False)

    def _start_elevated_action(self, action: str):
        self._set_busy(True)
        self._append_info("Solicitando permisos de administrador...")

        out_file = Path(tempfile.gettempdir()) / f"smb_check_{os.getpid()}_{action}.json"
        helper = Path(__file__).with_name("smb_uac_action.py")
        
        python_exe = sys.executable
        if os.name == "nt":
            candidate = Path(sys.executable).with_name("pythonw.exe")
            if candidate.exists():
                python_exe = str(candidate)

        if not helper.exists():
            self._append_error(f"No se encontró el helper: {helper.name}")
            self._set_busy(False)
            return

        SW_HIDE = 0
        params = f'"{helper}" --action {action} --folder "{self.folder_path}" --out "{out_file}"'
        result = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            python_exe,
            params,
            None,
            SW_HIDE,
        )

        if result <= 32:
            self._append_error("La elevación UAC fue cancelada o falló.")
            self._set_busy(False)
            return

        self._wait_for_elevated_result(out_file)

    def _wait_for_elevated_result(self, out_file: Path):
        timer = QtCore.QTimer(self)
        timer.setInterval(300)

        def poll():
            if not out_file.exists():
                return

            try:
                payload = json.loads(out_file.read_text(encoding="utf-8"))
            except Exception as exc:
                self._append_error(f"No se pudo leer la respuesta elevada: {exc}")
                timer.stop()
                timer.deleteLater()
                self._set_busy(False)
                return

            share_name = payload.get("share_name")
            for message in payload.get("messages", []):
                level = payload.get("level", "info")
                self._append(level, str(message))

            if share_name:
                self._append_info(f"Nombre del share: {share_name}")

            try:
                out_file.unlink(missing_ok=True)
            except Exception:
                pass

            timer.stop()
            timer.deleteLater()
            self._set_busy(False)

        timer.timeout.connect(poll)
        timer.start()

    def _on_failed(self, message: str):
        self._append_error(message)
        self._set_busy(False)