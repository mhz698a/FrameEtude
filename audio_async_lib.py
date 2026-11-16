from __future__ import annotations

from dataclasses import dataclass

from PyQt6 import QtCore


@dataclass(frozen=True)
class AudioFetchJob:
    path: str


def probe_audio_text(path: str) -> str:
    """Return Yes/No using MediaInfo, or N/A when probing is unavailable."""
    try:
        from pymediainfo import MediaInfo
    except Exception:
        return "N/A"

    try:
        media = MediaInfo.parse(path)
        tracks = getattr(media, "tracks", ()) or ()
        has_audio = any(
            str(getattr(track, "track_type", "") or "").casefold() == "audio"
            for track in tracks
        )
        return "Yes" if has_audio else "No"
    except Exception:
        return "N/A"


class AudioFetchThread(QtCore.QThread):
    audio_ready = QtCore.pyqtSignal(str, str)

    def __init__(self, jobs: list[AudioFetchJob], parent=None):
        super().__init__(parent)
        self._jobs = jobs

    def run(self):
        for job in self._jobs:
            if self.isInterruptionRequested():
                break
            self.audio_ready.emit(job.path, probe_audio_text(job.path))
