# ---- Config ----
from pathlib import Path

DEFAULT_THUMB_WIDTH = 700
THUMB_ASPECT = 9/16
MIN_THUMB_WIDTH = 120
NUM_THUMBS = 5
THUMB_SPACING = 8
CONTROL_WIDTH_ESTIMATE = 240
CACHE_SIZE = 15  # tamaño máximo del cache LRU (puedes reducirlo si memoria es problema)

# ---------------- OCR parameters (ajustables) ----------------
OCR_SCALE = 2               # escalado X
OCR_USE_CLAHE = True        # aplicar CLAHE (contraste adaptativo)
OCR_CLAHE_CLIP = 2.0       # factor clip para CLAHE (ajusta contraste)
OCR_DENOISE_KSIZE = 3      # ksize para medianBlur (impar: 1,3,5..)
OCR_DILATE_ITER = 1        # iteraciones de dilatación (0=no dilatar)
OCR_INVERT = True          # invertir colores
OCR_BINARIZE = True        # usar umbralización (OTSU)
OCR_PSM = 6                # psm para tesseract
OCR_LANG = 'spa'           # idioma para tesseract
# -----------------------------------------------------------

BASE_INTERNAL_ROOT = r"E:\_Internal"  # ruta base para el panel izquierdo
VIDEO_EXTS = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv'}
APP_DIR = Path(__file__).resolve().parent.as_posix()
ICON_PATH = f"{APP_DIR}/assets/frameetude.ico"
ID_APP = 'etude_video.FrameEtude.VideoFramesInspector.v2'