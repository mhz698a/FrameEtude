import os, datetime, subprocess, re
import functools
from ctypes import wintypes, windll
from typing import Any
from PyQt6 import QtCore, QtGui, QtWidgets
import config
from duration_async_lib import DurationFetchJob, DurationFetchThread
from metadata_async_lib import MetadataSaveJob, MetadataSaveThread
from metadata_edit_lib import (
    COMMENT_KEYS,
    ForeignCommentDialog,
    ForeignCommentSummaryDialog,
    comment_display_value,
    comment_status_from_path,
)
from about_season_dialog import load_seasons_for_year

try:
    from mutagen.mp4 import MP4
except Exception:
    MP4 = None

def windows_sort_key():
    _StrCmpLogicalW = windll.Shlwapi.StrCmpLogicalW
    _StrCmpLogicalW.argtypes = [wintypes.LPWSTR, wintypes.LPWSTR]
    _StrCmpLogicalW.restype = wintypes.INT

    return functools.cmp_to_key(_StrCmpLogicalW)

class FileTableWidget(QtWidgets.QTableWidget):
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
    row_count_changed = QtCore.pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._folder_cache: dict[str, list[dict[str, Any]]] = {}
        self._duration_cache: dict[str, str] = {}
        self._duration_threads: list[DurationFetchThread] = []
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
        self.setColumnHidden(len(self.COLUMNS) - 1, True)
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
        row["duration"] = self._duration_cache.get(path, "")
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
            self.row_count_changed.emit(0)
            self._sync_scrollbars()
            return

        if self._current_folder in self._folder_cache:
            rows = self._folder_cache[self._current_folder]
            for idx, row_data in enumerate(rows, start=1):
                self._append_row_data(row_data)
                self.row_count_changed.emit(idx)
                QtWidgets.QApplication.processEvents()

            self._save_header_state()
            self._sync_scrollbars()
            self.row_count_changed.emit(len(rows))
            self._start_duration_fetch(rows)
            return

        rows = []
        try:
            entries = sorted(
                [e for e in os.scandir(self._current_folder) if e.is_file()],
                key=lambda e: windows_sort_key()(e.name),
            )

            for entry in entries:
                if not entry.is_file():
                    continue

                if os.path.splitext(entry.name)[1].lower() not in {
                    ".mp4", ".m4v", ".mov", ".mkv", ".avi", ".wmv", ".flv"
                }:
                    continue

                row = self._read_file_row(entry.path)
                rows.append(row)
                self._append_row_data(row)
                self.row_count_changed.emit(len(rows))
                QtWidgets.QApplication.processEvents()
        except Exception:
            pass

        self._folder_cache[self._current_folder] = rows
        self._save_header_state()
        self._sync_scrollbars()
        self.row_count_changed.emit(len(rows))
        self._start_duration_fetch(rows)

    def _append_row_data(self, row_data: dict[str, Any]) -> None:
        row_index = self.rowCount()
        self.insertRow(row_index)

        for column, (_, key) in enumerate(self.COLUMNS):
            item = QtWidgets.QTableWidgetItem(row_data.get(key, ""))
            item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            item.setData(
                QtCore.Qt.ItemDataRole.UserRole,
                row_data.get("full_path", "") if key == "filename" else row_data.get(key, ""),
            )
            self.setItem(row_index, column, item)

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
        item = self.item(row, self._filename_column())
        return self._safe_text(item.data(QtCore.Qt.ItemDataRole.UserRole) if item else "")

    def current_folder_path(self) -> str:
        return self._safe_text(getattr(self, "_current_folder", ""))

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
        item = self.item(row, self._filename_column())
        return self._safe_text(item.data(QtCore.Qt.ItemDataRole.UserRole) if item else "")

    def _track_column_index(self) -> int:
        for index, (_, key) in enumerate(self.COLUMNS):
            if key == "track":
                return index
        return -1

    def _track_number_from_text(self, text: str) -> int | None:
        raw = self._safe_text(text)
        if not raw:
            return None
        head = raw.split("/", 1)[0].strip()
        if not head.isdigit():
            return None
        value = int(head)
        return value if value > 0 else None

    def _track_number_from_row(self, row: int) -> int | None:
        track_col = self._track_column_index()
        if track_col < 0:
            return None
        item = self.item(row, track_col)
        return self._track_number_from_text(item.text() if item else "")

    def _used_track_numbers(self, exclude_row: int | None = None) -> set[int]:
        used: set[int] = set()
        track_col = self._track_column_index()
        if track_col < 0:
            return used

        for row in range(self.rowCount()):
            if exclude_row is not None and row == exclude_row:
                continue
            number = self._track_number_from_row(row)
            if number is not None:
                used.add(number)

        return used

    def _set_track_number(self, row: int, number: int, total: int | None = None) -> None:
        total = total if total is not None and total > 0 else self.rowCount()
        track_col = self._track_column_index()
        if track_col < 0 or total <= 0:
            return
        self._save_row_updates(row, {track_col: f"{number:02d}/{total:02d}"})

    def _revoke_track_number(self, row: int) -> None:
        track_col = self._track_column_index()
        if track_col < 0:
            return
        self._save_row_updates(row, {track_col: ""})

    def _assign_remaining_track_numbers(self, total_override: int | None = None) -> None:
        total = total_override if total_override is not None and total_override > 0 else self.rowCount()
        track_col = self._track_column_index()
        if track_col < 0 or total <= 0:
            return

        used = self._used_track_numbers()
        available = [n for n in range(1, total + 1) if n not in used]

        jobs: list[MetadataSaveJob] = []
        for row in range(self.rowCount()):
            if not available:
                break

            path = self._path_for_row(row)
            if not path or not os.path.exists(path):
                continue
            if self._track_number_from_row(row) is not None:
                continue

            number = available.pop(0)
            jobs.append(
                MetadataSaveJob(
                    row=row,
                    path=path,
                    updates={"track": f"{number:02d}/{total:02d}"},
                    replace_foreign_comments=False,
                )
            )

        if jobs:
            self._run_metadata_jobs(jobs)

    def _assign_remaining_track_numbers_custom_total(self) -> None:
        current_total = self.rowCount() if self.rowCount() > 0 else 1
        total, ok = QtWidgets.QInputDialog.getInt(
            self,
            "Diferent Total Tracks",
            "Total Tracks:",
            current_total,
            1,
            99999,
            1,
        )
        if not ok:
            return

        self._assign_remaining_track_numbers(total)

    def _foreign_comment_summary_text(self, entries: list[tuple[str, str]]) -> str:
        blocks = []
        for path, text in entries:
            name = os.path.basename(path) if path else ""
            blocks.append(f"Archivo: {name}\nRuta: {path}\n\n{text}")
        return ("\n" + ("-" * 72) + "\n").join(blocks)

    def _show_foreign_comment_summary(self, entries: list[tuple[str, str]]) -> bool:
        if not entries:
            return True
        dlg = ForeignCommentSummaryDialog(self, self._foreign_comment_summary_text(entries))
        return dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted

    def _foreign_comment_resolution(
        self,
        path: str,
        foreign_entries: list[tuple[str, str]],
        collecting_all: bool,
        *,
        batch_mode: bool = False,
    ) -> tuple[bool, bool, bool]:
        status, existing_text = comment_status_from_path(path)
        if status != "foreign":
            return True, collecting_all, False

        if batch_mode and collecting_all:
            foreign_entries.append((path, existing_text))
            return True, collecting_all, True

        dlg = ForeignCommentDialog(self, existing_text)
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return False, collecting_all, False

        choice = getattr(dlg, "choice", "yes")
        if choice == "no_all":
            return False, collecting_all, False

        if batch_mode and choice == "yes_all":
            foreign_entries.append((path, existing_text))
            return True, True, True

        return True, collecting_all, True

    def _add_track_context_menu(self, menu: QtWidgets.QMenu, row: int) -> None:
        total = self.rowCount()
        if total <= 0:
            return

        track_menu = menu.addMenu("Track (EpNum)")
        set_menu = track_menu.addMenu("Establecer numero de pista")
        used_numbers = self._used_track_numbers()

        for start in range(1, total + 1, 10):
            end = min(start + 9, total)
            block_menu = set_menu.addMenu(f"{start:02d}-{end:02d}")

            for number in range(start, end + 1):
                action = block_menu.addAction(f"{number:02d}/{total:02d}")
                if number in used_numbers:
                    action.setEnabled(False)
                    action.setToolTip("Este número ya está asignado a otra pista")
                    continue
                action.triggered.connect(
                    lambda _checked=False, n=number, r=row: self._set_track_number(r, n)
                )

        track_menu.addAction("Asignar el resto", self._assign_remaining_track_numbers)
        track_menu.addAction(
            "Revocar numero de pista",
            lambda _checked=False, r=row: self._revoke_track_number(r),
        )
        track_menu.addAction(
            "Asignar el resto pero con total diferente",
            lambda _checked=False: self._assign_remaining_track_numbers_custom_total(),
        )

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

        slow_jobs = [job for job in jobs if job.path]
        if slow_jobs and self.progress_label is not None:
            self.progress_label.setText(
                f"Preparando... {len(slow_jobs)} archivo(s)"
            )

        thread = MetadataSaveThread(jobs, self)
        thread.job_started.connect(self._on_metadata_job_started)
        thread.progress.connect(self._on_metadata_progress)
        updates_by_row = {job.row: job.updates for job in jobs}
        thread.row_saved.connect(
            lambda r, p, ok, u=updates_by_row: (
                self._apply_saved_updates_to_row(r, p, u.get(r, {}))
                if ok else None
            )
        )
        self._on_metadata_job_started(
            1,
            len(jobs),
            jobs[0].path,
            False,
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
        foreign_entries: list[tuple[str, str]] = []
        collecting_all = False

        for row in range(self.rowCount()):
            path = self._path_for_row(row)
            if not path or not os.path.exists(path):
                continue

            value = self._filesystem_timestamp_text(path, ts_kind)
            if not value:
                continue

            can_continue, collecting_all, replace_foreign = self._foreign_comment_resolution(
                path,
                foreign_entries,
                collecting_all,
                batch_mode=True,
            )
            if not can_continue:
                return

            jobs.append(
                MetadataSaveJob(
                    row=row,
                    path=path,
                    updates={target_key: value},
                    replace_foreign_comments=replace_foreign,
                )
            )

        if not self._show_foreign_comment_summary(foreign_entries):
            return

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
                item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                self.setItem(row, column, item)

            value = str(row_data.get(key, ""))
            if key == "duration" and not value and item.text():
                value = item.text()

            item.setText(value)

            if key == "filename":
                item.setData(
                    QtCore.Qt.ItemDataRole.UserRole,
                    row_data.get("full_path", ""),
                )

    def _apply_saved_updates_to_row(self, row: int, path: str, updates_by_key: dict[str, str]) -> None:
        folder = os.path.dirname(path)

        if folder in self._folder_cache:
            cached_rows = self._folder_cache[folder]
            for cached in cached_rows:
                if cached.get("full_path") == path:
                    cached.update(updates_by_key)
                    cached["filename"] = os.path.basename(path)
                    cached["full_path"] = path
                    break

        for column, (_, key) in enumerate(self.COLUMNS):
            item = self.item(row, column)
            if item is None:
                item = QtWidgets.QTableWidgetItem()
                item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                self.setItem(row, column, item)

            if key == "filename":
                item.setText(os.path.basename(path))
                item.setData(QtCore.Qt.ItemDataRole.UserRole, path)
                continue

            if key in updates_by_key:
                item.setText(str(updates_by_key[key]))

    def _save_row_updates(self, row: int, updates_by_column: dict[int, str]) -> bool:
        path = self._path_for_row(row)
        if not path or not os.path.exists(path):
            return False

        updates_by_key: dict[str, str] = {}
        for column, value in updates_by_column.items():
            if 0 <= column < self.columnCount():
                key = self.COLUMNS[column][1]
                if key == "duration":
                    continue
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
        thread.job_started.connect(self._on_metadata_job_started)
        thread.progress.connect(self._on_metadata_progress)
        thread.row_saved.connect(
            lambda r, p, ok, u=updates_by_key: (
                self._apply_saved_updates_to_row(r, p, u)
                if ok else None
            )
        )
        self._on_metadata_job_started(
            1,
            1,
            path,
            False,
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

    def _on_metadata_job_started(self, current: int,total: int,
                                path: str, moov_front: bool,):
        self._moov_front_cache = getattr(self, "_moov_front_cache", {})
        self._moov_front_cache[path] = moov_front

        if self.progress_bar is not None:
            self.progress_bar.setMaximum(total)
            self.progress_bar.setValue(max(0, current - 1))

        if self.progress_label is not None:
            filename = os.path.basename(path)
            if moov_front:
                self.progress_label.setText(f"Procesando {current}/{total} - {filename}")
            else:
                self.progress_label.setText(
                    f"Procesando (no moov) {current}/{total} - {filename}"
                )

        if self._progress_reset_timer.isActive():
            self._progress_reset_timer.stop()

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
        foreign_entries: list[tuple[str, str]] = []
        collecting_all = False

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
                if target_col == 0:
                    continue

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
                can_continue, collecting_all, replace_foreign = self._foreign_comment_resolution(
                    path,
                    foreign_entries,
                    collecting_all,
                    batch_mode=True,
                )
                if not can_continue:
                    return

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

        if not self._show_foreign_comment_summary(foreign_entries):
            return

        thread = MetadataSaveThread(jobs, self)
        thread.job_started.connect(self._on_metadata_job_started)
        thread.progress.connect(self._on_metadata_progress)

        thread.row_saved.connect(
            lambda r, p, ok: (
                self._refresh_row_from_disk(r, p)
                if ok else None
            )
        )

        self._on_metadata_job_started(
            1,
            len(jobs),
            jobs[0].path,
            False,
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
            moov_front = getattr(self, "_moov_front_cache", {}).get(path, True)
            note = "" if moov_front else "no moov;"
            self.progress_label.setText(f"{note} {current}/{total} - {filename}")

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
        menu.setStyleSheet("""
            QMenu::item {
                padding: 4px 20px;
                color: #ffffff; /* Color de texto normal (ej. tema oscuro) */
            }
            QMenu::item:selected {
                background-color: #007acc; /* Color al pasar el cursor */
            }
            QMenu::item:disabled {
                color: #666666; /* Texto gris para indicar que está usado */
                background-color: transparent; /* Evita que resalte */
            }
        """)

        if cell:
            index = self.indexAt(pos)
            if index.isValid():

                logical_col = index.column()
                logical_key = self.COLUMNS[logical_col][1]

                header_text = (
                    self.horizontalHeaderItem(logical_col).text()
                    if self.horizontalHeaderItem(logical_col)
                    else ""
                )

                self.setCurrentCell(index.row(), index.column())

                if logical_col != 0:
                    menu.addAction("Editar esta celda", self.edit_current_cell)
                    menu.addAction("Pegar datos desde esta celda", self.paste_from_current_cell)
                    menu.addAction(
                        "Pegar y Rellenar esta columna",
                        lambda col=logical_col: self.fill_column_from_clipboard(col),
                    )
                    menu.addAction(
                        "Rellenar esta columna con un valor",
                        lambda col=logical_col: self.fill_column_from_input(col),
                    )
                    menu.addAction(
                        "Vaciar esta columna",
                        lambda col=logical_col: self.fill_column_with_voids(col),
                    )
                    menu.addSeparator()

                menu.addAction("Copiar celda", self.copy_current_cell)
                menu.addAction("Copiar fila", self.copy_current_row)
                menu.addSeparator()

                header_action = menu.addAction(f"Copiar encabezado: {header_text}")
                header_action.triggered.connect(
                    lambda _=False, t=header_text: self.copy_to_clipboard(t)
                )

                if logical_key in ("album", "artist"):
                    menu.addSeparator()
                    self._add_season_context_menu(menu, index.row(), logical_col)

                if logical_key == "track":
                    menu.addSeparator()
                    self._add_track_context_menu(menu, index.row())


                if logical_key == "real_ctime":
                    menu.addSeparator()
                    menu.addAction(
                        "Rellenar esta columna con ctime",
                        lambda: self._save_filesystem_times_from_column("real_ctime")
                    )
                    self._add_real_timestamp_single_context_menu(menu, index.row(), logical_col)


                if logical_key == "real_mtime":
                    menu.addSeparator()
                    menu.addAction(
                        "Rellenar esta columna con mtime",
                        lambda: self._save_filesystem_times_from_column("real_mtime")
                    )
                    self._add_real_timestamp_single_context_menu(menu, index.row(), logical_col)


                if logical_key == "genre":
                    menu.addSeparator()
                    genre_menu = menu.addMenu("Colocar tipo a toda la columna")

                    for genre_value in ("Episode", "Movie", "Soundtrack", "Short"):
                        genre_menu.addAction(
                            genre_value,
                            lambda checked=False, value=genre_value: self.fill_genre_column_with_value(value),
                        )

                    self._add_genre_single_context_menu(menu, index.row(), logical_col)

                if logical_key == "release_date":
                    menu.addSeparator()
                    release_menu = menu.addMenu("Obtener fechas del filename")
                    release_menu.addAction(
                        "Obtener solo desde este archivo",
                        lambda: self._save_release_date_from_filename(index.row()),
                    )
                    release_menu.addAction(
                        "Asignar a toda esta columna",
                        self._save_release_dates_from_filenames,
                    )

                if logical_key == "disk":
                    menu.addSeparator()
                    disk_menu = menu.addMenu("Agregar numero de disco/temporada")

                    disk_menu.addAction(
                        "Aplicar solo a este archivo",
                        lambda row=index.row(): self._apply_disk_season_to_row(row),
                    )

                    disk_menu.addAction(
                        "Aplicar en toda la columna",
                        lambda col=logical_col: self._apply_disk_season_to_column(col),
                    )

                menu.addSeparator()
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

                menu.addSeparator()
                menu.addAction("Copiar Ruta de este archivo", self.copy_current_file_path)
                menu.addAction("Abrir este archivo con rename dialog", self.open_current_file_with_rename_dialog)
                menu.addAction("Abrir este archivo", self.open_current_file)
        else:
            return super().contextMenuEvent(event)

        if not menu.isEmpty():
            menu.exec(event.globalPos())
            event.accept()
            return
        super().contextMenuEvent(event)

    def copy_current_file_path(self):
        path = self.current_file_path()
        if path:
            QtWidgets.QApplication.clipboard().setText(path)

    def open_current_file_with_rename_dialog(self):
        path = self.current_file_path()
        if not path:
            return

        command = ["pythonw", config.RENAME_DIALOG_SCRIPT, path]

        try:
            subprocess.Popen(command)
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                f"No se pudo abrir rename dialog.\n\n{e}",
            )

    def open_current_file(self):
        main_window = self.window()
        if hasattr(main_window, "load_selected_file"):
            main_window.load_selected_file()

    def _filename_column(self) -> int:
        for index, (_, key) in enumerate(self.COLUMNS):
            if key == "filename":
                return index
        return 0

    def _start_duration_fetch(self, rows: list[dict[str, Any]]) -> None:
        jobs = []
        for row in rows:
            path = self._safe_text(row.get("full_path", ""))
            if path and path not in self._duration_cache:
                jobs.append(DurationFetchJob(path=path))

        if not jobs:
            return

        thread = DurationFetchThread(jobs, self)
        thread.duration_ready.connect(self._on_duration_ready)
        thread.finished.connect(thread.deleteLater)

        self._duration_threads.append(thread)
        thread.finished.connect(
            lambda t=thread: self._duration_threads.remove(t)
            if t in self._duration_threads
            else None
        )
        thread.start()

    def _on_duration_ready(self, path: str, duration_text: str) -> None:
        self._duration_cache[path] = duration_text
        self._update_duration_for_path(path, duration_text)

    def _update_duration_for_path(self, path: str, duration_text: str) -> None:
        filename_col = self._filename_column()

        for row in range(self.rowCount()):
            item = self.item(row, filename_col)
            if not item:
                continue
            if self._safe_text(item.data(QtCore.Qt.ItemDataRole.UserRole)) != path:
                continue

            duration_item = self.item(row, 0)
            if duration_item is None:
                duration_item = QtWidgets.QTableWidgetItem()
                duration_item.setFlags(
                    duration_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable
                )
                self.setItem(row, 0, duration_item)

            duration_item.setText(duration_text)
            return

    def fill_column_from_clipboard(self, column: int):
        if column <= 0 or column >= self.columnCount():
            return

        key = self.COLUMNS[column][1]
        if key == "duration":
            return

        value = QtWidgets.QApplication.clipboard().text()
        if not value.strip():
            return

        reply = QtWidgets.QMessageBox.warning(
            self,
            "Advertencia",
            f"Rellenaras esta columna con un solo valor. Si estas pegando más valores esta no es la opcion.\n\n¿Deseas proceder?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No
        )

        if reply != QtWidgets.QMessageBox.StandardButton.Yes:
            return

        jobs = []
        foreign_entries: list[tuple[str, str]] = []
        collecting_all = False

        for row in range(self.rowCount()):
            path = self._path_for_row(row)
            if not path or not os.path.exists(path):
                continue

            replace_foreign = False
            if key in COMMENT_KEYS:
                can_continue, collecting_all, replace_foreign = self._foreign_comment_resolution(
                    path,
                    foreign_entries,
                    collecting_all,
                    batch_mode=True,
                )
                if not can_continue:
                    return

            jobs.append(
                MetadataSaveJob(
                    row=row,
                    path=path,
                    updates={key: value},
                    replace_foreign_comments=replace_foreign,
                )
            )

        if not self._show_foreign_comment_summary(foreign_entries):
            return

        if jobs:
            self._run_metadata_jobs(jobs)

    def fill_column_from_input(self, column: int):
        if column <= 0 or column >= self.columnCount():
            return

        key = self.COLUMNS[column][1]
        if key == "duration":
            return

        value, ok = QtWidgets.QInputDialog.getText(
            self,
            "Introducir valor",
            f"Ingrese el nuevo valor para rellenar esta columna '{key}':"
        )

        if not ok or not value.strip():
            return

        jobs = []

        for row in range(self.rowCount()):
            path = self._path_for_row(row)
            if not path or not os.path.exists(path):
                continue

            replace_foreign = False
            if key in COMMENT_KEYS:
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
                    updates={key: value},
                    replace_foreign_comments=replace_foreign,
                )
            )

        if jobs:
            self._run_metadata_jobs(jobs)

    def fill_column_with_voids(self, column: int):
        if column <= 0 or column >= self.columnCount():
            return

        key = self.COLUMNS[column][1]
        if key == "duration":
            return

        reply = QtWidgets.QMessageBox.warning(
            self,
            "Advertencia de borrado",
            f"Se vaciará toda la columna '{key}'. Asegúrate de respaldar la información antes de continuar.\n\n¿Deseas proceder?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No
        )

        if reply != QtWidgets.QMessageBox.StandardButton.Yes:
            return

        value = ''

        jobs = []

        for row in range(self.rowCount()):
            path = self._path_for_row(row)
            if not path or not os.path.exists(path):
                continue

            replace_foreign = False
            if key in COMMENT_KEYS:
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
                    updates={key: value},
                    replace_foreign_comments=replace_foreign,
                )
            )

        if jobs:
            self._run_metadata_jobs(jobs)


    def _genre_column(self) -> int:
        for index, (_, key) in enumerate(self.COLUMNS):
            if key == "genre":
                return index
        return -1


    def fill_genre_column_with_value(self, value: str) -> None:
        column = self._genre_column()
        if column < 0 or self.rowCount() <= 0:
            return

        jobs = []
        for row in range(self.rowCount()):
            path = self._path_for_row(row)
            if not path or not os.path.exists(path):
                continue

            jobs.append(
                MetadataSaveJob(
                    row=row,
                    path=path,
                    updates={"genre": value},
                    replace_foreign_comments=False,
                )
            )

        self._run_metadata_jobs(jobs)

    def _release_date_from_filename(self, path: str) -> str:
        filename = os.path.basename(path)

        for match in re.finditer(r'(?<!\d)((?:19|20)\d{2})-(\d{2})-(\d{2})(?!\d)', filename):
            year, month, day = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
            try:
                datetime.date(year, month, day)
            except ValueError:
                continue
            return f"{year:04d}-{month:02d}-{day:02d}"

        return ""

    def _release_date_column_index(self) -> int:
        for index, (_, key) in enumerate(self.COLUMNS):
            if key == "release_date":
                return index
        return -1

    def _save_release_date_from_filename(self, row: int) -> None:
        path = self._path_for_row(row)
        if not path or not os.path.exists(path):
            return

        value = self._release_date_from_filename(path)
        if not value:
            return

        release_col = self._release_date_column_index()
        if release_col < 0:
            return

        self._save_row_updates(row, {release_col: value})

    def _save_release_dates_from_filenames(self) -> None:
        if self.rowCount() <= 0:
            return

        reply = QtWidgets.QMessageBox.question(
            self,
            "Obtener fechas del filename",
            "Esto aplicará el cambio desde la primera fila hasta la última.\n¿Continuar?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No,
        )
        if reply != QtWidgets.QMessageBox.StandardButton.Yes:
            return

        jobs: list[MetadataSaveJob] = []

        for row in range(self.rowCount()):
            path = self._path_for_row(row)
            if not path or not os.path.exists(path):
                continue

            value = self._release_date_from_filename(path)
            if not value:
                continue

            jobs.append(
                MetadataSaveJob(
                    row=row,
                    path=path,
                    updates={"release_date": value},
                    replace_foreign_comments=False,
                )
            )

        if jobs:
            self._run_metadata_jobs(jobs)

    def _selected_year_px(self) -> str:
        window = self.window()
        combo_year = getattr(window, "combo_year", None)
        year = combo_year.currentText().strip() if combo_year else ""

        if not year or year == "(no encontrado)":
            return ""

        try:
            return f"{int(year) - 2003:02d}"
        except ValueError:
            return ""

    def _selected_year_full(self) -> str:
        window = self.window()
        combo_year = getattr(window, "combo_year", None)
        year = combo_year.currentText().strip() if combo_year else ""

        if not year or year == "(no encontrado)":
            return ""

        try:
            return str(year)
        except ValueError:
            return ""

    def _disk_column_index(self) -> int:
        for index, (_, key) in enumerate(self.COLUMNS):
            if key == "disk":
                return index
        return -1

    def _apply_disk_season_to_row(self, row: int) -> None:
        px = self._selected_year_px()
        if not px:
            return

        disk_col = self._disk_column_index()
        if disk_col < 0:
            return

        self._save_row_updates(row, {disk_col: px})

    def _apply_disk_season_to_column(self, column: int) -> None:
        px = self._selected_year_px()
        if not px:
            return

        if column < 0 or column >= self.columnCount():
            return

        jobs: list[MetadataSaveJob] = []

        for row in range(self.rowCount()):
            path = self._path_for_row(row)
            if not path or not os.path.exists(path):
                continue

            jobs.append(
                MetadataSaveJob(
                    row=row,
                    path=path,
                    updates={self.COLUMNS[column][1]: px},
                    replace_foreign_comments=False,
                )
            )

        if jobs:
            self._run_metadata_jobs(jobs)

    def set_overwrite_1_hidden(self, hidden: bool) -> None:
        for column, (_, key) in enumerate(self.COLUMNS):
            if key == "overwrite_1_times":
                self.setColumnHidden(column, hidden)
                break


    def _column_index_by_key(self, key: str) -> int:
        for index, (_, current_key) in enumerate(self.COLUMNS):
            if current_key == key:
                return index
        return -1


    def _release_year_for_row(self, row: int) -> str:
        release_col = self._column_index_by_key("release_date")
        if release_col < 0:
            return ""

        item = self.item(row, release_col)
        text = self._safe_text(item.text() if item else "")
        match = re.search(r"(\d{4})", text)
        return match.group(1) if match else ""


    def _season_names_for_row(self, row: int) -> list[str]:
        year = self._selected_year_full()
        if not year:
            return []

        names: list[str] = []
        for record in load_seasons_for_year(year):
            name = self._safe_text(record.get("precure_season_name", ""))
            if name:
                names.append(name)
        return names


    def _apply_value_to_column(self, column: int, value: str, *, only_row: int | None = None) -> None:
        if column <= 0 or column >= self.columnCount():
            return

        if only_row is not None:
            self._save_row_updates(only_row, {column: value})
            return

        key = self.COLUMNS[column][1]
        if key == "duration":
            return

        jobs: list[MetadataSaveJob] = []
        for row in range(self.rowCount()):
            path = self._path_for_row(row)
            if not path or not os.path.exists(path):
                continue

            jobs.append(
                MetadataSaveJob(
                    row=row,
                    path=path,
                    updates={key: value},
                    replace_foreign_comments=False,
                )
            )

        if jobs:
            self._run_metadata_jobs(jobs)


    def _add_season_context_menu(self, menu: QtWidgets.QMenu, row: int, column: int) -> None:
        key = self.COLUMNS[column][1]
        if key not in ("album", "artist"):
            return

        season_menu = menu.addMenu("Obtener Temporada/Sp")
        single_menu = season_menu.addMenu("Aplicar solo a este archivo")
        column_menu = season_menu.addMenu("Aplicar a toda la columna")

        names = self._season_names_for_row(row)
        if not names:
            a1 = single_menu.addAction("Sin valores para este año")
            a1.setEnabled(False)
            a2 = column_menu.addAction("Sin valores para este año")
            a2.setEnabled(False)
            return

        for name in names:
            single_menu.addAction(
                name,
                lambda _checked=False, col=column, r=row, v=name: self._apply_value_to_column(col, v, only_row=r),
            )
            column_menu.addAction(
                name,
                lambda _checked=False, col=column, v=name: self._apply_value_to_column(col, v),
            )


    def _add_genre_single_context_menu(self, menu: QtWidgets.QMenu, row: int, column: int) -> None:
        if self.COLUMNS[column][1] != "genre":
            return

        genre_menu = menu.addMenu("Colocar tipo solo a este archivo")
        for value in ("Episode", "Movie", "Soundtrack", "Short"):
            genre_menu.addAction(
                value,
                lambda _checked=False, r=row, c=column, v=value: self._save_row_updates(r, {c: v}),
            )


    def _save_single_row_filesystem_time(self, row: int, column: int, target_key: str) -> None:
        path = self._path_for_row(row)
        if not path or not os.path.exists(path):
            return

        title = "Obtener ctime solo para este archivo" if target_key == "real_ctime" else "Obtener mtime solo para este archivo"
        reply = QtWidgets.QMessageBox.question(
            self,
            title,
            "Esto aplicará el cambio solo a este archivo.\n¿Continuar?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No,
        )
        if reply != QtWidgets.QMessageBox.StandardButton.Yes:
            return

        ts_kind = "ctime" if target_key == "real_ctime" else "mtime"
        value = self._filesystem_timestamp_text(path, ts_kind)
        if not value:
            return

        self._save_row_updates(row, {column: value})


    def _add_real_timestamp_single_context_menu(self, menu: QtWidgets.QMenu, row: int, column: int) -> None:
        key = self.COLUMNS[column][1]
        if key not in ("real_ctime", "real_mtime"):
            return

        label = (
            "Obtener ctime solo para este archivo"
            if key == "real_ctime"
            else "Obtener mtime solo para este archivo"
        )
        menu.addAction(
            label,
            lambda _checked=False, r=row, c=column, k=key: self._save_single_row_filesystem_time(r, c, k),
        )