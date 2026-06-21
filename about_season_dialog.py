import json
import os

from PyQt6 import QtCore, QtWidgets


def _repo_root() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def _seasons_path() -> str:
    return os.path.join(_repo_root(), "seasons.json")


def load_seasons_for_year(year: str) -> list[dict]:
    year = str(year).strip()
    if not year:
        return []

    try:
        with open(_seasons_path(), "r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except Exception:
        return []

    matches: list[dict] = []
    for obj in payload.get("seasons", []):
        if str(obj.get("year", "")).strip() == year:
            matches.append(obj)

    return matches


class AboutSeasonDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, year: str = "", master_folder_name: str = ""):
        super().__init__(parent)
        self.setWindowTitle("About")
        self.setModal(True)
        self.resize(760, 700)

        self._year = str(year).strip()
        self._master_folder_name = str(master_folder_name).strip()
        self._data = load_seasons_for_year(self._year)

        self._build_ui()

    def _build_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        title = QtWidgets.QLabel("About")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        root.addWidget(title)

        if not self._data:
            msg = QtWidgets.QLabel(f"No se encontró información para el año {self._year}.")
            msg.setWordWrap(True)
            root.addWidget(msg)

            footer = QtWidgets.QHBoxLayout()
            footer.addStretch(1)
            btn_close = QtWidgets.QPushButton("Close")
            btn_close.clicked.connect(self.accept)
            footer.addWidget(btn_close)
            root.addLayout(footer)
            return

        if len(self._data) == 1:
            root.addWidget(self._record_scroll(self._data[0]), 1)
        else:
            tabs = QtWidgets.QTabWidget()
            for idx, record in enumerate(self._data, start=1):
                tabs.addTab(self._record_scroll(record), self._record_title(record, idx))
            root.addWidget(tabs, 1)

        footer = QtWidgets.QHBoxLayout()
        footer.addStretch(1)
        btn_close = QtWidgets.QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        footer.addWidget(btn_close)
        root.addLayout(footer)

    def _record_title(self, record: dict, index: int) -> str:
        name = (
            str(record.get("precure_season_name", "")).strip()
            or str(record.get("precure_season_romaji_name", "")).strip()
            or str(record.get("precure_season_kanji_name", "")).strip()
            or f"Entrada {index}"
        )
        return f"{index}. {name}"

    def _record_scroll(self, record: dict) -> QtWidgets.QScrollArea:
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)

        body = QtWidgets.QWidget()
        body_layout = QtWidgets.QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(10)

        self._add_field(body_layout, "year", self._year or record.get("year", ""), 16, False, 36)
        self._add_field(body_layout, "precure_season_name", record.get("precure_season_name", ""), 14, False, 42)
        self._add_field(body_layout, "precure_season_kanji_name", record.get("precure_season_kanji_name", ""), 13, True, 42)
        self._add_field(body_layout, "precure_season_romaji_name", record.get("precure_season_romaji_name", ""), 13, True, 42)
        self._add_field(body_layout, "ep_total", record.get("ep_total", ""), 12, False, 34)
        self._add_field(body_layout, "release_date", record.get("release_date", ""), 12, False, 34)
        self._add_field(body_layout, "carpeta_maestra", self._master_folder_name, 12, False, 34)
        self._add_field(body_layout, "theme_description", record.get("theme_description", ""), 11, False, 90)

        body_layout.addStretch(1)
        scroll.setWidget(body)
        return scroll

    def _add_field(self, parent_layout, label_text: str, value: str, 
                   font_size: int, italic: bool, height: int) -> None:
        wrapper = QtWidgets.QWidget()
        wrapper_layout = QtWidgets.QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(4)

        label = QtWidgets.QLabel(label_text)
        label.setStyleSheet("font-size: 11px;")
        wrapper_layout.addWidget(label)

        row = QtWidgets.QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        edit = QtWidgets.QTextEdit()
        edit.setReadOnly(True)
        edit.setAcceptRichText(False)
        edit.setPlainText(str(value))
        edit.setFixedHeight(height)
        edit.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
            | QtCore.Qt.TextInteractionFlag.TextSelectableByKeyboard
        )

        style = [
            f"font-size: {font_size}px;",
        ]
        if italic:
            style.append("font-style: italic;")
        edit.setStyleSheet("".join(style))

        btn_copy = QtWidgets.QPushButton("Copy")
        btn_copy.setFixedWidth(72)
        btn_copy.clicked.connect(lambda checked=False, e=edit: QtWidgets.QApplication.clipboard().setText(e.toPlainText()))

        row.addWidget(edit, 1)
        row.addWidget(btn_copy)

        wrapper_layout.addLayout(row)
        parent_layout.addWidget(wrapper)