import json
import os
from typing import Any

from PyQt6 import QtCore, QtGui, QtWidgets

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
        ("Disk (SeasonNum)", "disk"),
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
        text = self._safe_text(comment_raw)
        if not text:
            return ""
        try:
            data = json.loads(text)
        except Exception:
            return ""
        if not isinstance(data, dict):
            return ""
        value = data.get(key, "")
        if key == "free_listener_times":
            if isinstance(value, list):
                items = [self._safe_text(v) for v in value if self._safe_text(v)]
                return " / ".join(items)
            return ""
        return self._safe_text(value)

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

                menu.addAction("Copiar celda", self.copy_current_cell)
                menu.addAction("Copiar fila", self.copy_current_row)
                menu.addSeparator()

                header_action = menu.addAction(f"Copiar encabezado: {header_text}")
                header_action.triggered.connect(
                    lambda _=False, t=header_text: self.copy_to_clipboard(t)
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