# config.py
import os
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


DEFAULT_OCR_PARAMETERS = {
    "OCR_SCALE": 2,         # escalado X
    "OCR_USE_CLAHE": True,  # aplicar CLAHE (contraste adaptativo)
    "OCR_CLAHE_CLIP": 2.0,  # factor clip para CLAHE (ajusta contraste)
    "OCR_DENOISE_KSIZE": 3, # ksize para medianBlur (impar: 1,3,5..)
    "OCR_DILATE_ITER": 1,   # iteraciones de dilatación (0=no dilatar)
    "OCR_INVERT": True,     # invertir colores
    "OCR_BINARIZE": True,   # usar umbralización (OTSU)
    "OCR_PSM": 6,           # psm para tesseract
    "OCR_LANG": 'spa',      # idioma para tesseract
}

DEFAULT_SETTINGS = {
    "RENAME_DIALOG_SCRIPT": r"C:\Users\miche\OneDrive\foobar2000\profile\ActivityBar\rename_dialog.py",
    "OVERWRITE_DATABASE": f"{APP_DIR}/overwrite.json",
    "SEASON_DATABASE": f"{APP_DIR}/seasons.json",
    "BASE_INTERNAL_ROOT": r"E:\_Internal",
    "DEFAULT_THUMB_WIDTH": 700,
    "MIN_THUMB_WIDTH": 120,
    "NUM_THUMBS": 5,
    "THUMB_SPACING": 8,
    "CONTROL_WIDTH_ESTIMATE": 240,
    "CACHE_SIZE": 15, # tamaño máximo del cache LRU (afecta rendimiento de CPU/RAM)
}

OCR_SCALE = int(DEFAULT_OCR_PARAMETERS["OCR_SCALE"])
OCR_USE_CLAHE = bool(DEFAULT_OCR_PARAMETERS["OCR_USE_CLAHE"])       
OCR_CLAHE_CLIP = float(DEFAULT_OCR_PARAMETERS["OCR_CLAHE_CLIP"])
OCR_DENOISE_KSIZE = int(DEFAULT_OCR_PARAMETERS["OCR_DENOISE_KSIZE"])
OCR_DILATE_ITER = int(DEFAULT_OCR_PARAMETERS["OCR_DILATE_ITER"])     
OCR_INVERT = int(DEFAULT_OCR_PARAMETERS["OCR_INVERT"])
OCR_BINARIZE = int(DEFAULT_OCR_PARAMETERS["OCR_BINARIZE"])
OCR_PSM = int(DEFAULT_OCR_PARAMETERS["OCR_PSM"])
OCR_LANG = str(DEFAULT_OCR_PARAMETERS["OCR_LANG"])
RENAME_DIALOG_SCRIPT = str(DEFAULT_SETTINGS["RENAME_DIALOG_SCRIPT"])
OVERWRITE_DATABASE = str(DEFAULT_SETTINGS["OVERWRITE_DATABASE"])
SEASON_DATABASE = str(DEFAULT_SETTINGS["SEASON_DATABASE"])
BASE_INTERNAL_ROOT = str(DEFAULT_SETTINGS["BASE_INTERNAL_ROOT"])

DEFAULT_THUMB_WIDTH = int(DEFAULT_SETTINGS["DEFAULT_THUMB_WIDTH"])
MIN_THUMB_WIDTH = int(DEFAULT_SETTINGS["MIN_THUMB_WIDTH"])
NUM_THUMBS = int(DEFAULT_SETTINGS["NUM_THUMBS"])
THUMB_SPACING = int(DEFAULT_SETTINGS["THUMB_SPACING"])
CONTROL_WIDTH_ESTIMATE = int(DEFAULT_SETTINGS["CONTROL_WIDTH_ESTIMATE"])
CACHE_SIZE = int(DEFAULT_SETTINGS["CACHE_SIZE"])
