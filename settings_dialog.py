from PyQt6 import QtCore, QtWidgets
import config

class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(450, 500)

        self.layout = QtWidgets.QVBoxLayout(self)

        self.tabs = QtWidgets.QTabWidget()
        self.layout.addWidget(self.tabs)

        # --- OCR Tab ---
        self.ocr_tab = QtWidgets.QWidget()
        self.ocr_layout = QtWidgets.QFormLayout(self.ocr_tab)

        self.ocr_scale = QtWidgets.QDoubleSpinBox()
        self.ocr_scale.setRange(0.1, 10.0)
        self.ocr_scale.setValue(config.OCR_SCALE)
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
        self.ocr_invert.setChecked(config.OCR_INVERT)
        self.ocr_layout.addRow("Invert Colors:", self.ocr_invert)

        self.ocr_binarize = QtWidgets.QCheckBox()
        self.ocr_binarize.setChecked(config.OCR_BINARIZE)
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

        self.rename_script = QtWidgets.QLineEdit()
        self.rename_script.setText(config.RENAME_DIALOG_SCRIPT)
        self.gen_layout.addRow("Rename Script:", self.rename_script)

        self.internal_root = QtWidgets.QLineEdit()
        self.internal_root.setText(config.BASE_INTERNAL_ROOT)
        self.gen_layout.addRow("Internal Root:", self.internal_root)

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

    def save(self):
        # Update config module variables
        config.OCR_SCALE = self.ocr_scale.value()
        config.OCR_USE_CLAHE = self.ocr_use_clahe.isChecked()
        config.OCR_CLAHE_CLIP = self.ocr_clahe_clip.value()
        config.OCR_DENOISE_KSIZE = self.ocr_denoise.value()
        config.OCR_DILATE_ITER = self.ocr_dilate.value()
        config.OCR_INVERT = self.ocr_invert.isChecked()
        config.OCR_BINARIZE = self.ocr_binarize.isChecked()
        config.OCR_PSM = self.ocr_psm.value()
        config.OCR_LANG = self.ocr_lang.text()

        config.DEFAULT_THUMB_WIDTH = self.thumb_width.value()
        config.MIN_THUMB_WIDTH = self.min_thumb_width.value()
        config.NUM_THUMBS = self.num_thumbs.value()
        config.THUMB_SPACING = self.thumb_spacing.value()
        config.CACHE_SIZE = self.cache_size.value()
        config.CONTROL_WIDTH_ESTIMATE = self.control_width.value()
        config.RENAME_DIALOG_SCRIPT = self.rename_script.text()
        config.BASE_INTERNAL_ROOT = self.internal_root.text()

        # Persist to file
        config.save_settings()
        self.accept()
