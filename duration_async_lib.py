from __future__ import annotations

from dataclasses import dataclass
import os
import shutil
import subprocess

from PyQt6 import QtCore


@dataclass(frozen=True)
class DurationFetchJob:
    path: str


def _format_duration_text(seconds: float | None, allow_ms: bool = False) -> str:
    if seconds is None or seconds < 0:
        return ""

    total_ms = int(round(seconds * 1000))
    hours, rem = divmod(total_ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1000)

    if ms and allow_ms:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{ms:03d}"
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _probe_with_mutagen(path: str) -> float | None:
    try:
        from mutagen import File as MutagenFile
    except Exception:
        return None

    try:
        media = MutagenFile(path)
    except Exception:
        return None

    if media is None:
        return None

    length = getattr(getattr(media, "info", None), "length", None)
    try:
        return float(length) if length is not None else None
    except Exception:
        return None


def _probe_with_ffprobe(path: str) -> float | None:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None

    cmd = [
        ffprobe,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        path,
    ]

    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception:
        return None

    raw = (completed.stdout or completed.stderr or "").strip().splitlines()
    if not raw:
        return None

    try:
        return float(raw[0].strip().replace(",", "."))
    except Exception:
        return None


def probe_duration_text(path: str) -> str:
    if not path or not os.path.exists(path):
        return ""

    seconds = _probe_with_mutagen(path)
    if seconds is None:
        seconds = _probe_with_ffprobe(path)

    return _format_duration_text(seconds)


class DurationFetchThread(QtCore.QThread):
    duration_ready = QtCore.pyqtSignal(str, str)

    def __init__(self, jobs: list[DurationFetchJob], parent=None):
        super().__init__(parent)
        self._jobs = jobs

    def run(self):
        for job in self._jobs:
            if self.isInterruptionRequested():
                break
            self.duration_ready.emit(job.path, probe_duration_text(job.path))