from __future__ import annotations

import os


def is_moov_at_front(path: str) -> bool:
    try:
        filesize = os.path.getsize(path)
        with open(path, "rb") as f:
            offset = 0

            while offset + 8 <= filesize:
                header = f.read(8)
                if len(header) < 8:
                    break

                atom_size = int.from_bytes(header[:4], "big")
                atom_type = header[4:8]

                if atom_type == b"moov":
                    return True

                if atom_type == b"mdat":
                    return False

                if atom_size == 1:
                    ext = f.read(8)
                    if len(ext) < 8:
                        break
                    atom_size = int.from_bytes(ext, "big")
                    if atom_size < 16:
                        break
                    f.seek(atom_size - 16, os.SEEK_CUR)
                    offset += atom_size
                    continue

                if atom_size < 8:
                    break

                f.seek(atom_size - 8, os.SEEK_CUR)
                offset += atom_size

        return False
    except Exception:
        return False