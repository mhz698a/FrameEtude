# -*- coding: utf-8 -*-
import os
import sys
import json
import csv
import traceback
import datetime
from pathlib import Path
from PyQt6 import QtCore, QtGui, QtWidgets

try:
    from mutagen.mp4 import MP4
except Exception:
    MP4 = None

import config
from metadata_edit_lib import comment_display_value

# Import logic from FileTableWidget or replicate it
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

def get_onedrive_path():
    # Common environment variables for OneDrive
    for env in ["OneDrive", "OneDriveCommercial", "OneDriveConsumer"]:
        path = os.getenv(env)
        if path and os.path.exists(path):
            return path
    return None

def get_default_backup_path():
    od = get_onedrive_path()
    if od:
        return od
    return str(Path.home() / "Documents")

def get_mp4_duration(path):
    if MP4 is None:
        return ""
    try:
        audio = MP4(path)
        seconds = int(audio.info.length)
        return str(datetime.timedelta(seconds=seconds))
    except Exception:
        return ""

def get_metadata(path):
    data = {key: "" for _, key in COLUMNS}
    data["filename"] = os.path.basename(path)
    data["duration"] = get_mp4_duration(path)

    if MP4 is None:
        return data

    try:
        tags = MP4(path).tags
        if not tags:
            return data
    except Exception:
        return data

    def safe_text(val):
        if not val: return ""
        if isinstance(val, list): val = val[0]
        return str(val).strip()

    def pair_text(val, digits=2, include_total=False):
        if not val or not isinstance(val, list): return ""
        try:
            item = val[0]
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                first = int(item[0]) if item[0] not in (None, "") else 0
                second = int(item[1]) if item[1] not in (None, "") else 0
                if include_total:
                    return f"{first:0{digits}d}/{second:0{digits}d}"
                return f"{first:0{digits}d}"
        except Exception:
            pass
        return ""

    data["title"] = safe_text(tags.get("©nam"))
    data["album"] = safe_text(tags.get("©alb"))
    data["artist"] = safe_text(tags.get("©ART"))
    data["track"] = pair_text(tags.get("trkn"), include_total=True)
    data["release_date"] = safe_text(tags.get("©day"))
    data["disk"] = pair_text(tags.get("disk"))
    data["genre"] = safe_text(tags.get("©gen"))

    comment_raw = tags.get("©cmt")
    if comment_raw:
        for _, key in COLUMNS:
            if key in ["real_ctime", "real_mtime", "after_of_episode", "overwrite_1_times", "overwrite_2_times", "overwrite_3_times", "free_listener_times"]:
                data[key] = comment_display_value(comment_raw, key)

    return data

class YearSelectionDialog(QtWidgets.QDialog):
    def __init__(self, years, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Seleccionar años para respaldo")
        self.resize(400, 500)

        layout = QtWidgets.QVBoxLayout(self)

        self.scroll = QtWidgets.QScrollArea()
        self.scroll_widget = QtWidgets.QWidget()
        self.scroll_layout = QtWidgets.QVBoxLayout(self.scroll_widget)

        self.checkboxes = []

        # Select All
        self.chk_all = QtWidgets.QCheckBox("Seleccionar todos")
        self.chk_all.toggled.connect(self.toggle_all)
        layout.addWidget(self.chk_all)
        layout.addWidget(QtWidgets.QLabel("<hr>"))

        for year in years:
            chk = QtWidgets.QCheckBox(year)
            chk.toggled.connect(self.update_continue_button)
            self.scroll_layout.addWidget(chk)
            self.checkboxes.append(chk)

        self.scroll.setWidget(self.scroll_widget)
        self.scroll.setWidgetResizable(True)
        layout.addWidget(self.scroll)

        btn_layout = QtWidgets.QHBoxLayout()
        self.btn_continue = QtWidgets.QPushButton("Continuar")
        self.btn_continue.setEnabled(False)
        self.btn_continue.clicked.connect(self.accept)

        self.btn_cancel = QtWidgets.QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_continue)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def toggle_all(self, checked):
        for chk in self.checkboxes:
            chk.setChecked(checked)
        self.update_continue_button()

    def update_continue_button(self):
        has_checked = any(chk.isChecked() for chk in self.checkboxes)
        self.btn_continue.setEnabled(has_checked)

    def get_selected_years(self):
        return [chk.text() for chk in self.checkboxes if chk.isChecked()]

class BackupWorker(QtCore.QThread):
    progress = QtCore.pyqtSignal(int, int, str) # current, total, message
    finished = QtCore.pyqtSignal(bool, str, str) # success, message, traceback

    def __init__(self, selected_years, backup_root):
        super().__init__()
        self.selected_years = selected_years
        self.backup_root = backup_root

    def run(self):
        try:
            tasks = []
            for year in self.selected_years:
                year_path = os.path.join(config.BASE_INTERNAL_ROOT, year)
                if not os.path.isdir(year_path): continue

                # Find Master folder
                prefix = f"{(int(year) - 2003):02d}. " if int(year) >= 2004 else ""
                master_found = None
                for name in os.listdir(year_path):
                    full = os.path.join(year_path, name)
                    if os.path.isdir(full) and "___[" in name:
                        if not prefix or name.startswith(prefix):
                            master_found = full
                            break

                if not master_found: continue

                # Find important subfolders
                for sub in os.listdir(master_found):
                    sub_full = os.path.join(master_found, sub)
                    if not os.path.isdir(sub_full): continue

                    name_low = sub.lower()
                    important = False
                    if name_low.endswith("_eps.on") or name_low.startswith("mov_") or name_low.endswith("sp.on") or name_low.endswith("vocals"):
                        important = True

                    if important:
                        tasks.append((year, sub, sub_full))

            total_tasks = len(tasks)
            if total_tasks == 0:
                self.finished.emit(True, "No se encontraron carpetas para respaldar.", "")
                return

            for i, (year, foldername, path) in enumerate(tasks):
                self.progress.emit(i, total_tasks, f"Respaldando {year} - {foldername}...")

                csv_filename = f"{year}-{foldername}.csv"
                csv_path = os.path.join(self.backup_root, csv_filename)

                files = [os.path.join(path, f) for f in os.listdir(path) if f.lower().endswith(".mp4")]
                # Sort similar to FrameEtude if possible, or just alphabetically
                files.sort()

                with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.writer(f)
                    # Header
                    writer.writerow([col[0] for col in COLUMNS])

                    for video_path in files:
                        meta = get_metadata(video_path)
                        writer.writerow([meta[col[1]] for col in COLUMNS])

            self.progress.emit(total_tasks, total_tasks, "Finalizado")
            self.finished.emit(True, "Respaldo completado correctamente.", "")

        except Exception as e:
            self.finished.emit(False, str(e), traceback.format_exc())

class ProgressDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Progreso de Respaldo")
        self.setFixedSize(400, 150)
        layout = QtWidgets.QVBoxLayout(self)

        self.label = QtWidgets.QLabel("Iniciando...")
        layout.addWidget(self.label)

        self.bar = QtWidgets.QProgressBar()
        layout.addWidget(self.bar)

    def update_progress(self, val, total, msg):
        self.bar.setMaximum(total)
        self.bar.setValue(val)
        self.label.setText(msg)

def main():
    app = QtWidgets.QApplication(sys.argv)

    # Check backup path
    backup_path = config.BACKUP_PATH
    if not backup_path:
        # Try detect OneDrive
        backup_path = get_default_backup_path()

        reply = QtWidgets.QMessageBox.question(
            None, "Configurar ruta de respaldo",
            f"No se ha configurado una ruta de respaldo. ¿Desea usar la siguiente ruta?\n\n{backup_path}\n\nSi elige 'No', podrá seleccionar otra carpeta.",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No | QtWidgets.QMessageBox.StandardButton.Cancel
        )

        if reply == QtWidgets.QMessageBox.StandardButton.Cancel:
            return
        elif reply == QtWidgets.QMessageBox.StandardButton.No:
            backup_path = QtWidgets.QFileDialog.getExistingDirectory(None, "Seleccionar carpeta de respaldo")
            if not backup_path:
                return

        # Save new path to config
        config.update_and_save({}, {"BACKUP_PATH": backup_path})

    # Get available years
    years = []
    # Static hidden years
    for y in ["1999", "2000", "2001", "2002", "2003"]:
        if os.path.exists(os.path.join(config.BASE_INTERNAL_ROOT, y)):
            years.append(y)

    # Dynamic years
    try:
        for name in os.listdir(config.BASE_INTERNAL_ROOT):
            if name.isdigit() and len(name) == 4 and int(name) >= 2004:
                if name not in years:
                    years.append(name)
        years.sort()
    except Exception:
        pass

    dlg = YearSelectionDialog(years)
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
            msg_box.setIcon(QtWidgets.QMessageBox.Icon.Warning)
            msg_box.setWindowTitle("Error en Respaldo")
            msg_box.setText(f"Ocurrió un error: {message}")
            if tb:
                msg_box.setInformativeText(tb)
        msg_box.exec()
        sys.exit(0)

    worker.finished.connect(on_finished)
    progress.show()
    worker.start()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
