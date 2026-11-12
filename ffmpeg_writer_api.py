from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from typing import Any

try:
    from mutagen.mp4 import MP4
except Exception:
    MP4 = None

try:
    from wctime import setctime_blocking
except Exception:
    setctime_blocking = None


COMMENT_KEYS = [
    "real_ctime",
    "real_mtime",
    "after_of_episode",
    "overwrite_1_times",
    "overwrite_2_times",
    "overwrite_3_times",
    "free_listener_times",
]

COLUMN_TO_METADATA = {
    "title": "title",
    "album": "album",
    "artist": "artist",
    "release_date": "date",
    "genre": "genre",
    "track": "track",
    "disk": "disc",
}


class ForeignCommentError(RuntimeError):
    def __init__(self, existing_text: str):
        super().__init__(existing_text)
        self.existing_text = existing_text


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
                for part in text.replace("\r", "\n").split("\n")
                for part in part.split("/")
                if part.strip()
            ]

    items = items[:3]
    while len(items) < 3:
        items.append("")
    return items


def _normalize_comment_value(key: str, value: Any) -> Any:
    if key == "free_listener_times":
        return _normalize_free_listener_value(value)
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


def probe_mp4_duration_seconds(path: str) -> float | None:
    if MP4 is None or not os.path.exists(path):
        return None
    try:
        mp4 = MP4(path)
        return float(getattr(mp4.info, "length", 0.0) or 0.0)
    except Exception:
        return None


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def _parse_pair_value(value: Any) -> tuple[int, int] | None:
    text = _safe_text(value)
    if not text:
        return None

    if "/" in text:
        left, right = text.split("/", 1)
        left = left.strip()
        right = right.strip()
        if left.isdigit() and right.isdigit():
            return int(left), int(right)
        return None

    if text.isdigit():
        return int(text), 0

    return None


def _build_metadata_payload(
    path: str,
    updates: dict[str, Any],
    *,
    replace_foreign_comments: bool,
) -> dict[str, str]:
    comment_updates = {key: value for key, value in updates.items() if key in COMMENT_KEYS}
    normal_updates = {
        key: value for key, value in updates.items()
        if key not in COMMENT_KEYS and key != "filename"
    }

    metadata: dict[str, str] = {}

    if comment_updates:
        existing_raw = _read_comment_raw(path)
        status, raw_text = comment_status_from_text(existing_raw)
        if status == "foreign" and not replace_foreign_comments:
            raise ForeignCommentError(raw_text)

        if status == "ours":
            try:
                payload = json.loads(raw_text)
            except Exception:
                payload = _empty_comment_payload()
        else:
            payload = _empty_comment_payload()

        for key, value in comment_updates.items():
            payload[key] = _normalize_comment_value(key, value)

        metadata["comment"] = json.dumps(payload, ensure_ascii=False)

    for key, value in normal_updates.items():
        meta_key = COLUMN_TO_METADATA.get(key)
        if meta_key is None:
            continue

        if key in {"track", "disk"}:
            pair = _parse_pair_value(value)
            if pair is None:
                metadata[meta_key] = ""
            else:
                metadata[meta_key] = f"{pair[0]}/{pair[1]}" if pair[1] else str(pair[0])
        else:
            metadata[meta_key] = _safe_text(value)

    return metadata


def save_mp4_updates_ffmpeg(
    path: str,
    updates: dict[str, Any],
    *,
    replace_foreign_comments: bool = False,
) -> None:
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    if not ffmpeg_available():
        raise RuntimeError("ffmpeg no está disponible en PATH.")
    if MP4 is None:
        raise RuntimeError("mutagen.mp4 no está disponible.")

    st = os.stat(path)
    old_atime = st.st_atime
    old_mtime = st.st_mtime
    old_ctime = st.st_ctime

    metadata = _build_metadata_payload(
        path,
        updates,
        replace_foreign_comments=replace_foreign_comments,
    )

    output_dir = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp_path = tempfile.mkstemp(prefix="ffmpeg_meta_", suffix=".mp4", dir=output_dir)
    os.close(fd)

    try:
        cmd = [
            shutil.which("ffmpeg") or "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-i",
            path,
            "-map",
            "0",
            "-map_chapters",
            "0",
            "-map_metadata",
            "0",
            "-ignore_unknown",
            "-c",
            "copy",
        ]

        for key, value in metadata.items():
            cmd.extend(["-metadata", f"{key}={value}"])

        cmd.append(tmp_path)

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        if proc.returncode != 0:
            stderr = (proc.stderr or "").strip()
            stdout = (proc.stdout or "").strip()
            details = stderr or stdout or f"ffmpeg devolvió código {proc.returncode}"
            raise RuntimeError(details)

        os.replace(tmp_path, path)

        try:
            os.utime(path, (old_atime, old_mtime))
        except Exception:
            pass

        if setctime_blocking is not None:
            try:
                setctime_blocking(path, old_ctime)
            except Exception:
                pass
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass