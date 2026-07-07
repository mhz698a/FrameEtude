from PyQt6 import QtCore, QtWidgets
import config

class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(500, 600) # Un poco más alto para los nuevos campos

        self.layout = QtWidgets.QVBoxLayout(self)
        self.tabs = QtWidgets.QTabWidget()
        self.layout.addWidget(self.tabs)

        # --- OCR Tab ---
        self.ocr_tab = QtWidgets.QWidget()
        self.ocr_layout = QtWidgets.QFormLayout(self.ocr_tab)

        # Corregido a QSpinBox porque en tu config definiste OCR_SCALE como int
        self.ocr_scale = QtWidgets.QSpinBox()
        self.ocr_scale.setRange(1, 10)
        self.ocr_scale.setValue(int(config.OCR_SCALE))
        self.ocr_layout.addRow("OCR Scale:", self.ocr_scale)

        self.ocr_use_clahe = QtWidgets.QCheckBox()
        self.ocr_use_clahe.setChecked(config.OCR_USE_CLAHE)
        self.ocr_layout.addRow("Use CLAHE:", self.ocr_use_clahe)

        self.ocr_clahe_clip = QtWidgets.QDoubleSpinBox()
        self.ocr_clahe_clip.setRange(0.1, 10.0)
        self.ocr_clahe_clip.setValue(config.OCR_CLAHE_CLIP)
        self.ocr_layout.addRow("CLAHE Clip:", self.ocr_clahe_clip)

        self.ocr_denoise = QtWidgets.QSpinBox()
        self.ocr_denoise.setRange(1, 21)
        self.ocr_denoise.setSingleStep(2)
        self.ocr_denoise.setValue(config.OCR_DENOISE_KSIZE)
        self.ocr_denoise.valueChanged.connect(self._ensure_odd)
        self.ocr_layout.addRow("Denoise KSize (odd):", self.ocr_denoise)

        self.ocr_dilate = QtWidgets.QSpinBox()
        self.ocr_dilate.setRange(0, 10)
        self.ocr_dilate.setValue(config.OCR_DILATE_ITER)
        self.ocr_layout.addRow("Dilate Iterations:", self.ocr_dilate)

        self.ocr_invert = QtWidgets.QCheckBox()
        self.ocr_invert.setChecked(bool(config.OCR_INVERT))
        self.ocr_layout.addRow("Invert Colors:", self.ocr_invert)

        self.ocr_binarize = QtWidgets.QCheckBox()
        self.ocr_binarize.setChecked(bool(config.OCR_BINARIZE))
        self.ocr_layout.addRow("Binarize (OTSU):", self.ocr_binarize)

        self.ocr_psm = QtWidgets.QSpinBox()
        self.ocr_psm.setRange(0, 13)
        self.ocr_psm.setValue(config.OCR_PSM)
        self.ocr_layout.addRow("Tesseract PSM:", self.ocr_psm)

        self.ocr_lang = QtWidgets.QLineEdit()
        self.ocr_lang.setText(config.OCR_LANG)
        self.ocr_layout.addRow("Tesseract Lang:", self.ocr_lang)

        self.tabs.addTab(self.ocr_tab, "OCR")

        # --- General Tab ---
        self.gen_tab = QtWidgets.QWidget()
        self.gen_layout = QtWidgets.QFormLayout(self.gen_tab)

        self.thumb_width = QtWidgets.QSpinBox()
        self.thumb_width.setRange(100, 2000)
        self.thumb_width.setValue(config.DEFAULT_THUMB_WIDTH)
        self.gen_layout.addRow("Default Thumb Width:", self.thumb_width)

        self.min_thumb_width = QtWidgets.QSpinBox()
        self.min_thumb_width.setRange(50, 1000)
        self.min_thumb_width.setValue(config.MIN_THUMB_WIDTH)
        self.gen_layout.addRow("Min Thumb Width:", self.min_thumb_width)

        self.num_thumbs = QtWidgets.QSpinBox()
        self.num_thumbs.setRange(1, 15)
        self.num_thumbs.setValue(config.NUM_THUMBS)
        self.gen_layout.addRow("Number of Thumbs:", self.num_thumbs)

        self.thumb_spacing = QtWidgets.QSpinBox()
        self.thumb_spacing.setRange(0, 50)
        self.thumb_spacing.setValue(config.THUMB_SPACING)
        self.gen_layout.addRow("Thumb Spacing:", self.thumb_spacing)

        self.cache_size = QtWidgets.QSpinBox()
        self.cache_size.setRange(1, 100)
        self.cache_size.setValue(config.CACHE_SIZE)
        self.gen_layout.addRow("Cache Size:", self.cache_size)

        self.control_width = QtWidgets.QSpinBox()
        self.control_width.setRange(100, 1000)
        self.control_width.setValue(config.CONTROL_WIDTH_ESTIMATE)
        self.gen_layout.addRow("Control Width Estimate:", self.control_width)

        # Campo de script con botón de búsqueda de archivo (.py)
        self.rename_script = QtWidgets.QLineEdit()
        self.rename_script.setText(config.RENAME_DIALOG_SCRIPT)
        self.btn_browse_script = QtWidgets.QPushButton("Browse...")
        self.btn_browse_script.clicked.connect(self._browse_script)

        script_layout = QtWidgets.QHBoxLayout()
        script_layout.addWidget(self.rename_script)
        script_layout.addWidget(self.btn_browse_script)
        self.gen_layout.addRow("Rename Script:", script_layout)

        # Campo de ruta raíz con botón de búsqueda de carpeta
        self.internal_root = QtWidgets.QLineEdit()
        self.internal_root.setText(config.BASE_INTERNAL_ROOT)
        self.btn_browse_root = QtWidgets.QPushButton("Browse...")
        self.btn_browse_root.clicked.connect(self._browse_root)

        root_layout = QtWidgets.QHBoxLayout()
        root_layout.addWidget(self.internal_root)
        root_layout.addWidget(self.btn_browse_root)
        self.gen_layout.addRow("Internal Root:", root_layout)

        # Campo para OVERWRITE_DATABASE
        self.overwrite_db = QtWidgets.QLineEdit()
        self.overwrite_db.setText(config.OVERWRITE_DATABASE)
        self.btn_browse_ov = QtWidgets.QPushButton("Browse...")
        self.btn_browse_ov.clicked.connect(self._browse_overwrite_db)

        ov_layout = QtWidgets.QHBoxLayout()
        ov_layout.addWidget(self.overwrite_db)
        ov_layout.addWidget(self.btn_browse_ov)
        self.gen_layout.addRow("Overwrite DB:", ov_layout)

        # Campo para SEASON_DATABASE
        self.season_db = QtWidgets.QLineEdit()
        self.season_db.setText(config.SEASON_DATABASE)
        self.btn_browse_season = QtWidgets.QPushButton("Browse...")
        self.btn_browse_season.clicked.connect(self._browse_season_db)

        season_layout = QtWidgets.QHBoxLayout()
        season_layout.addWidget(self.season_db)
        season_layout.addWidget(self.btn_browse_season)
        self.gen_layout.addRow("Season DB:", season_layout)

        # Campo para BACKUP_PATH
        self.backup_path = QtWidgets.QLineEdit()
        self.backup_path.setText(config.BACKUP_PATH)
        self.btn_browse_backup = QtWidgets.QPushButton("Browse...")
        self.btn_browse_backup.clicked.connect(self._browse_backup_path)

        backup_layout = QtWidgets.QHBoxLayout()
        backup_layout.addWidget(self.backup_path)
        backup_layout.addWidget(self.btn_browse_backup)
        self.gen_layout.addRow("Backup Path:", backup_layout)

        self.tabs.addTab(self.gen_tab, "General")

        # --- Buttons ---
        self.buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok |
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self.save)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons)

    def _ensure_odd(self, value):
        if value > 0 and value % 2 == 0:
            self.ocr_denoise.setValue(value + 1)

    def _browse_script(self):
        """Abre explorador nativo para seleccionar el script de Python."""
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select Rename Script", self.rename_script.text(), "Python Files (*.py);;All Files (*)"
        )
        if file_path:
            self.rename_script.setText(file_path)

    def _browse_root(self):
        """Abre explorador nativo para seleccionar el directorio raíz."""
        dir_path = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select Internal Root Directory", self.internal_root.text()
        )
        if dir_path:
            self.internal_root.setText(dir_path)

    def _browse_overwrite_db(self):
        """Abre explorador nativo para seleccionar el archivo JSON de overwrite."""
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select Overwrite Database", self.overwrite_db.text(), "JSON Files (*.json);;All Files (*)"
        )
        if file_path:
            self.overwrite_db.setText(file_path)

    def _browse_season_db(self):
        """Abre explorador nativo para seleccionar el archivo JSON de seasons."""
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select Season Database", self.season_db.text(), "JSON Files (*.json);;All Files (*)"
        )
        if file_path:
            self.season_db.setText(file_path)

    def _browse_backup_path(self):
        """Abre explorador nativo para seleccionar el directorio de respaldo."""
        dir_path = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select Backup Directory", self.backup_path.text()
        )
        if dir_path:
            self.backup_path.setText(dir_path)

    def save(self):
        # Empaquetar datos de OCR respetando tus tipos de datos originales
        new_ocr = {
            "OCR_SCALE": int(self.ocr_scale.value()),
            "OCR_USE_CLAHE": self.ocr_use_clahe.isChecked(),
            "OCR_CLAHE_CLIP": float(self.ocr_clahe_clip.value()),
            "OCR_DENOISE_KSIZE": int(self.ocr_denoise.value()),
            "OCR_DILATE_ITER": int(self.ocr_dilate.value()),
            "OCR_INVERT": int(self.ocr_invert.isChecked()), # Guardado como entero según tu config
            "OCR_BINARIZE": int(self.ocr_binarize.isChecked()), # Guardado como entero según tu config
            "OCR_PSM": int(self.ocr_psm.value()),
            "OCR_LANG": str(self.ocr_lang.text())
        }

        # Empaquetar datos generales
        new_general = {
            "DEFAULT_THUMB_WIDTH": int(self.thumb_width.value()),
            "MIN_THUMB_WIDTH": int(self.min_thumb_width.value()),
            "NUM_THUMBS": int(self.num_thumbs.value()),
            "THUMB_SPACING": int(self.thumb_spacing.value()),
            "CACHE_SIZE": int(self.cache_size.value()),
            "CONTROL_WIDTH_ESTIMATE": int(self.control_width.value()),
            "RENAME_DIALOG_SCRIPT": str(self.rename_script.text()),
            "BASE_INTERNAL_ROOT": str(self.internal_root.text()),
            "OVERWRITE_DATABASE": str(self.overwrite_db.text()),
            "SEASON_DATABASE": str(self.season_db.text()),
            "BACKUP_PATH": str(self.backup_path.text())
        }

        # Enviar los datos al puente de guardado seguro
        config.update_and_save(new_ocr, new_general)
        self.accept()
