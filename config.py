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

BASE_INTERNAL_ROOT = r"E:\_Internal"
VIDEO_EXTS = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv'}
APP_DIR = Path(__file__).resolve().parent.as_posix()
ICON_PATH = f"{APP_DIR}/assets/frameetude.ico"
ICON_PATH_LIRYCS = f"{APP_DIR}/assets/lyricsbook.ico"
ID_APP = 'etude_video.FrameEtude.VideoFramesInspector.v2'
ID_APP_LIRYCS = 'etude_video.LyricManagment.LyricsBook.v2'

# -----------------------------------------------------------------------
RENAME_DIALOG_EXE = "pythonw"
RENAME_DIALOG_SCRIPT = r"C:\Users\miche\OneDrive\foobar2000\profile\ActivityBar\rename_dialog.py"

# -----------------------------------------------------------------------
# Informacion acerca de la sobrescritura
# (time_num, review_date, info)
OVERWRITE_0 = (0, "2022-06-13", "Examen de admision a la sobrescritura vigilado por SRPF CometNova, para aspirantes al colegio de sobrescritores y estudios a fines, en el examen se trata 1999-2003. El examen de admision concluyo el 31 de diciembre del 2022.")

OVERWRITE_1 = (1, "2023-01-01", "Primera vez que se hace sobrescritura a cargo de la TSPF & ERPF. La mejora es instruida por las fundaciones administrativas Nova, tratando los rangos 2004-2018 para 2023, 2019-2024 para 2024. Se alcanzo el ultimo episodio más reciente el 2024-05-13.")

OVERWRITE_2 = (2, "2024-08-31", "Segunda vez que se hace sobrescritura pero esta vez haciendo redaccion y referenicas y percepcion sentimental. Se permite el control individual para analisis de episodios y profundizacion de eventos entre los años 2004-2025 en los años 2024-2025. Se alcanzo el ultimo episodio más reciente el 31 de diciembre del 2025.")

OVERWRITE_3 = (3, "2030-01-01", "Tercera vez que se hace sobrescritura, tiene como plan iniciar la sobrescritura en los años del 2030s.")
