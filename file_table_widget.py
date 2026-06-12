import json
import os
import datetime
from typing import Any
from PyQt6 import QtCore, QtGui, QtWidgets

from metadata_async_lib import MetadataSaveJob, MetadataSaveThread
from metadata_edit_lib import (
    COMMENT_KEYS,
    ForeignCommentDialog,
    comment_display_value,
    comment_status_from_path,
    save_mp4_updates,
)

try:
    from mutagen.mp4 import MP4
except Exception:
    MP4 = None


class FileTableWidget(QtWidgets.QTableWidget):
    COLUMNS = [
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

    def __init__(self, parent=None):
        super().__init__(parent)
        self._folder_cache: dict[str, list[dict[str, Any]]] = {}
        self._current_folder = ""
        self._settings = QtCore.QSettings("FrameEtude", "FileTableWidget")
        self._metadata_thread = None
        self._progress_reset_timer = QtCore.QTimer(self)
        self._progress_reset_timer.setSingleShot(True)
        self._progress_reset_timer.timeout.connect(self._reset_metadata_progress)
        self.progress_bar = None
        self.progress_label = None

        self.setColumnCount(len(self.COLUMNS))
        self.setHorizontalHeaderLabels([label for label, _ in self.COLUMNS])
        self.verticalHeader().setVisible(True)
        self.horizontalHeader().setVisible(True)

        self.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectItems)
        self.setAlternatingRowColors(True)
        self.setWordWrap(False)
        self.setSortingEnabled(False)
        self.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.SizeAdjustPolicy.AdjustIgnored)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        header = self.horizontalHeader()
        header.setSectionsMovable(True)
        header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(False)
        header.sectionResized.connect(self._save_header_state)
        header.sectionMoved.connect(self._save_header_state)

        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.DefaultContextMenu)
        self._restore_header_state()

    def _restore_header_state(self):
        state = self._settings.value("header_state")
        if state is not None:
            try:
                self.horizontalHeader().restoreState(state)
            except Exception:
                pass

    def _save_header_state(self, *_):
        try:
            self._settings.setValue("header_state", self.horizontalHeader().saveState())
        except Exception:
            pass

    def _empty_row(self) -> dict[str, Any]:
        row = {key: "" for _, key in self.COLUMNS}
        row["full_path"] = ""
        return row

    def _safe_text(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, bytes):
            try:
                return value.decode("utf-8", "ignore").strip()
            except Exception:
                return ""
        if isinstance(value, (list, tuple)):
            if not value:
                return ""
            return self._safe_text(value[0])
        return str(value).strip()

    def _pair_text(self, value: Any, digits: int = 2, include_total: bool = False) -> str:
        if value is None:
            return ""
        try:
            if isinstance(value, (list, tuple)) and value:
                item = value[0]
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    first = int(item[0]) if item[0] not in (None, "") else 0
                    second = int(item[1]) if item[1] not in (None, "") else 0
                    if include_total:
                        return f"{first:0{digits}d}/{second:0{digits}d}"
                    return f"{first:0{digits}d}"
        except Exception:
            return ""
        return ""

    def _comment_field(self, comment_raw: Any, key: str) -> str:
        return comment_display_value(comment_raw, key)

    def _read_file_row(self, path: str) -> dict[str, Any]:
        row = self._empty_row()
        row["filename"] = os.path.basename(path)
        row["full_path"] = path

        if MP4 is None:
            return row

        try:
            tags = MP4(path)
            mp4_tags = tags.tags or {}
        except Exception:
            return row

        def tag(name: str):
            return mp4_tags.get(name, "")

        row["title"] = self._safe_text(tag("©nam"))
        row["album"] = self._safe_text(tag("©alb"))
        row["artist"] = self._safe_text(tag("©ART"))
        row["track"] = self._pair_text(tag("trkn"), digits=2, include_total=True)
        row["release_date"] = self._safe_text(tag("©day"))
        row["disk"] = self._pair_text(tag("disk"), digits=2, include_total=False)
        row["genre"] = self._safe_text(tag("©gen"))

        comment_raw = tag("©cmt")
        row["real_ctime"] = self._comment_field(comment_raw, "real_ctime")
        row["real_mtime"] = self._comment_field(comment_raw, "real_mtime")
        row["after_of_episode"] = self._comment_field(comment_raw, "after_of_episode")
        row["overwrite_1_times"] = self._comment_field(comment_raw, "overwrite_1_times")
        row["overwrite_2_times"] = self._comment_field(comment_raw, "overwrite_2_times")
        row["overwrite_3_times"] = self._comment_field(comment_raw, "overwrite_3_times")
        row["free_listener_times"] = self._comment_field(comment_raw, "free_listener_times")
        return row

    def invalidate_folder(self, folder_path: str):
        self._folder_cache.pop(folder_path, None)

    def load_folder(self, folder_path: str):
        self._current_folder = folder_path if folder_path and os.path.isdir(folder_path) else ""
        self.setRowCount(0)

        if not self._current_folder:
            self._sync_scrollbars()
            return

        if self._current_folder in self._folder_cache:
            rows = self._folder_cache[self._current_folder]
        else:
            rows = []
            try:
                files = [
                    f for f in os.listdir(self._current_folder)
                    if os.path.isfile(os.path.join(self._current_folder, f))
                    and os.path.splitext(f)[1].lower() in {
                        ".mp4", ".m4v", ".mov", ".mkv", ".avi", ".wmv", ".flv"
                    }
                ]
                for filename in sorted(files):
                    rows.append(self._read_file_row(os.path.join(self._current_folder, filename)))
            except Exception:
                rows = []
            self._folder_cache[self._current_folder] = rows

        self.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, (_, key) in enumerate(self.COLUMNS):
                item = QtWidgets.QTableWidgetItem(row.get(key, ""))
                item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                item.setData(
                    QtCore.Qt.ItemDataRole.UserRole,
                    row.get("full_path", "") if c == 0 else row.get(key, "")
                )
                self.setItem(r, c, item)

        self._save_header_state()
        self._sync_scrollbars()

    def _sync_scrollbars(self):
        self.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded if self.rowCount() > 0
            else QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded if self.columnCount() > 0
            else QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

    def set_progress_widgets(self, progress_bar, progress_label):
        self.progress_bar = progress_bar
        self.progress_label = progress_label

    def current_file_path(self) -> str:
        row = self.currentRow()
        if row < 0:
            return ""
        item = self.item(row, 0)
        return self._safe_text(item.data(QtCore.Qt.ItemDataRole.UserRole) if item else "")

    def copy_to_clipboard(self, text: str):
        QtWidgets.QApplication.clipboard().setText(text)

    def _tab_join_rows(self, rows: list[list[str]]) -> str:
        return "\n".join("\t".join(row) for row in rows)

    def copy_current_cell(self):
        item = self.currentItem()
        self.copy_to_clipboard(item.text() if item else "")

    def copy_current_row(self):
        row = self.currentRow()
        if row < 0:
            self.copy_to_clipboard("")
            return
        values = [self.item(row, c).text() if self.item(row, c) else "" for c in range(self.columnCount())]
        self.copy_to_clipboard("\t".join(values))

    def copy_column(self, column: int, include_header: bool = True):
        if column < 0 or column >= self.columnCount():
            return
        values = []
        if include_header:
            values.append([self.horizontalHeaderItem(column).text() if self.horizontalHeaderItem(column) else ""])
        for row in range(self.rowCount()):
            item = self.item(row, column)
            values.append([item.text() if item else ""])
        self.copy_to_clipboard(self._tab_join_rows(values))

    def copy_all(self, include_headers: bool = True):
        rows = []
        if include_headers:
            rows.append([self.horizontalHeaderItem(c).text() if self.horizontalHeaderItem(c) else "" for c in range(self.columnCount())])
        for r in range(self.rowCount()):
            rows.append([self.item(r, c).text() if self.item(r, c) else "" for c in range(self.columnCount())])
        self.copy_to_clipboard(self._tab_join_rows(rows))

    def _path_for_row(self, row: int) -> str:
        item = self.item(row, 0)
        return self._safe_text(item.data(QtCore.Qt.ItemDataRole.UserRole) if item else "")

    def _parse_clipboard_matrix(self) -> list[list[str]]:
        text = QtWidgets.QApplication.clipboard().text()
        if not text:
            return []

        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = normalized.split("\n")
        if lines and lines[-1] == "":
            lines.pop()

        if not lines:
            return []

        return [line.split("\t") for line in lines]

    def _filesystem_timestamp_text(self, path: str, kind: str) -> str:
        try:
            st = os.stat(path)
            ts = st.st_ctime if kind == "ctime" else st.st_mtime
            return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return ""

    def _run_metadata_jobs(self, jobs: list[MetadataSaveJob]) -> None:
        if not jobs:
            return

        thread = MetadataSaveThread(jobs, self)
        thread.progress.connect(self._on_metadata_progress)
        thread.row_saved.connect(
            lambda r, p, ok: (
                self._refresh_row_from_disk(r, p)
                if ok else None
            )
        )
        thread.finished.connect(thread.deleteLater)

        if not hasattr(self, "_metadata_threads"):
            self._metadata_threads = []

        self._metadata_threads.append(thread)
        thread.finished.connect(
            lambda t=thread: self._metadata_threads.remove(t)
            if t in self._metadata_threads
            else None
        )
        thread.start()

    def _save_filesystem_times_from_column(self, target_key: str) -> None:
        if self.rowCount() <= 0:
            return

        title = "Obtener y pegar ctime" if target_key == "real_ctime" else "Obtener y pegar mtime"
        reply = QtWidgets.QMessageBox.question(
            self,
            title,
            "Esto aplicará el cambio desde la primera fila hasta la última.\n¿Continuar?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No,
        )
        if reply != QtWidgets.QMessageBox.StandardButton.Yes:
            return

        ts_kind = "ctime" if target_key == "real_ctime" else "mtime"
        jobs: list[MetadataSaveJob] = []

        for row in range(self.rowCount()):
            path = self._path_for_row(row)
            if not path or not os.path.exists(path):
                continue

            value = self._filesystem_timestamp_text(path, ts_kind)
            if not value:
                continue

            replace_foreign = False
            status, existing_text = comment_status_from_path(path)
            if status == "foreign":
                dlg = ForeignCommentDialog(self, existing_text)
                if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
                    return
                replace_foreign = True

            jobs.append(
                MetadataSaveJob(
                    row=row,
                    path=path,
                    updates={target_key: value},
                    replace_foreign_comments=replace_foreign,
                )
            )

        self._run_metadata_jobs(jobs)

    def _reset_metadata_progress(self) -> None:
        if self.progress_bar is not None:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
        if self.progress_label is not None:
            self.progress_label.setText("0/0")

    def _refresh_row_from_disk(self, row: int, path: str):
        folder = os.path.dirname(path)
        row_data = self._read_file_row(path)

        if folder in self._folder_cache:
            cached_rows = self._folder_cache[folder]
            for i, cached in enumerate(cached_rows):
                if cached.get("full_path") == path:
                    cached_rows[i] = row_data
                    break

        for column, (_, key) in enumerate(self.COLUMNS):
            item = self.item(row, column)
            if item is None:
                item = QtWidgets.QTableWidgetItem()
                self.setItem(row, column, item)

            item.setText(str(row_data.get(key, "")))

            if column == 0:
                item.setData(
                    QtCore.Qt.ItemDataRole.UserRole,
                    row_data.get("full_path", ""),
                )

    def _save_row_updates(self, row: int, updates_by_column: dict[int, str]) -> bool:
        path = self._path_for_row(row)
        if not path or not os.path.exists(path):
            return False

        updates_by_key: dict[str, str] = {}
        for column, value in updates_by_column.items():
            if 0 <= column < self.columnCount():
                key = self.COLUMNS[column][1]
                updates_by_key[key] = value

        if not updates_by_key:
            return False

        replace_foreign = False

        if any(
            self.COLUMNS[column][1] in COMMENT_KEYS
            for column in updates_by_column
        ):
            status, existing_text = comment_status_from_path(path)

            if status == "foreign":
                dlg = ForeignCommentDialog(self, existing_text)

                if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
                    return False

                replace_foreign = True

        job = MetadataSaveJob(
            row=row,
            path=path,
            updates=updates_by_key,
            replace_foreign_comments=replace_foreign,
        )

        thread = MetadataSaveThread([job], self)
        thread.progress.connect(self._on_metadata_progress)

        thread.row_saved.connect(
            lambda r, p, ok: (
                self._refresh_row_from_disk(r, p)
                if ok else None
            )
        )

        thread.finished.connect(thread.deleteLater)

        if not hasattr(self, "_metadata_threads"):
            self._metadata_threads = []

        self._metadata_threads.append(thread)

        thread.finished.connect(
            lambda t=thread: self._metadata_threads.remove(t)
            if t in self._metadata_threads
            else None
        )

        thread.start()

        return True

    def edit_current_cell(self):
        item = self.currentItem()
        row = self.currentRow()
        column = self.currentColumn()
        if item is None or row < 0 or column <= 0:
            return

        path = self._path_for_row(row)
        if not path:
            return

        key = self.COLUMNS[column][1]
        if key in COMMENT_KEYS:
            status, existing_text = comment_status_from_path(path)
            if status == "foreign":
                dlg = ForeignCommentDialog(self, existing_text)
                if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
                    return

        header_item = self.horizontalHeaderItem(column)
        label = header_item.text() if header_item else "Valor"
        value, ok = QtWidgets.QInputDialog.getText(
            self,
            "Editar esta celda",
            label,
            text=item.text(),
        )
        if not ok:
            return

        self._save_row_updates(row, {column: value})

    def paste_from_current_cell(self):
        row = self.currentRow()
        column = self.currentColumn()
        if row < 0 or column < 0:
            return
        self._paste_from_start(row, column)

    def _paste_from_start(self, start_row: int, start_col: int):
        matrix = self._parse_clipboard_matrix()
        if not matrix:
            return

        jobs = []

        for r_off, src_row in enumerate(matrix):
            target_row = start_row + r_off

            if target_row >= self.rowCount():
                break

            path = self._path_for_row(target_row)
            if not path:
                continue

            updates_by_key = {}
            replace_foreign = False

            for c_off, value in enumerate(src_row):
                target_col = start_col + c_off

                if target_col >= self.columnCount():
                    break

                key = self.COLUMNS[target_col][1]
                updates_by_key[key] = value

            if not updates_by_key:
                continue

            comment_columns = {
                "real_ctime",
                "real_mtime",
                "after_of_episode",
                "overwrite_1_times",
                "overwrite_2_times",
                "overwrite_3_times",
                "free_listener_times",
            }

            if any(key in comment_columns for key in updates_by_key):
                status, existing_text = comment_status_from_path(path)

                if status == "foreign":
                    dlg = ForeignCommentDialog(self, existing_text)

                    if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
                        return

                    replace_foreign = True

            jobs.append(
                MetadataSaveJob(
                    row=target_row,
                    path=path,
                    updates=updates_by_key,
                    replace_foreign_comments=replace_foreign,
                )
            )

        if not jobs:
            return

        thread = MetadataSaveThread(jobs, self)
        thread.progress.connect(self._on_metadata_progress)

        thread.row_saved.connect(
            lambda r, p, ok: (
                self._refresh_row_from_disk(r, p)
                if ok else None
            )
        )

        thread.finished.connect(thread.deleteLater)

        if not hasattr(self, "_metadata_threads"):
            self._metadata_threads = []

        self._metadata_threads.append(thread)

        thread.finished.connect(
            lambda t=thread: self._metadata_threads.remove(t)
            if t in self._metadata_threads
            else None
        )

        thread.start()

    def _on_metadata_progress(self, current: int, total: int, path: str):
        if self.progress_bar is not None:
            self.progress_bar.setMaximum(total)
            self.progress_bar.setValue(current)

        if self.progress_label is not None:
            filename = os.path.basename(path)
            self.progress_label.setText(f"{current}/{total} - {filename}")

        if current >= total and total > 0:
            self._progress_reset_timer.start(10000)
        elif self._progress_reset_timer.isActive():
            self._progress_reset_timer.stop()

    def resize_column_to_content(self, column: int):
        if 0 <= column < self.columnCount():
            self.resizeColumnToContents(column)

    def resize_all_columns_to_content(self):
        for column in range(self.columnCount()):
            self.resizeColumnToContents(column)

    def contextMenuEvent(self, event: QtGui.QContextMenuEvent):
        pos = event.pos()

        index = self.indexAt(pos)
        corner = (
            pos.x() < self.verticalHeader().width()
            and pos.y() < self.horizontalHeader().height()
        )
        header = (
            not index.isValid()
            and pos.y() < self.horizontalHeader().height()
        )

        cell = index.isValid()

        menu = QtWidgets.QMenu(self)

        if cell:
            index = self.indexAt(pos)
            if index.isValid():
                logical_col = index.column()
                header_text = (
                    self.horizontalHeaderItem(logical_col).text()
                    if self.horizontalHeaderItem(logical_col)
                    else ""
                )

                self.setCurrentCell(index.row(), index.column())
                
                menu.addAction("Editar esta celda", self.edit_current_cell)
                menu.addAction("Pegar datos desde esta celda", self.paste_from_current_cell)
                menu.addSeparator()

                menu.addAction("Copiar celda", self.copy_current_cell)
                menu.addAction("Copiar fila", self.copy_current_row)
                menu.addSeparator()

                header_action = menu.addAction(f"Copiar encabezado: {header_text}")
                header_action.triggered.connect(
                    lambda _=False, t=header_text: self.copy_to_clipboard(t)
                )
                
                if logical_col in (8, 9):
                    menu.addSeparator()
                    menu.addAction(
                        "Obtener y pegar ctime",
                        lambda: self._save_filesystem_times_from_column("real_ctime")
                    )
                    menu.addAction(
                        "Obtener y pegar mtime",
                        lambda: self._save_filesystem_times_from_column("real_mtime")
                    )
                
                menu.addAction(
                    "Copiar columna completa",
                    lambda col=logical_col: self.copy_column(col, include_header=True)
                )
                menu.addAction(
                    "Copiar columna sin encabezado",
                    lambda col=logical_col: self.copy_column(col, include_header=False)
                )
                menu.addSeparator()
                menu.addAction(
                    "Ajustar esta columna al contenido",
                    lambda col=logical_col: self.resize_column_to_content(col)
                )
                menu.addAction(
                    "Ajustar todas las columnas al contenido",
                    self.resize_all_columns_to_content
                )
                menu.addSeparator()
                menu.addAction(
                    "Copiar tabla con encabezados",
                    lambda: self.copy_all(True)
                )
        else:
            return super().contextMenuEvent(event)

        if not menu.isEmpty():
            menu.exec(event.globalPos())
            event.accept()
            return
        super().contextMenuEvent(event)