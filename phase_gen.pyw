# -*- coding: utf-8 -*-

"""
Genera un Markdown con:
- # The Year {year}
- ## Struct
- ## Master Folders

Búsqueda:
E:\\_Internal\\{year}\\{prefix}. ___[master]\\...

Donde:
prefix = f"{int(year) - 2003:02d}. "
"""

from __future__ import annotations

import os
import sys
import traceback
import ctypes
from pathlib import Path
from collections import defaultdict

from functools import cmp_to_key

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6 import QtGui

import config

_strcmp_logical = ctypes.windll.shlwapi.StrCmpLogicalW


BASE_ROOT = Path(r"E:\_Internal")
root = os.path.join("E:\\", "_Internal")

STRUCT_BLOCK = '''```toml
[title] = ""
[album] = ""
[artist] = ""
[track] = ""
[date] = ""
[disk] = ""
[genre] = ""
[comments] = """
{
    "real_ctime": "", 
    "real_mtime": "", 
    "after_of_episode": "", 
    "overwrite_1_times": "", 
    "overwrite_2_times": "", 
    "overwrite_3_times": "", 
    "free_listener_times": ["", "", ""]
}
"""
```'''

def windows_sort_key(path: Path):
    return path

def windows_compare(a: Path, b: Path):
    return _strcmp_logical(a.name, b.name)

def ask_year() -> int:
    raw = input("Year: ").strip()
    if not raw.isdigit():
        raise ValueError(f"Invalid year: {raw!r}")
    year = int(raw)
    if year < 1900 or year > 3000:
        raise ValueError(f"Year out of range: {year}")
    return year


def find_master_folder(year: int) -> Path:
    prefix = f"{year - 2003:02d}. "
    year_dir = BASE_ROOT / str(year)

    if not year_dir.exists():
        raise FileNotFoundError(f"Year folder does not exist: {year_dir}")

    candidates = [
        p for p in year_dir.iterdir()
        if p.is_dir() and "___[" in p.name and p.name.startswith(prefix)
    ]

    if not candidates:
        raise FileNotFoundError(
            f"No master folder found in {year_dir} with prefix {prefix!r} and '___['"
        )

    if len(candidates) > 1:
        # Si por algún motivo hubiera más de uno, toma el primero ordenado.
        candidates.sort(key=cmp_to_key(windows_compare))

    return candidates[0]


def is_valid_folder(folder: Path) -> bool:
    name = folder.name.lower()

    # Omitir carpetas "sh_"
    if "sh_" in name:
        return False

    # Las carpetas que contienen "_eps" solo son válidas
    # si terminan en ".on".
    if "_eps" in name and not name.endswith(".on"):
        return False
    
    if "sp" in name and not name.endswith(".on"):
        return False

    return True

def collect_folders_with_mp4(master_dir: Path) -> dict[Path, list[Path]]:
    groups: dict[Path, list[Path]] = defaultdict(list)

    for file_path in master_dir.rglob("*"):
        if not file_path.is_file():
            continue

        if file_path.suffix.lower() != ".mp4":
            continue

        folder = file_path.parent

        if not is_valid_folder(folder):
            continue

        groups[folder].append(file_path)

    for folder in groups:
        groups[folder].sort(key=lambda p: p.name.lower())

    return dict(
        sorted(
            groups.items(),
            key=lambda item: str(item[0].relative_to(master_dir)).lower()
        )
    )

def render_markdown(year: int, master_dir: Path, groups: dict[Path, list[Path]]) -> str:
    lines: list[str] = []

    lines.append(f"# The Year {year}")
    lines.append("")
    lines.append("## Struct")
    lines.append("")
    lines.append(STRUCT_BLOCK)
    lines.append("")
    lines.append("## Master Folders")
    lines.append("")

    if not groups:
        msg = "_No mp4 files found._"
        lines.append(msg)
        lines.append("")
        print(msg)
        return "\n".join(lines)

    # Agrupar por carpeta relativa para generar secciones.
    for folder_index, (folder_path, files) in enumerate(groups.items(), start=1):
        rel_folder = folder_path.relative_to(master_dir)
        folder_label = str(rel_folder) if str(rel_folder) != "." else master_dir.name

        lines.append(f"### {folder_label}")
        lines.append("")

        if "vocals" in folder_path.name.lower():
            total = len(files)

            base = total // 4
            extra = total % 4

            start = 0
            for section in range(4):
                size = base + (1 if section < extra else 0)
                end = start + size

                lines.append(f"#### Sección {section + 1}")
                lines.append("")

                for file_path in files[start:end]:
                    lines.append(f"* {file_path.name}")
                    lines.append("    - ")
                    lines.append("")

                start = end
        else:
            for file_path in files:
                lines.append(f"* {file_path.name}")
                lines.append("    - ")
                lines.append("")

    return "\n".join(lines) + "\n---\n"


def main_all() -> int:
    try:
        # year = ask_year()
        
        for year in range(2004, 2026+1):
            master_dir = find_master_folder(year)
            groups = collect_folders_with_mp4(master_dir)
            md = render_markdown(year, master_dir, groups)

            year_path = os.path.join(root, str(year))
            prefix = f"{int(year) - 2003:02d}"
            master = [f for f in os.listdir(year_path) if f.startswith(f"{prefix}. ___[")]
            wroad_folder = Path(master[0]) / f"{prefix}. wroad"

            # output_path = Path.cwd() / f"The_Year_{year}.md"
            output_path = BASE_ROOT / str(year) / wroad_folder / f"The_Year_{year}.md"
            output_path.write_text(md, encoding="utf-8")

            print(str(output_path))
            
        return 0

    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

def main() -> int:
    app = QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon(config.ICON_PATH))

    try:
        # Requiere argumento
        if len(sys.argv) != 2:
            QMessageBox.warning(
                None,
                "Generate Year MD",
                "Debe especificar el año como argumento.\n\n"
                "Ejemplo:\n"
                "generate_year_md.pyw 2026"
            )
            return 1

        year = int(sys.argv[1])

        master_dir = find_master_folder(year)
        groups = collect_folders_with_mp4(master_dir)
        md = render_markdown(year, master_dir, groups)

        year_path = BASE_ROOT / str(year)
        prefix = f"{year - 2003:02d}"

        master = next(
            f for f in os.listdir(year_path)
            if f.startswith(f"{prefix}. ___[")
        )

        wroad_folder = year_path / master / f"{prefix}. wroad"
        wroad_folder.mkdir(parents=True, exist_ok=True)

        output_path = wroad_folder / f"The_Year_{year}.md"

        # Si existe preguntar si desea conservarlo como antiguo.
        if output_path.exists():
            answer = QMessageBox.question(
                None,
                "Archivo existente",
                (
                    f"Ya existe:\n\n"
                    f"{output_path.name}\n\n"
                    "¿Desea marcarlo como antiguo y generar uno nuevo?"
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )

            if answer == QMessageBox.StandardButton.No:
                return 0

            index = 1
            while True:
                old_path = output_path.with_name(
                    f"{output_path.stem}_old_{index}{output_path.suffix}"
                )

                if not old_path.exists():
                    output_path.rename(old_path)
                    break

                index += 1

        output_path.write_text(md, encoding="utf-8")

        QMessageBox.information(
            None,
            "Generate Year MD",
            "Operación completada correctamente en 'wroad'."
        )

        return 0

    except Exception:
        tb = traceback.format_exc()

        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("Error")
        msg.setText("Ocurrió un error durante la operación.")
        msg.setInformativeText("Se produjo una excepción inesperada.")
        msg.setDetailedText(tb)
        msg.exec()

        return 1

if __name__ == "__main__":
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(config.ID_APP_PHASE_GEN)
    sys.exit(main())