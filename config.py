# config.py
import os
import tomllib
from pathlib import Path

APP_NAME = "FrameEtude"
ID_APP = 'etude_video.FrameEtude.VideoFramesInspector.v2'
ID_APP_LIRYCS = 'etude_video.LyricManagment.LyricsBook.v2'

USER_HOME = Path.home()
APP_DIR = Path(__file__).resolve().parent.as_posix()

ICON_PATH_LIRYCS = f"{APP_DIR}/assets/lyricsbook.ico"
ICON_PATH = f"{APP_DIR}/assets/frameetude.ico"
VIDEO_EXTS = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv'}
THUMB_ASPECT = 9/16

APPDATA_DIR = Path(os.getenv("APPDATA", USER_HOME)) / APP_NAME
APPDATA_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_FILE = APPDATA_DIR / "settings.toml"

DEFAULT_OCR_PARAMETERS = {
    "OCR_SCALE": 2,
    "OCR_USE_CLAHE": True,
    "OCR_CLAHE_CLIP": 2.0,
    "OCR_DENOISE_KSIZE": 3,
    "OCR_DILATE_ITER": 1,
    "OCR_INVERT": True,
    "OCR_BINARIZE": True,
    "OCR_PSM": 6,
    "OCR_LANG": "spa",
}

DEFAULT_SETTINGS = {
    "DEFAULT_THUMB_WIDTH": 700,
    "MIN_THUMB_WIDTH": 120,
    "NUM_THUMBS": 5,
    "THUMB_SPACING": 8,
    "CONTROL_WIDTH_ESTIMATE": 240,
    "CACHE_SIZE": 15,
    "RENAME_DIALOG_SCRIPT": r"C:\Users\miche\OneDrive\foobar2000\profile\ActivityBar\rename_dialog.py",
    "BASE_INTERNAL_ROOT": r"E:\_Internal",
}

# Constant-like settings that are not in the toml
OVERWRITE_DATABASE = f"{APP_DIR}/overwrite.json"
SEASON_DATABASE = f"{APP_DIR}/seasons.json"

# These will be populated by load_settings
OCR_SCALE = DEFAULT_OCR_PARAMETERS["OCR_SCALE"]
OCR_USE_CLAHE = DEFAULT_OCR_PARAMETERS["OCR_USE_CLAHE"]
OCR_CLAHE_CLIP = DEFAULT_OCR_PARAMETERS["OCR_CLAHE_CLIP"]
OCR_DENOISE_KSIZE = DEFAULT_OCR_PARAMETERS["OCR_DENOISE_KSIZE"]
OCR_DILATE_ITER = DEFAULT_OCR_PARAMETERS["OCR_DILATE_ITER"]
OCR_INVERT = DEFAULT_OCR_PARAMETERS["OCR_INVERT"]
OCR_BINARIZE = DEFAULT_OCR_PARAMETERS["OCR_BINARIZE"]
OCR_PSM = DEFAULT_OCR_PARAMETERS["OCR_PSM"]
OCR_LANG = DEFAULT_OCR_PARAMETERS["OCR_LANG"]

DEFAULT_THUMB_WIDTH = DEFAULT_SETTINGS["DEFAULT_THUMB_WIDTH"]
MIN_THUMB_WIDTH = DEFAULT_SETTINGS["MIN_THUMB_WIDTH"]
NUM_THUMBS = DEFAULT_SETTINGS["NUM_THUMBS"]
THUMB_SPACING = DEFAULT_SETTINGS["THUMB_SPACING"]
CONTROL_WIDTH_ESTIMATE = DEFAULT_SETTINGS["CONTROL_WIDTH_ESTIMATE"]
CACHE_SIZE = DEFAULT_SETTINGS["CACHE_SIZE"]
RENAME_DIALOG_SCRIPT = DEFAULT_SETTINGS["RENAME_DIALOG_SCRIPT"]
BASE_INTERNAL_ROOT = DEFAULT_SETTINGS["BASE_INTERNAL_ROOT"]

def load_settings():
    global OCR_SCALE, OCR_USE_CLAHE, OCR_CLAHE_CLIP, OCR_DENOISE_KSIZE, OCR_DILATE_ITER
    global OCR_INVERT, OCR_BINARIZE, OCR_PSM, OCR_LANG
    global DEFAULT_THUMB_WIDTH, MIN_THUMB_WIDTH, NUM_THUMBS, THUMB_SPACING
    global CONTROL_WIDTH_ESTIMATE, CACHE_SIZE, RENAME_DIALOG_SCRIPT, BASE_INTERNAL_ROOT

    if not SETTINGS_FILE.exists():
        save_settings()
        return

    try:
        with open(SETTINGS_FILE, "rb") as f:
            data = tomllib.load(f)

        ocr = data.get("ocr", {})
        general = data.get("general", {})

        OCR_SCALE = ocr.get("OCR_SCALE", DEFAULT_OCR_PARAMETERS["OCR_SCALE"])
        OCR_USE_CLAHE = ocr.get("OCR_USE_CLAHE", DEFAULT_OCR_PARAMETERS["OCR_USE_CLAHE"])
        OCR_CLAHE_CLIP = ocr.get("OCR_CLAHE_CLIP", DEFAULT_OCR_PARAMETERS["OCR_CLAHE_CLIP"])
        OCR_DENOISE_KSIZE = ocr.get("OCR_DENOISE_KSIZE", DEFAULT_OCR_PARAMETERS["OCR_DENOISE_KSIZE"])
        OCR_DILATE_ITER = ocr.get("OCR_DILATE_ITER", DEFAULT_OCR_PARAMETERS["OCR_DILATE_ITER"])
        OCR_INVERT = ocr.get("OCR_INVERT", DEFAULT_OCR_PARAMETERS["OCR_INVERT"])
        OCR_BINARIZE = ocr.get("OCR_BINARIZE", DEFAULT_OCR_PARAMETERS["OCR_BINARIZE"])
        OCR_PSM = ocr.get("OCR_PSM", DEFAULT_OCR_PARAMETERS["OCR_PSM"])
        OCR_LANG = ocr.get("OCR_LANG", DEFAULT_OCR_PARAMETERS["OCR_LANG"])

        DEFAULT_THUMB_WIDTH = general.get("DEFAULT_THUMB_WIDTH", DEFAULT_SETTINGS["DEFAULT_THUMB_WIDTH"])
        MIN_THUMB_WIDTH = general.get("MIN_THUMB_WIDTH", DEFAULT_SETTINGS["MIN_THUMB_WIDTH"])
        NUM_THUMBS = general.get("NUM_THUMBS", DEFAULT_SETTINGS["NUM_THUMBS"])
        THUMB_SPACING = general.get("THUMB_SPACING", DEFAULT_SETTINGS["THUMB_SPACING"])
        CONTROL_WIDTH_ESTIMATE = general.get("CONTROL_WIDTH_ESTIMATE", DEFAULT_SETTINGS["CONTROL_WIDTH_ESTIMATE"])
        CACHE_SIZE = general.get("CACHE_SIZE", DEFAULT_SETTINGS["CACHE_SIZE"])
        RENAME_DIALOG_SCRIPT = general.get("RENAME_DIALOG_SCRIPT", DEFAULT_SETTINGS["RENAME_DIALOG_SCRIPT"])
        BASE_INTERNAL_ROOT = general.get("BASE_INTERNAL_ROOT", DEFAULT_SETTINGS["BASE_INTERNAL_ROOT"])

    except Exception as e:
        print(f"Error loading settings: {e}")

def save_settings():
    if not APPDATA_DIR.exists():
        APPDATA_DIR.mkdir(parents=True, exist_ok=True)
    lines = []
    lines.append("[ocr]")
    lines.append(f"OCR_SCALE = {OCR_SCALE}")
    lines.append(f"OCR_USE_CLAHE = {'true' if OCR_USE_CLAHE else 'false'}")
    lines.append(f"OCR_CLAHE_CLIP = {OCR_CLAHE_CLIP}")
    lines.append(f"OCR_DENOISE_KSIZE = {OCR_DENOISE_KSIZE}")
    lines.append(f"OCR_DILATE_ITER = {OCR_DILATE_ITER}")
    lines.append(f"OCR_INVERT = {'true' if OCR_INVERT else 'false'}")
    lines.append(f"OCR_BINARIZE = {'true' if OCR_BINARIZE else 'false'}")
    lines.append(f"OCR_PSM = {OCR_PSM}")
    lines.append(f'OCR_LANG = "{OCR_LANG}"')
    lines.append("")
    lines.append("[general]")
    lines.append(f"DEFAULT_THUMB_WIDTH = {DEFAULT_THUMB_WIDTH}")
    lines.append(f"MIN_THUMB_WIDTH = {MIN_THUMB_WIDTH}")
    lines.append(f"NUM_THUMBS = {NUM_THUMBS}")
    lines.append(f"THUMB_SPACING = {THUMB_SPACING}")
    lines.append(f"CONTROL_WIDTH_ESTIMATE = {CONTROL_WIDTH_ESTIMATE}")
    lines.append(f"CACHE_SIZE = {CACHE_SIZE}")

    # Escape backslashes for TOML strings
    script_path = RENAME_DIALOG_SCRIPT.replace("\\", "\\\\")
    lines.append(f'RENAME_DIALOG_SCRIPT = "{script_path}"')
    root_path = BASE_INTERNAL_ROOT.replace("\\", "\\\\")
    lines.append(f'BASE_INTERNAL_ROOT = "{root_path}"')

    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    except Exception as e:
        print(f"Error saving settings: {e}")

load_settings()
