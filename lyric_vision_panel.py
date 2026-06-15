# lyric_vision_panel.py
from __future__ import annotations

import os
import re
from pathlib import PureWindowsPath

from PyQt6 import QtCore, QtGui, QtWidgets


class LyricVisionPanel(QtWidgets.QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main = main_window

        self.source_video_path = ""
        self.indirect_path = ""
        self.row_index = 0
        self.total_rows = 0

        self._build()

    def _build(self):
        self.outer = QtWidgets.QVBoxLayout(self)
        self.outer.setContentsMargins(0, 0, 0, 0)
        self.outer.setSpacing(8)

        self.info_label = QtWidgets.QLabel("Linea actual: 1 | Columna: 1 | 0/0 | - ")
        self.outer.addWidget(self.info_label)

        self.stack = QtWidgets.QStackedLayout()
        self.outer.addLayout(self.stack)

        self.editor_page = QtWidgets.QWidget()
        editor_layout = QtWidgets.QVBoxLayout(self.editor_page)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(6)

        self.editor = QtWidgets.QPlainTextEdit()
        self.editor.setFont(QtGui.QFont("Segoe UI Emoji", 12))
        self.editor.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.NoWrap)
        self.editor.setTabChangesFocus(False)
        self.editor.cursorPositionChanged.connect(self._update_cursor_info)
        editor_layout.addWidget(self.editor)

        buttons = QtWidgets.QHBoxLayout()
        BTN_W = 60; BTN_WL = 50

        self.btn_copy_filename = QtWidgets.QPushButton("Copy Filename")
        self.btn_copy_filename.clicked.connect(self.copy_filename)
        buttons.addWidget(self.btn_copy_filename)
        
        self.btn_preview = QtWidgets.QPushButton("Review")
        self.btn_preview.clicked.connect(self.preview_current_file)
        self.btn_preview.setFixedWidth(BTN_W)
        buttons.addWidget(self.btn_preview)

        self.btn_undo = QtWidgets.QPushButton("Undo")
        self.btn_undo.clicked.connect(self.editor.undo)
        self.btn_undo.setFixedWidth(BTN_WL)
        buttons.addWidget(self.btn_undo)

        self.btn_redo = QtWidgets.QPushButton("Redo")
        self.btn_redo.clicked.connect(self.editor.redo)
        self.btn_redo.setFixedWidth(BTN_WL)
        buttons.addWidget(self.btn_redo)

        self.btn_cut = QtWidgets.QPushButton("Cut")
        self.btn_cut.clicked.connect(self.editor.cut)
        self.btn_cut.setFixedWidth(BTN_WL)
        buttons.addWidget(self.btn_cut)

        self.btn_copy = QtWidgets.QPushButton("Copy")
        self.btn_copy.clicked.connect(self.editor.copy)
        self.btn_copy.setFixedWidth(BTN_WL)
        buttons.addWidget(self.btn_copy)
        
        buttons.addStretch(1) 

        self.btn_paste = QtWidgets.QPushButton("Paste")
        self.btn_paste.clicked.connect(self.editor.paste)
        self.btn_paste.setFixedWidth(BTN_W)
        buttons.addWidget(self.btn_paste)

        self.btn_save = QtWidgets.QPushButton("Save")
        self.btn_save.clicked.connect(self.save_current_file)
        self.btn_save.setFixedWidth(BTN_W)
        buttons.addWidget(self.btn_save)
        
        self.btn_next = QtWidgets.QPushButton("Prev")
        self.btn_next.clicked.connect(self.prev_file)
        self.btn_next.setFixedWidth(BTN_W)
        buttons.addWidget(self.btn_next)

        self.btn_next = QtWidgets.QPushButton("Next")
        self.btn_next.clicked.connect(self.next_file)
        self.btn_next.setFixedWidth(BTN_W)
        buttons.addWidget(self.btn_next)

        editor_layout.addLayout(buttons)
        self.stack.addWidget(self.editor_page)

        self.warning_page = QtWidgets.QWidget()
        warning_layout = QtWidgets.QVBoxLayout(self.warning_page)
        warning_layout.setContentsMargins(0, 0, 0, 0)
        warning_layout.setSpacing(10)

        warning_row = QtWidgets.QHBoxLayout()
        self.warning_icon = QtWidgets.QLabel()
        self.warning_icon.setPixmap(
            self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_MessageBoxWarning).pixmap(32, 32)
        )
        warning_row.addWidget(self.warning_icon, 0, QtCore.Qt.AlignmentFlag.AlignTop)

        self.warning_text = QtWidgets.QLabel("")
        self.warning_text.setWordWrap(True)
        warning_row.addWidget(self.warning_text, 1)

        warning_layout.addLayout(warning_row)
        warning_layout.addStretch(1)

        self.stack.addWidget(self.warning_page)
        self.stack.setCurrentWidget(self.editor_page)

        self._set_editor_enabled(True)
        self._update_cursor_info()

    def _set_editor_enabled(self, enabled: bool):
        self.editor.setEnabled(enabled)
        self.btn_copy_filename.setEnabled(enabled)
        self.btn_undo.setEnabled(enabled)
        self.btn_redo.setEnabled(enabled)
        self.btn_cut.setEnabled(enabled)
        self.btn_copy.setEnabled(enabled)
        self.btn_paste.setEnabled(enabled)
        self.btn_save.setEnabled(enabled)
        self.btn_preview.setEnabled(enabled)

    def set_document(self, source_video_path: str, indirect_path: str, text: str, row_index: int, total_rows: int):
        self.source_video_path = source_video_path
        self.indirect_path = indirect_path
        self.row_index = row_index
        self.total_rows = total_rows

        self.stack.setCurrentWidget(self.editor_page)
        self._set_editor_enabled(True)

        self.editor.blockSignals(True)
        self.editor.setPlainText(text)
        self.editor.blockSignals(False)
        self.editor.document().setModified(False)
        self.editor.moveCursor(QtGui.QTextCursor.MoveOperation.Start)

        self._update_cursor_info()

    def set_missing_document(self, source_video_path: str, indirect_path: str, row_index: int, total_rows: int):
        self.source_video_path = source_video_path
        self.indirect_path = indirect_path
        self.row_index = row_index
        self.total_rows = total_rows

        self.warning_text.setText(
            "El archivo indirecto no existe.\n\n"
            f"Video: {source_video_path}\n"
            f"Indirecto esperado: {indirect_path}"
        )
        self.stack.setCurrentWidget(self.warning_page)
        self._set_editor_enabled(False)
        self.info_label.setText(
            f"Linea actual: - | Columna: - | {row_index}/{total_rows} | {os.path.basename(indirect_path) if indirect_path else '-'}"
        )

    def clear(self):
        self.source_video_path = ""
        self.indirect_path = ""
        self.row_index = 0
        self.total_rows = 0
        self.editor.clear()
        self.stack.setCurrentWidget(self.editor_page)
        self._set_editor_enabled(True)
        self._update_cursor_info()

    def _update_cursor_info(self):
        cursor = self.editor.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.positionInBlock() + 1
        name = os.path.basename(self.indirect_path) if self.indirect_path else "-"
        self.info_label.setText(
            f"Linea actual: {line} | Columna: {col} | {self.row_index}/{self.total_rows} | {name}"
        )

    def copy_filename(self):
        path = self.indirect_path or self.source_video_path
        if not path:
            return
        stem = os.path.splitext(os.path.basename(path))[0]
        QtWidgets.QApplication.clipboard().setText(stem)

    def save_current_file(self):
        if not self.indirect_path or self.stack.currentWidget() is self.warning_page:
            return False

        folder = os.path.dirname(self.indirect_path)
        if folder:
            os.makedirs(folder, exist_ok=True)

        with open(self.indirect_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(self.editor.toPlainText())

        self.editor.document().setModified(False)
        return True

    def preview_current_file(self):
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("Preview")
        dlg.resize(780, 540)

        layout = QtWidgets.QVBoxLayout(dlg)

        preview = QtWidgets.QPlainTextEdit()
        preview.setReadOnly(True)
        preview.setPlainText(self.editor.toPlainText())
        layout.addWidget(preview)

        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Close)
        btns.rejected.connect(dlg.reject)
        btns.accepted.connect(dlg.accept)
        layout.addWidget(btns)

        dlg.exec()

    def next_file(self):
        if not self._ask_pending_changes("Antes de pasar al siguiente archivo se debe resolver el estado del archivo actual."):
            return
        self.main.next_lyric_entry()
        
    def prev_file(self):
        if not self._ask_pending_changes("Antes de pasar al anterior archivo se debe resolver el estado del archivo actual."):
            return
        self.main.prev_lyric_entry()

    @staticmethod
    def build_indirect_path(video_path: str) -> str:
        p = PureWindowsPath(video_path)
        parts = list(p.parts)

        replaced = False
        for i, part in enumerate(parts):
            new_part = re.sub(r"vocals", "lyrics", part, flags=re.IGNORECASE)
            if new_part != part:
                parts[i] = new_part
                replaced = True
                break

        new_path = PureWindowsPath(*parts)
        new_path = new_path.with_suffix(".md")

        if not replaced:
            return str(new_path)

        return str(new_path)

    @staticmethod
    def read_utf8(path: str) -> str:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _reload_current_document(self):
        if not self.indirect_path or self.stack.currentWidget() is self.warning_page:
            return

        if not os.path.exists(self.indirect_path):
            self.set_missing_document(
                self.source_video_path,
                self.indirect_path,
                self.row_index,
                self.total_rows,
            )
            return

        text = self.read_utf8(self.indirect_path)
        self.editor.blockSignals(True)
        self.editor.setPlainText(text)
        self.editor.blockSignals(False)
        self.editor.document().setModified(False)
        self.editor.moveCursor(QtGui.QTextCursor.MoveOperation.Start)
        self._update_cursor_info()
        
    def _ask_pending_changes(self, action_text: str) -> bool:
        if self.stack.currentWidget() is self.warning_page:
            return True

        if not self.editor.document().isModified():
            return True

        box = QtWidgets.QMessageBox(self)
        box.setIcon(QtWidgets.QMessageBox.Icon.Warning)
        box.setWindowTitle("Cambios pendientes")
        box.setText("Hay cambios sin guardar en el archivo actual.")
        box.setInformativeText(action_text)

        btn_save = box.addButton("Guardar", QtWidgets.QMessageBox.ButtonRole.AcceptRole)
        btn_discard = box.addButton("Descartar", QtWidgets.QMessageBox.ButtonRole.DestructiveRole)
        btn_cancel = box.addButton("Cancelar", QtWidgets.QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(btn_cancel)
        box.exec()

        clicked = box.clickedButton()
        if clicked == btn_save:
            return self.save_current_file()
        if clicked == btn_discard:
            self._reload_current_document()
            return True
        return False