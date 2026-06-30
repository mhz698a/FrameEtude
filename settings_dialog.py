import os
from PyQt6 import QtWidgets, QtCore, QtGui
import config

class AjustesDialog(QtWidgets.QDialog):
    settings_saved = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración de FrameEtude")
        self.resize(600, 500)
        self.setModal(True)

        config.ensure_config_exists()

        self.layout = QtWidgets.QVBoxLayout(self)

        self.tabs = QtWidgets.QTabWidget()
        self.layout.addWidget(self.tabs)

        # Tab 1: Sistema
        self.tab_sistema = QtWidgets.QWidget()
        self.setup_tab_sistema()
        self.tabs.addTab(self.tab_sistema, "Sistema")

        # Tab 2: Motor OCR
        self.tab_ocr = QtWidgets.QWidget()
        self.setup_tab_ocr()
        self.tabs.addTab(self.tab_ocr, "Motor OCR")

        # Tab 3: Interfaz y Caché
        self.tab_interfaz = QtWidgets.QWidget()
        self.setup_tab_interfaz()
        self.tabs.addTab(self.tab_interfaz, "Interfaz y Caché")

        # Tab 4: Historial de Sobrescritura
        self.tab_historial = QtWidgets.QWidget()
        self.setup_tab_historial()
        self.tabs.addTab(self.tab_historial, "Historial de Sobrescritura")

        # Action Buttons
        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Save |
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.save_and_close)
        self.button_box.rejected.connect(self.reject)

        # Rename buttons to Spanish
        self.button_box.button(QtWidgets.QDialogButtonBox.StandardButton.Save).setText("Guardar")
        self.button_box.button(QtWidgets.QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")

        self.layout.addWidget(self.button_box)

    def setup_tab_sistema(self):
        layout = QtWidgets.QFormLayout(self.tab_sistema)

        # BASE_INTERNAL_ROOT
        self.root_edit = QtWidgets.QLineEdit(config.BASE_INTERNAL_ROOT)
        self.root_btn = QtWidgets.QPushButton("Examinar...")
        self.root_btn.clicked.connect(self.browse_root)

        root_h = QtWidgets.QHBoxLayout()
        root_h.addWidget(self.root_edit)
        root_h.addWidget(self.root_btn)
        layout.addRow("Ruta Raíz Interna:", root_h)

        # RENAME_DIALOG_SCRIPT
        self.script_edit = QtWidgets.QLineEdit(config.RENAME_DIALOG_SCRIPT)
        self.script_btn = QtWidgets.QPushButton("Examinar...")
        self.script_btn.clicked.connect(self.browse_script)

        script_h = QtWidgets.QHBoxLayout()
        script_h.addWidget(self.script_edit)
        script_h.addWidget(self.script_btn)
        layout.addRow("Script de Renombrado:", script_h)

    def setup_tab_ocr(self):
        layout = QtWidgets.QFormLayout(self.tab_ocr)

        # OCR_SCALE
        self.ocr_scale = QtWidgets.QSpinBox()
        self.ocr_scale.setRange(1, 10)
        self.ocr_scale.setValue(config.OCR_SCALE)
        self.ocr_scale.setToolTip("Factor de escalado para mejorar la detección de texto.")
        layout.addRow("Escala OCR:", self.ocr_scale)

        # OCR_USE_CLAHE
        self.ocr_use_clahe = QtWidgets.QCheckBox()
        self.ocr_use_clahe.setChecked(config.OCR_USE_CLAHE)
        self.ocr_use_clahe.setToolTip("Aplicar CLAHE (Contraste Adaptativo) para mejorar visibilidad.")
        layout.addRow("Usar CLAHE:", self.ocr_use_clahe)

        # OCR_CLAHE_CLIP
        self.ocr_clahe_clip = QtWidgets.QDoubleSpinBox()
        self.ocr_clahe_clip.setRange(0.1, 10.0)
        self.ocr_clahe_clip.setSingleStep(0.1)
        self.ocr_clahe_clip.setValue(config.OCR_CLAHE_CLIP)
        self.ocr_clahe_clip.setEnabled(config.OCR_USE_CLAHE)
        self.ocr_clahe_clip.setToolTip("Factor de clip para CLAHE (ajusta el contraste).")
        layout.addRow("CLAHE Clip:", self.ocr_clahe_clip)
        self.ocr_use_clahe.toggled.connect(self.ocr_clahe_clip.setEnabled)

        # OCR_DENOISE_KSIZE
        self.ocr_denoise_ksize = QtWidgets.QSpinBox()
        self.ocr_denoise_ksize.setRange(1, 15)
        self.ocr_denoise_ksize.setSingleStep(2)
        self.ocr_denoise_ksize.setValue(config.OCR_DENOISE_KSIZE)
        self.ocr_denoise_ksize.valueChanged.connect(self.validate_ksize)
        self.ocr_denoise_ksize.setToolTip("Tamaño del kernel para eliminación de ruido. Debe ser impar.")
        layout.addRow("Denoise KSize (Impar):", self.ocr_denoise_ksize)

        # OCR_DILATE_ITER
        self.ocr_dilate_iter = QtWidgets.QSpinBox()
        self.ocr_dilate_iter.setRange(0, 10)
        self.ocr_dilate_iter.setValue(config.OCR_DILATE_ITER)
        self.ocr_dilate_iter.setToolTip("Iteraciones de dilatación (0 para desactivar).")
        layout.addRow("Iteraciones Dilatación:", self.ocr_dilate_iter)

        # OCR_INVERT
        self.ocr_invert = QtWidgets.QCheckBox()
        self.ocr_invert.setChecked(config.OCR_INVERT)
        self.ocr_invert.setToolTip("Invertir colores del frame para el OCR.")
        layout.addRow("Invertir Colores:", self.ocr_invert)

        # OCR_BINARIZE
        self.ocr_binarize = QtWidgets.QCheckBox()
        self.ocr_binarize.setChecked(config.OCR_BINARIZE)
        self.ocr_binarize.setToolTip("Usar umbralización (OTSU) para binarizar la imagen.")
        layout.addRow("Binarizar (OTSU):", self.ocr_binarize)

        # OCR_PSM
        self.ocr_psm = QtWidgets.QSpinBox()
        self.ocr_psm.setRange(0, 13)
        self.ocr_psm.setValue(config.OCR_PSM)
        self.ocr_psm.setToolTip("Modo de segmentación de página de Tesseract (PSM).")
        layout.addRow("Tesseract PSM:", self.ocr_psm)

        # OCR_LANG
        self.ocr_lang = QtWidgets.QComboBox()
        self.ocr_lang.addItems(['spa', 'eng'])
        self.ocr_lang.setCurrentText(config.OCR_LANG)
        self.ocr_lang.setToolTip("Idioma utilizado por Tesseract.")
        layout.addRow("Idioma OCR:", self.ocr_lang)

    def setup_tab_interfaz(self):
        layout = QtWidgets.QFormLayout(self.tab_interfaz)

        self.thumb_width = QtWidgets.QSpinBox()
        self.thumb_width.setRange(100, 2000)
        self.thumb_width.setValue(config.DEFAULT_THUMB_WIDTH)
        layout.addRow("Ancho Miniatura Defecto:", self.thumb_width)

        self.min_thumb_width = QtWidgets.QSpinBox()
        self.min_thumb_width.setRange(50, 1000)
        self.min_thumb_width.setValue(config.MIN_THUMB_WIDTH)
        layout.addRow("Ancho Miniatura Mínimo:", self.min_thumb_width)

        self.num_thumbs = QtWidgets.QSpinBox()
        self.num_thumbs.setRange(1, 50)
        self.num_thumbs.setValue(config.NUM_THUMBS)
        layout.addRow("Número de Miniaturas:", self.num_thumbs)

        self.thumb_spacing = QtWidgets.QSpinBox()
        self.thumb_spacing.setRange(0, 100)
        self.thumb_spacing.setValue(config.THUMB_SPACING)
        layout.addRow("Espaciado Miniaturas:", self.thumb_spacing)

        self.control_width = QtWidgets.QSpinBox()
        self.control_width.setRange(100, 1000)
        self.control_width.setValue(config.CONTROL_WIDTH_ESTIMATE)
        layout.addRow("Estimación Ancho Control:", self.control_width)

        self.cache_size = QtWidgets.QSpinBox()
        self.cache_size.setRange(1, 500)
        self.cache_size.setValue(config.CACHE_SIZE)
        layout.addRow("Tamaño de Caché:", self.cache_size)

    def setup_tab_historial(self):
        layout = QtWidgets.QVBoxLayout(self.tab_historial)

        self.table_history = QtWidgets.QTableWidget(4, 3)
        self.table_history.setHorizontalHeaderLabels(["ID", "Fecha de Revisión", "Información"])
        self.table_history.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table_history.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_history.setWordWrap(True)
        self.table_history.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.ResizeToContents)

        history_data = [
            config.OVERWRITE_0,
            config.OVERWRITE_1,
            config.OVERWRITE_2,
            config.OVERWRITE_3
        ]

        for row, data in enumerate(history_data):
            self.table_history.setItem(row, 0, QtWidgets.QTableWidgetItem(str(data[0])))
            self.table_history.setItem(row, 1, QtWidgets.QTableWidgetItem(str(data[1])))
            self.table_history.setItem(row, 2, QtWidgets.QTableWidgetItem(str(data[2])))

        layout.addWidget(self.table_history)

    def browse_root(self):
        dir_path = QtWidgets.QFileDialog.getExistingDirectory(self, "Seleccionar Directorio Raíz", self.root_edit.text())
        if dir_path:
            self.root_edit.setText(dir_path)

    def browse_script(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Seleccionar Script Python", self.script_edit.text(), "Python files (*.py)")
        if file_path:
            self.script_edit.setText(file_path)

    def validate_ksize(self, value):
        if value % 2 == 0:
            self.ocr_denoise_ksize.setValue(value + 1)

    def save_and_close(self):
        data = {
            "BASE_INTERNAL_ROOT": self.root_edit.text(),
            "RENAME_DIALOG_SCRIPT": self.script_edit.text(),
            "OCR_SCALE": self.ocr_scale.value(),
            "OCR_USE_CLAHE": self.ocr_use_clahe.isChecked(),
            "OCR_CLAHE_CLIP": self.ocr_clahe_clip.value(),
            "OCR_DENOISE_KSIZE": self.ocr_denoise_ksize.value(),
            "OCR_DILATE_ITER": self.ocr_dilate_iter.value(),
            "OCR_INVERT": self.ocr_invert.isChecked(),
            "OCR_BINARIZE": self.ocr_binarize.isChecked(),
            "OCR_PSM": self.ocr_psm.value(),
            "OCR_LANG": self.ocr_lang.currentText(),
            "DEFAULT_THUMB_WIDTH": self.thumb_width.value(),
            "MIN_THUMB_WIDTH": self.min_thumb_width.value(),
            "NUM_THUMBS": self.num_thumbs.value(),
            "THUMB_SPACING": self.thumb_spacing.value(),
            "CONTROL_WIDTH_ESTIMATE": self.control_width.value(),
            "CACHE_SIZE": self.cache_size.value(),
            "OVERWRITE_HISTORY": [
                [int(self.table_history.item(0, 0).text()), self.table_history.item(0, 1).text(), self.table_history.item(0, 2).text()],
                [int(self.table_history.item(1, 0).text()), self.table_history.item(1, 1).text(), self.table_history.item(1, 2).text()],
                [int(self.table_history.item(2, 0).text()), self.table_history.item(2, 1).text(), self.table_history.item(2, 2).text()],
                [int(self.table_history.item(3, 0).text()), self.table_history.item(3, 1).text(), self.table_history.item(3, 2).text()],
            ]
        }

        config.save_config(data)
        config.reload_config()
        self.settings_saved.emit()
        self.accept()
