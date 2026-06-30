import os
import tomllib
from pathlib import Path

# ---- Config ----
APPNAME = "FrameEtude"
CONFIG_DIR = Path(os.getenv("APPDATA", Path.home())) / APPNAME
CONFIG_PATH = CONFIG_DIR / "config.toml"

# Default values as module-level variables
DEFAULT_THUMB_WIDTH = 700
THUMB_ASPECT = 9/16
MIN_THUMB_WIDTH = 120
NUM_THUMBS = 5
THUMB_SPACING = 8
CONTROL_WIDTH_ESTIMATE = 240
CACHE_SIZE = 15

OCR_SCALE = 2
OCR_USE_CLAHE = True
OCR_CLAHE_CLIP = 2.0
OCR_DENOISE_KSIZE = 3
OCR_DILATE_ITER = 1
OCR_INVERT = True
OCR_BINARIZE = True
OCR_PSM = 6
OCR_LANG = 'spa'

BASE_INTERNAL_ROOT = r"E:\_Internal"
VIDEO_EXTS = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv'}
APP_DIR = Path(__file__).resolve().parent.as_posix()
ICON_PATH = f"{APP_DIR}/assets/frameetude.ico"
ICON_PATH_LIRYCS = f"{APP_DIR}/assets/lyricsbook.ico"
ID_APP = 'etude_video.FrameEtude.VideoFramesInspector.v2'
ID_APP_LIRYCS = 'etude_video.LyricManagment.LyricsBook.v2'

RENAME_DIALOG_EXE = "pythonw"
RENAME_DIALOG_SCRIPT = r"C:\Users\miche\OneDrive\foobar2000\profile\ActivityBar\rename_dialog.py"

OVERWRITE_0 = (0, "2022-06-13", "Examen de admision a la sobrescritura vigilado por SRPF CometNova, para aspirantes al colegio de sobrescritores y estudios a fines, en el examen se trata 1999-2003. El examen de admision concluyo el 31 de diciembre del 2022.")
OVERWRITE_1 = (1, "2023-01-01", "Primera vez que se hace sobrescritura a cargo de la TSPF & ERPF. La mejora es instruida por las fundaciones administrativas Nova, tratando los rangos 2004-2018 para 2023, 2019-2024 para 2024. Se alcanzo el ultimo episodio más reciente el 2024-05-13.")
OVERWRITE_2 = (2, "2024-08-31", "Segunda vez que se hace sobrescritura pero esta vez haciendo redaccion y referenicas y percepcion sentimental. Se permite el control individual para analisis de episodios y profundizacion de eventos entre los años 2004-2025 en los años 2024-2025. Se alcanzo el ultimo episodio más reciente el 31 de diciembre del 2025.")
OVERWRITE_3 = (3, "2030-01-01", "Tercera vez que se hace sobrescritura, tiene como plan iniciar la sobrescritura en los años del 2030s.")

def load_config():
    if not CONFIG_PATH.exists():
        return

    try:
        with open(CONFIG_PATH, "rb") as f:
            config_data = tomllib.load(f)

        # Update global module variables
        g = globals()

        for key, value in config_data.items():
            if key == "OVERWRITE_HISTORY":
                history = value
                if len(history) > 0: g['OVERWRITE_0'] = tuple(history[0])
                if len(history) > 1: g['OVERWRITE_1'] = tuple(history[1])
                if len(history) > 2: g['OVERWRITE_2'] = tuple(history[2])
                if len(history) > 3: g['OVERWRITE_3'] = tuple(history[3])
            elif key in g:
                g[key] = value

    except Exception as e:
        print(f"Error loading config: {e}")

def save_config(data):
    lines = []
    for key, value in data.items():
        if key == "OVERWRITE_HISTORY":
            lines.append(f'{key} = [')
            for item in value:
                info_escaped = str(item[2]).replace('\\', '\\\\').replace('"', '\\"')
                lines.append(f'    [{item[0]}, "{item[1]}", "{info_escaped}"],')
            lines.append(']')
        elif isinstance(value, str):
            val_escaped = value.replace('\\', '\\\\').replace('"', '\\"')
            lines.append(f'{key} = "{val_escaped}"')
        elif isinstance(value, bool):
            lines.append(f'{key} = {str(value).lower()}')
        elif isinstance(value, (int, float)):
            lines.append(f'{key} = {value}')

    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    except Exception as e:
        print(f"Error saving config: {e}")

    # Reload into module variables
    load_config()

def reload_config():
    load_config()

def ensure_config_exists():
    if not CONFIG_PATH.exists():
        data = {
            "DEFAULT_THUMB_WIDTH": DEFAULT_THUMB_WIDTH,
            "MIN_THUMB_WIDTH": MIN_THUMB_WIDTH,
            "NUM_THUMBS": NUM_THUMBS,
            "THUMB_SPACING": THUMB_SPACING,
            "CONTROL_WIDTH_ESTIMATE": CONTROL_WIDTH_ESTIMATE,
            "CACHE_SIZE": CACHE_SIZE,
            "OCR_SCALE": OCR_SCALE,
            "OCR_USE_CLAHE": OCR_USE_CLAHE,
            "OCR_CLAHE_CLIP": OCR_CLAHE_CLIP,
            "OCR_DENOISE_KSIZE": OCR_DENOISE_KSIZE,
            "OCR_DILATE_ITER": OCR_DILATE_ITER,
            "OCR_INVERT": OCR_INVERT,
            "OCR_BINARIZE": OCR_BINARIZE,
            "OCR_PSM": OCR_PSM,
            "OCR_LANG": OCR_LANG,
            "BASE_INTERNAL_ROOT": BASE_INTERNAL_ROOT,
            "RENAME_DIALOG_SCRIPT": RENAME_DIALOG_SCRIPT,
            "OVERWRITE_HISTORY": [
                list(OVERWRITE_0),
                list(OVERWRITE_1),
                list(OVERWRITE_2),
                list(OVERWRITE_3),
            ]
        }
        save_config(data)

# Initial load
load_config()
