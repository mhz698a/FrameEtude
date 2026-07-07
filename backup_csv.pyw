import os
import sys
import csv
import json
import traceback
import datetime
from PyQt6 import QtCore, QtGui, QtWidgets
from pathlib import Path

try:
    from mutagen.mp4 import MP4
except ImportError:
    MP4 = None

import config
from duration_async_lib import probe_duration_text
from metadata_edit_lib import comment_display_value

# Metadata columns from FrameEtude
COLUMNS = [
    ("Duration 🔒", "duration"),
    ("Filename", "filename"),
    ("Title", "title"),
    ("Album (Season/Sp)", "album"),
    ("Artista (Root Season)", "artist"),
    ("Track (EpNum)", "track"),
    ("Release Date", "release_date"),
    ("Disk (SeNum)", "disk"),
    ("Genre (Type)", "genre"),
    ("Real Created", "real_ctime"),
    ("Real Modified", "real_mtime"),
    ("After of...", "after_of_episode"),
    ("Sobrescritura 1", "overwrite_1_times"),
    ("Sobrescritura 2", "overwrite_2_times"),
    ("Sobrescritura 3", "overwrite_3_times"),
    ("Free listener", "free_listener_times"),
]

def get_file_metadata(path):
    metadata = {key: "" for _, key in COLUMNS}
    metadata["duration"] = probe_duration_text(path)
    metadata["filename"] = os.path.basename(path)

    if MP4 is None:
        return metadata

    try:
        tags = MP4(path)
        mp4_tags = tags.tags or {}
    except Exception:
        return metadata

    def tag_text(name):
        val = mp4_tags.get(name, "")
        if val is None: return ""
        if isinstance(val, (list, tuple)):
            if not val: return ""
            val = val[0]
        return str(val).strip()

    def pair_text(name, digits=2, include_total=False):
        val = mp4_tags.get(name, "")
        if not val or not isinstance(val, (list, tuple)): return ""
        item = val[0]
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            first = int(item[0]) if item[0] not in (None, "") else 0
            second = int(item[1]) if item[1] not in (None, "") else 0
            if include_total:
                return f"{first:0{digits}d}/{second:0{digits}d}"
            return f"{first:0{digits}d}"
        return ""

    metadata["title"] = tag_text("©nam")
    metadata["album"] = tag_text("©alb")
    metadata["artist"] = tag_text("©ART")
    metadata["track"] = pair_text("trkn", digits=2, include_total=True)
    metadata["release_date"] = tag_text("©day")
    metadata["disk"] = pair_text("disk", digits=2, include_total=False)
    metadata["genre"] = tag_text("©gen")

    comment_raw = mp4_tags.get("©cmt", "")
    metadata["real_ctime"] = comment_display_value(comment_raw, "real_ctime")
    metadata["real_mtime"] = comment_display_value(comment_raw, "real_mtime")
    metadata["after_of_episode"] = comment_display_value(comment_raw, "after_of_episode")
    metadata["overwrite_1_times"] = comment_display_value(comment_raw, "overwrite_1_times")
    metadata["overwrite_2_times"] = comment_display_value(comment_raw, "overwrite_2_times")
    metadata["overwrite_3_times"] = comment_display_value(comment_raw, "overwrite_3_times")
    metadata["free_listener_times"] = comment_display_value(comment_raw, "free_listener_times")

    return metadata

class BackupWorker(QtCore.QThread):
    progress = QtCore.pyqtSignal(int, int, str)
    finished = QtCore.pyqtSignal(bool, str, str) # success, message, traceback

    def __init__(self, selected_years, backup_root):
        super().__init__()
        self.selected_years = selected_years
        self.backup_root = backup_root

    def run(self):
        try:
            if not os.path.exists(self.backup_root):
                os.makedirs(self.backup_root, exist_ok=True)

            tasks = []
            for year in self.selected_years:
                year_path = os.path.join(config.BASE_INTERNAL_ROOT, year)
                if not os.path.isdir(year_path):
                    continue

                # Find master folder (contains "___[")
                master_folder = None
                try:
                    for name in os.listdir(year_path):
                        full = os.path.join(year_path, name)
                        if os.path.isdir(full) and "___[" in name:
                            master_folder = full
                            break
                except Exception:
                    continue

                if not master_folder:
                    continue

                # Find subfolders
                try:
                    for sub in os.listdir(master_folder):
                        sub_full = os.path.join(master_folder, sub)
                        if not os.path.isdir(sub_full):
                            continue

                        sub_lower = sub.lower()
                        # Important folders according to requirements
                        if any(kw in sub_lower for kw in ["_eps.on", "mov_", "sp.on", "vocals"]):
                            tasks.append((year, sub, sub_full))
                except Exception:
                    continue

            total_tasks = len(tasks)
            if total_tasks == 0:
                self.finished.emit(True, "No se encontraron carpetas para respaldar.", "")
                return

            for i, (year, sub_name, sub_path) in enumerate(tasks):
                self.progress.emit(i, total_tasks, f"Respaldando {year} - {sub_name}")

                csv_filename = f"{year}-{sub_name}.csv"
                csv_path = os.path.join(self.backup_root, csv_filename)

                files = sorted([f for f in os.listdir(sub_path) if f.lower().endswith(tuple(config.VIDEO_EXTS))])

                with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    # Write headers
                    writer.writerow([col[0] for col in COLUMNS])

                    for filename in files:
                        file_path = os.path.join(sub_path, filename)
                        meta = get_file_metadata(file_path)
                        writer.writerow([meta[col[1]] for col in COLUMNS])

            self.finished.emit(True, f"Respaldo completado con éxito. {total_tasks} archivos CSV generados.", "")

        except Exception as e:
            self.finished.emit(False, str(e), traceback.format_exc())

class YearSelectionDialog(QtWidgets.QDialog):
    def __init__(self, years, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Seleccionar Años para Respaldo")
        self.setMinimumWidth(350)
        layout = QtWidgets.QVBoxLayout(self)

        self.chk_all = QtWidgets.QCheckBox("Seleccionar todos los años")
        layout.addWidget(self.chk_all)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        container = QtWidgets.QWidget()
        self.scroll_layout = QtWidgets.QVBoxLayout(container)

        self.checkboxes = []
        for year in years:
            cb = QtWidgets.QCheckBox(year)
            self.scroll_layout.addWidget(cb)
            self.checkboxes.append(cb)
            cb.toggled.connect(self.update_continue_button)

        scroll.setWidget(container)
        layout.addWidget(scroll)

        self.chk_all.toggled.connect(self.toggle_all)

        buttons = QtWidgets.QHBoxLayout()
        self.btn_continue = QtWidgets.QPushButton("Continuar")
        self.btn_cancel = QtWidgets.QPushButton("Cancelar")

        self.btn_continue.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

        buttons.addWidget(self.btn_continue)
        buttons.addWidget(self.btn_cancel)
        layout.addLayout(buttons)

        self.update_continue_button()

    def toggle_all(self, checked):
        for cb in self.checkboxes:
            cb.blockSignals(True)
            cb.setChecked(checked)
            cb.blockSignals(False)
        self.update_continue_button()

    def update_continue_button(self):
        any_checked = any(cb.isChecked() for cb in self.checkboxes)
        self.btn_continue.setEnabled(any_checked)

    def get_selected_years(self):
        return [cb.text() for cb in self.checkboxes if cb.isChecked()]

class ProgressDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Procesando Respaldo")
        self.setFixedSize(450, 120)
        self.setModal(True)
        layout = QtWidgets.QVBoxLayout(self)

        self.label = QtWidgets.QLabel("Iniciando...")
        self.label.setWordWrap(True)
        layout.addWidget(self.label)

        self.bar = QtWidgets.QProgressBar()
        layout.addWidget(self.bar)

    @QtCore.pyqtSlot(int, int, str)
    def update_progress(self, val, total, msg):
        self.bar.setMaximum(total)
        self.bar.setValue(val)
        self.label.setText(msg)

def main():
    app = QtWidgets.QApplication(sys.argv)

    # Use dark theme if available
    try:
        import utils
        utils.set_dark_theme(app)
    except:
        pass

    if config.ICON_PATH and os.path.exists(config.ICON_PATH):
        app.setWindowIcon(QtGui.QIcon(config.ICON_PATH))

    # Determine backup path
    backup_path = config.BACKUP_PATH
    if not backup_path:
        backup_path = QtWidgets.QFileDialog.getExistingDirectory(None, "Seleccionar carpeta de respaldo")
        if not backup_path:
            QtWidgets.QMessageBox.warning(None, "Aviso", "No se puede continuar sin una carpeta de respaldo.")
            return

    # List years
    all_years = []
    # Hidden years
    all_years.extend(["1999", "2000", "2001", "2002", "2003"])
    # Actual years in root
    try:
        if os.path.exists(config.BASE_INTERNAL_ROOT):
            for name in os.listdir(config.BASE_INTERNAL_ROOT):
                if name.isdigit() and len(name) == 4 and int(name) >= 2004:
                    if name not in all_years:
                        all_years.append(name)

        current_year = datetime.date.today().year
        if str(current_year) not in all_years:
             all_years.append(str(current_year))

        # Use set to avoid duplicates and sort
        all_years = sorted(list(set(all_years)))
    except Exception:
        pass

    dlg = YearSelectionDialog(all_years)
    if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
        return

    selected_years = dlg.get_selected_years()

    progress = ProgressDialog()
    worker = BackupWorker(selected_years, backup_path)

    worker.progress.connect(progress.update_progress)

    def on_finished(success, message, tb):
        progress.close()
        msg_box = QtWidgets.QMessageBox()
        if success:
            msg_box.setIcon(QtWidgets.QMessageBox.Icon.Information)
            msg_box.setWindowTitle("Respaldo Finalizado")
            msg_box.setText(message)
        else:
            msg_box.setIcon(QtWidgets.QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("Error en Respaldo")
            msg_box.setText(f"Ocurrió un error: {message}")
            if tb:
                msg_box.setInformativeText(tb)
        msg_box.exec()
        sys.exit(0)

    worker.finished.connect(on_finished)
    worker.start()
    progress.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
