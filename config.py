import os
import tomllib
from pathlib import Path

# --- Constantes fijas de la aplicación ---
APP_NAME = "FrameEtude"
ID_APP = 'etude_video.FrameEtude.VideoFramesInspector.v2'
ID_APP_LIRYCS = 'etude_video.LyricManagment.LyricsBook.v2'
ID_APP_PHASE_GEN = 'etude_video.LyricManagment.PlanMdGen.v1'
ID_APP_TMP_EP = 'etude_video.LyricManagment.temp_EpList.v1'

USER_HOME = Path.home()
APP_DIR = Path(__file__).resolve().parent.as_posix()

ICON_PATH_LIRYCS = f"{APP_DIR}/assets/lyricsbook.ico"
ICON_PATH = f"{APP_DIR}/assets/frameetude.ico"
VIDEO_EXTS = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv'}
THUMB_ASPECT = 9/16

APPDATA_DIR = Path(os.getenv("APPDATA", USER_HOME)) / APP_NAME
APPDATA_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_FILE = APPDATA_DIR / "settings.toml"

# --- Valores por defecto (con tus comentarios) ---
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
    "RENAME_DIALOG_SCRIPT": r"",
    "OVERWRITE_DATABASE": "",
    "SEASON_DATABASE": "",
    "BASE_INTERNAL_ROOT": r"E:\_Internal", # Ajuste parametrado para sistema local
    "DEFAULT_THUMB_WIDTH": 700,
    "MIN_THUMB_WIDTH": 120,
    "NUM_THUMBS": 5,
    "THUMB_SPACING": 8,
    "CONTROL_WIDTH_ESTIMATE": 240,
    "CACHE_SIZE": 15, # tamaño máximo del cache LRU (afecta rendimiento de CPU/RAM)
}

# Diccionario contenedor interno para evitar usar la palabra clave 'global'
_C = {
    "ocr": DEFAULT_OCR_PARAMETERS.copy(),
    "general": DEFAULT_SETTINGS.copy()
}

def load_settings():
    """Lee el archivo TOML y actualiza el contenedor interno."""
    if not SETTINGS_FILE.exists():
        save_settings()
        return

    try:
        with open(SETTINGS_FILE, "rb") as f:
            data = tomllib.load(f)
            _C["ocr"].update(data.get("ocr", {}))
            _C["general"].update(data.get("general", {}))
    except Exception as e:
        print(f"Error loading settings: {e}")

def save_settings():
    """Guarda la configuración actual en el archivo TOML."""
    lines = []
    
    lines.append("[ocr]")
    for k, v in _C["ocr"].items():
        if isinstance(v, bool):
            lines.append(f"{k} = {'true' if v else 'false'}")
        elif isinstance(v, str):
            lines.append(f'{k} = "{v}"')
        else:
            lines.append(f"{k} = {v}")
    
    lines.append("\n[general]")
    for k, v in _C["general"].items():
        if isinstance(v, str):
            # Escapa barras invertidas automáticamente para rutas de Windows
            escaped_str = v.replace("\\", "\\\\")
            lines.append(f'{k} = "{escaped_str}"')
        else:
            lines.append(f"{k} = {v}")

    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    except Exception as e:
        print(f"Error saving settings: {e}")

def update_and_save(ocr_data, general_data):
    """Actualiza el diccionario interno con nuevos datos del diálogo y los guarda."""
    _C["ocr"].update(ocr_data)
    _C["general"].update(general_data)
    save_settings()
    
    # Recargar las variables globales del módulo para el resto de la app
    globals().update({k: int(v) if isinstance(v, (int, float)) and k != "OCR_CLAHE_CLIP" else v for k, v in ocr_data.items()})
    globals().update({k: v for k, v in general_data.items()})


# --- Cargar datos inicialmente desde el archivo ---
load_settings()

# --- Exposición de variables con tus conversiones de tipo explícitas ---
OCR_SCALE = int(_C["ocr"]["OCR_SCALE"])
OCR_USE_CLAHE = bool(_C["ocr"]["OCR_USE_CLAHE"])       
OCR_CLAHE_CLIP = float(_C["ocr"]["OCR_CLAHE_CLIP"])
OCR_DENOISE_KSIZE = int(_C["ocr"]["OCR_DENOISE_KSIZE"])
OCR_DILATE_ITER = int(_C["ocr"]["OCR_DILATE_ITER"])     
OCR_INVERT = int(_C["ocr"]["OCR_INVERT"])
OCR_BINARIZE = int(_C["ocr"]["OCR_BINARIZE"])
OCR_PSM = int(_C["ocr"]["OCR_PSM"])
OCR_LANG = str(_C["ocr"]["OCR_LANG"])

RENAME_DIALOG_SCRIPT = str(_C["general"]["RENAME_DIALOG_SCRIPT"])
OVERWRITE_DATABASE = str(_C["general"]["OVERWRITE_DATABASE"])
SEASON_DATABASE = str(_C["general"]["SEASON_DATABASE"])
BASE_INTERNAL_ROOT = str(_C["general"]["BASE_INTERNAL_ROOT"])

DEFAULT_THUMB_WIDTH = int(_C["general"]["DEFAULT_THUMB_WIDTH"])
MIN_THUMB_WIDTH = int(_C["general"]["MIN_THUMB_WIDTH"])
NUM_THUMBS = int(_C["general"]["NUM_THUMBS"])
THUMB_SPACING = int(_C["general"]["THUMB_SPACING"])
CONTROL_WIDTH_ESTIMATE = int(_C["general"]["CONTROL_WIDTH_ESTIMATE"])
CACHE_SIZE = int(_C["general"]["CACHE_SIZE"])
