from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from PyQt6 import QtCore
from metadata_edit_lib import save_mp4_updates


@dataclass
class MetadataSaveJob:
    row: int
    path: str
    updates: dict[str, Any]
    replace_foreign_comments: bool = False


class MetadataSaveThread(QtCore.QThread):
    progress = QtCore.pyqtSignal(int, int, str)
    row_saved = QtCore.pyqtSignal(int, str, bool)
    finished_batch = QtCore.pyqtSignal(list, int, int)

    def __init__(self, jobs: list[MetadataSaveJob], parent=None):
        super().__init__(parent)
        self._jobs = jobs

    def run(self):
        saved_rows: list[int] = []
        ok_count = 0
        fail_count = 0
        total = len(self._jobs)

        for index, job in enumerate(self._jobs, start=1):
            if self.isInterruptionRequested():
                break
            
            saved_path = job.path
            try:
                saved_path = save_mp4_updates(
                    job.path,
                    job.updates,
                    replace_foreign_comments=job.replace_foreign_comments,
                )
                saved_rows.append(job.row)
                ok_count += 1
                self.row_saved.emit(job.row, saved_path, True)
            except Exception:
                fail_count += 1
                self.row_saved.emit(job.row, job.path, False)

            self.progress.emit(index, total, saved_path)

        self.finished_batch.emit(saved_rows, ok_count, fail_count)