from __future__ import annotations

import os


_FASTSTART_EXTS = {".mp4", ".m4v", ".mov", ".qt"}


def is_moov_at_front(path: str, sample_size: int = 4 * 1024 * 1024) -> bool:
    """
    Best-effort detector.
    True  -> moov parece estar al frente (faststart).
    False -> moov probablemente está al final.
    """
    if not path or not os.path.exists(path):
        return True

    if os.path.splitext(path)[1].lower() not in _FASTSTART_EXTS:
        return True

    try:
        with open(path, "rb") as f:
            head = f.read(sample_size)

        moov_pos = head.find(b"moov")
        mdat_pos = head.find(b"mdat")

        if moov_pos == -1:
            return False

        if mdat_pos == -1:
            return True

        return moov_pos < mdat_pos
    except Exception:
        return True