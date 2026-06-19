from __future__ import annotations

import json
import os
import re
from typing import Any
from PyQt6 import QtWidgets

try:
    from mutagen.mp4 import MP4
except Exception:
    MP4 = None

from wctime import setctime_blocking
from isodatetimerng import standardize_time_range
from ffmpeg_writer_api import ffmpeg_available, probe_mp4_duration_seconds, save_mp4_updates_ffmpeg


COMMENT_KEYS = [
    "real_ctime",
    "real_mtime",
    "after_of_episode",
    "overwrite_1_times",
    "overwrite_2_times",
    "overwrite_3_times",
    "free_listener_times",
]

COMMENT_PLACEHOLDER = "((tiene algo))"

COLUMN_TO_ATOM = {
    "title": "©nam",
    "album": "©alb",
    "artist": "©ART",
    "release_date": "©day",
    "genre": "©gen",
    "track": "trkn",
    "disk": "disk",
}


class ForeignCommentError(RuntimeError):
    def __init__(self, existing_text: str):
        super().__init__(existing_text)
        self.existing_text = existing_text


class ForeignCommentDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, existing_text: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Comentarios existentes")
        self.setModal(True)
        self.choice = "cancel"

        layout = QtWidgets.QVBoxLayout(self)

        label = QtWidgets.QLabel(
            "En la etiqueta comentarios hay algo que no es de la estructura.\n"
            "Si desea conservarlo, cópielo y guárdelo en un documento antes de seguir.\n"
            "¿Desea reemplazar esta información con la nueva?"
        )
        label.setWordWrap(True)
        layout.addWidget(label)

        text_edit = QtWidgets.QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(existing_text)
        text_edit.setMinimumSize(620, 240)
        layout.addWidget(text_edit)

        buttons_row = QtWidgets.QHBoxLayout()
        buttons_row.addStretch(1)

        yes_button = QtWidgets.QPushButton("Yes")
        yes_all_button = QtWidgets.QPushButton("Yes to all")
        no_all_button = QtWidgets.QPushButton("No to All")

        yes_button.clicked.connect(self._accept_yes)
        yes_all_button.clicked.connect(self._accept_yes_to_all)
        no_all_button.clicked.connect(self._reject_no_to_all)

        buttons_row.addWidget(yes_button)
        buttons_row.addWidget(yes_all_button)
        buttons_row.addWidget(no_all_button)
        layout.addLayout(buttons_row)

    def _accept_yes(self):
        self.choice = "yes"
        self.accept()

    def _accept_yes_to_all(self):
        self.choice = "yes_all"
        self.accept()

    def _reject_no_to_all(self):
        self.choice = "no_all"
        self.reject()

class ForeignCommentSummaryDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, aggregated_text: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Comentarios existentes recopilados")
        self.setModal(True)

        layout = QtWidgets.QVBoxLayout(self)

        label = QtWidgets.QLabel(
            "Si desea rescatar esta informacion puede copiarla y guardarla"
        )
        label.setWordWrap(True)
        layout.addWidget(label)

        text_edit = QtWidgets.QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(aggregated_text)
        text_edit.setMinimumSize(720, 320)
        layout.addWidget(text_edit)

        buttons_row = QtWidgets.QHBoxLayout()
        buttons_row.addStretch(1)

        proceed_button = QtWidgets.QPushButton("Proceder")
        cancel_button = QtWidgets.QPushButton("Cancelar")
        proceed_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)

        buttons_row.addWidget(proceed_button)
        buttons_row.addWidget(cancel_button)
        layout.addLayout(buttons_row)

def _safe_text(value: Any) -> str:
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
        return _safe_text(value[0])
    return str(value).strip()


def _empty_comment_payload() -> dict[str, Any]:
    return {
        "real_ctime": "",
        "real_mtime": "",
        "after_of_episode": "",
        "overwrite_1_times": "",
        "overwrite_2_times": "",
        "overwrite_3_times": "",
        "free_listener_times": ["", "", ""],
    }


def _is_our_comment_data(data: Any) -> bool:
    return isinstance(data, dict) and all(key in data for key in COMMENT_KEYS)


def _normalize_free_listener_value(value: Any) -> list[str]:
    if isinstance(value, (list, tuple)):
        items = [_safe_text(v) for v in value]
    else:
        text = _safe_text(value)
        if not text:
            items = []
        else:
            items = [
                part.strip()
                for part in re.split(r"\s*/\s*|\t+|\r?\n+", text)
                if part.strip()
            ]
    items = items[:3]
    while len(items) < 3:
        items.append("")
    return items


def _normalize_comment_value(key: str, value: Any) -> Any:
    if key == "free_listener_times":
        return _normalize_free_listener_value(value)

    if key in {"overwrite_1_times", "overwrite_2_times", "overwrite_3_times"}:
        text = _safe_text(value)
        if text:
            return standardize_time_range(text)
        return ""

    return _safe_text(value)


def comment_status_from_text(text: Any) -> tuple[str, str]:
    raw_text = _safe_text(text)
    if not raw_text:
        return "empty", ""

    try:
        data = json.loads(raw_text)
    except Exception:
        return "foreign", raw_text

    if _is_our_comment_data(data):
        return "ours", raw_text

    return "foreign", raw_text


def _read_comment_raw(path: str) -> str:
    if MP4 is None or not os.path.exists(path):
        return ""

    try:
        mp4 = MP4(path)
        tags = mp4.tags or {}
        return _safe_text(tags.get("©cmt", ""))
    except Exception:
        return ""


def comment_status_from_path(path: str) -> tuple[str, str]:
    return comment_status_from_text(_read_comment_raw(path))


def comment_display_value(comment_raw: Any, key: str) -> str:
    status, raw_text = comment_status_from_text(comment_raw)
    if status == "foreign":
        return COMMENT_PLACEHOLDER
    if status == "empty":
        return ""

    try:
        data = json.loads(raw_text)
    except Exception:
        return ""

    if not _is_our_comment_data(data):
        return COMMENT_PLACEHOLDER

    value = data.get(key, "")
    if key == "free_listener_times":
        if isinstance(value, list):
            items = [_safe_text(v) for v in value if _safe_text(v)]
            return " / ".join(items)
        return ""
    return _safe_text(value)


def _parse_pair_value(value: Any) -> tuple[int, int] | None:
    text = _safe_text(value)
    if not text:
        return None

    match = re.fullmatch(r"(\d+)(?:\s*/\s*(\d+))?", text)
    if not match:
        return None

    first = int(match.group(1))
    second = int(match.group(2)) if match.group(2) is not None else 0
    return first, second


def _delete_tag(tags: Any, atom: str) -> None:
    try:
        del tags[atom]
    except Exception:
        pass


def _set_text_tag(tags: Any, atom: str, value: Any) -> None:
    text = _safe_text(value)
    if text:
        tags[atom] = [text]
    else:
        _delete_tag(tags, atom)


def _set_pair_tag(tags: Any, atom: str, value: Any) -> None:
    pair = _parse_pair_value(value)
    if pair is None:
        _delete_tag(tags, atom)
    else:
        tags[atom] = [pair]


def save_mp4_updates(
    path: str,
    updates: dict[str, Any],
    *,
    replace_foreign_comments: bool = False,) -> str:
    
    if MP4 is None:
        raise RuntimeError("mutagen.mp4 no está disponible.")

    if not os.path.exists(path):
        raise FileNotFoundError(path)

    st = os.stat(path)
    old_atime = st.st_atime
    old_mtime = st.st_mtime
    old_ctime = st.st_ctime

    mp4 = MP4(path)
    if mp4.tags is None:
        mp4.add_tags()

    tags = mp4.tags

    filename_value = _safe_text(updates.get("filename", ""))
    rename_base = os.path.splitext(filename_value)[0] if filename_value else ""

    comment_updates = {
        key: value for key, value in updates.items() if key in COMMENT_KEYS
    }
    normal_updates = {
        key: value
        for key, value in updates.items()
        if key not in COMMENT_KEYS and key != "filename"
    }

    if comment_updates:
        existing_raw = _safe_text(tags.get("©cmt", ""))
        status, raw_text = comment_status_from_text(existing_raw)
        if status == "foreign" and not replace_foreign_comments:
            raise ForeignCommentError(raw_text)

        if status == "ours":
            payload = json.loads(raw_text)
        else:
            payload = _empty_comment_payload()

        for key, value in comment_updates.items():
            payload[key] = _normalize_comment_value(key, value)

        tags["©cmt"] = [json.dumps(payload, ensure_ascii=False)]

    for key, value in normal_updates.items():
        atom = COLUMN_TO_ATOM.get(key)
        if atom is None:
            continue

        if key in {"track", "disk"}:
            _set_pair_tag(tags, atom, value)
        else:
            _set_text_tag(tags, atom, value)

    mp4.save(path)
    
    if rename_base:
        folder = os.path.dirname(path)
        ext = os.path.splitext(path)[1]
        new_path = os.path.join(folder, f"{rename_base}{ext}")

        if os.path.normcase(new_path) != os.path.normcase(path):
            if os.path.exists(new_path):
                raise FileExistsError(new_path)
            os.rename(path, new_path)
            path = new_path

    try:
        os.utime(path, (old_atime, old_mtime))
    except Exception:
        pass

    if setctime_blocking is not None:
        try:
            setctime_blocking(path, old_ctime)
        except Exception:
            pass
    
    return path