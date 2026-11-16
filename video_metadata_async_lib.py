from __future__ import annotations

import os

from PyQt6 import QtCore


def empty_video_metadata(pending: bool = False) -> dict[str, str]:
    value = "..." if pending else "N/A"
    return {
        "resolution": value,
        "bit_rate": value,
        "audio": value,
        "weight": value,
    }


def _format_file_size(size: int) -> str:
    value = float(size)
    units = ("B", "KB", "MB", "GB", "TB")
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.2f} {unit}"
        value /= 1024
    return "N/A"


def _positive_int(value) -> int | None:
    try:
        number = int(float(value))
    except (TypeError, ValueError, OverflowError):
        return None
    return number if number > 0 else None


def _format_bit_rate(value) -> str:
    try:
        bits_per_second = float(value)
    except (TypeError, ValueError, OverflowError):
        return "N/A"

    if bits_per_second <= 0:
        return "N/A"
    if bits_per_second >= 1_000_000:
        return f"{bits_per_second / 1_000_000:.2f} Mbps"
    if bits_per_second >= 1_000:
        return f"{bits_per_second / 1_000:.0f} kbps"
    return f"{bits_per_second:.0f} bps"


def probe_video_metadata(path: str) -> dict[str, str]:
    metadata = empty_video_metadata()

    try:
        metadata["weight"] = _format_file_size(os.path.getsize(path))
    except (OSError, TypeError, ValueError):
        pass

    try:
        from pymediainfo import MediaInfo

        media = MediaInfo.parse(path)
        tracks = getattr(media, "tracks", ()) or ()
    except Exception:
        return metadata

    video_track = next(
        (
            track for track in tracks
            if str(getattr(track, "track_type", "") or "").casefold() == "video"
        ),
        None,
    )
    general_track = next(
        (
            track for track in tracks
            if str(getattr(track, "track_type", "") or "").casefold() == "general"
        ),
        None,
    )
    has_audio = any(
        str(getattr(track, "track_type", "") or "").casefold() == "audio"
        for track in tracks
    )

    if video_track is not None:
        width = _positive_int(getattr(video_track, "width", None))
        height = _positive_int(getattr(video_track, "height", None))
        if width and height:
            metadata["resolution"] = f"{width} × {height}"

    bit_rate = getattr(video_track, "bit_rate", None) if video_track else None
    if not bit_rate and general_track is not None:
        bit_rate = getattr(general_track, "bit_rate", None)
    metadata["bit_rate"] = _format_bit_rate(bit_rate)
    metadata["audio"] = "Yes" if has_audio else "No"

    return metadata


class VideoMetadataFetchThread(QtCore.QThread):
    metadata_ready = QtCore.pyqtSignal(str, object)

    def __init__(self, path: str, parent=None):
        super().__init__(parent)
        self.path = os.path.abspath(path)

    def run(self):
        if self.isInterruptionRequested():
            return

        metadata = probe_video_metadata(self.path)
        if not self.isInterruptionRequested():
            self.metadata_ready.emit(self.path, metadata)
