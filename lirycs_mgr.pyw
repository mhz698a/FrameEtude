import os
import sys
import ctypes
import platform
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QFileDialog, QMessageBox,
    QHBoxLayout, QVBoxLayout, QWidget, QPushButton, QLabel,
    QListWidget, QSizePolicy
)
from PyQt6.QtGui import (
    QAction, QActionGroup, QFont, QIcon, QKeySequence, QShortcut,
    QPalette, QColor
)
from PyQt6.QtCore import Qt
from config import ID_APP_LIRYCS, ICON_PATH_LIRYCS

ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(ID_APP_LIRYCS)


class LirycsBook(QMainWindow):
    LIST_WIDTH = 350  # ancho fijo del panel de lista

    def __init__(self):
        super().__init__()

        if os.path.exists(ICON_PATH_LIRYCS):
            self.setWindowIcon(QIcon(ICON_PATH_LIRYCS))

        self.setWindowTitle("LyricsBook")
        self.resize(1200, 600)
        self.txt_files = []
        self.current_index = 0
        self.current_file = None
        self.text_modified = False
        self.updating_list = False

        # Menú principal
        menu_bar = self.menuBar()
        archivo_menu = menu_bar.addMenu("Archivo")

        abrir_carpeta_action = QAction("Abrir carpeta", self)
        abrir_carpeta_action.triggered.connect(self.select_folder)
        archivo_menu.addAction(abrir_carpeta_action)

        abrir_archivo_action = QAction("Abrir archivo", self)
        abrir_archivo_action.triggered.connect(self.select_file)
        archivo_menu.addAction(abrir_archivo_action)

        archivo_menu.addSeparator()

        guardar_action = QAction("Guardar", self)
        guardar_action.setShortcut(QKeySequence("Ctrl+S"))
        guardar_action.triggered.connect(self.save_file)
        archivo_menu.addAction(guardar_action)

        guardar_como_action = QAction("Guardar como...", self)
        guardar_como_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        guardar_como_action.triggered.connect(self.save_file_as)
        archivo_menu.addAction(guardar_como_action)

        archivo_menu.addSeparator()
        tema_menu = archivo_menu.addMenu("Tema")
        tema_oscuro_action = QAction("Oscuro", self, checkable=True)
        tema_claro_action = QAction("Claro", self, checkable=True)
        tema_sistema_action = QAction("Sistema", self, checkable=True)
        tema_group = QActionGroup(self)
        for act in (tema_oscuro_action, tema_claro_action, tema_sistema_action):
            tema_group.addAction(act)
        tema_oscuro_action.setChecked(True)
        tema_menu.addAction(tema_oscuro_action)
        tema_menu.addAction(tema_claro_action)
        tema_menu.addAction(tema_sistema_action)
        tema_oscuro_action.triggered.connect(lambda: self.set_theme('dark'))
        tema_claro_action.triggered.connect(lambda: self.set_theme('light'))
        tema_sistema_action.triggered.connect(lambda: self.set_theme('system'))

        archivo_menu.addSeparator()
        copiar_nombre_action = QAction("Copy Filename", self)
        copiar_nombre_action.triggered.connect(self.copiar_nombre_sin_extension)
        archivo_menu.addAction(copiar_nombre_action)
        archivo_menu.addSeparator()
        salir_action = QAction("Salir", self)
        salir_action.triggered.connect(self.close)
        archivo_menu.addAction(salir_action)

        # Edit menu (soporte básico de edición)
        edit_menu = menu_bar.addMenu("Editar")
        undo_action = QAction("Deshacer", self)
        undo_action.setShortcut(QKeySequence("Ctrl+Z"))
        undo_action.triggered.connect(lambda: self.text.undo())
        edit_menu.addAction(undo_action)

        redo_action = QAction("Rehacer", self)
        redo_action.setShortcut(QKeySequence("Ctrl+Y"))
        redo_action.triggered.connect(lambda: self.text.redo())
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()

        cut_action = QAction("Cortar", self)
        cut_action.setShortcut(QKeySequence("Ctrl+X"))
        cut_action.triggered.connect(lambda: self.text.cut())
        edit_menu.addAction(cut_action)

        copy_action = QAction("Copiar", self)
        copy_action.setShortcut(QKeySequence("Ctrl+C"))
        copy_action.triggered.connect(lambda: self.text.copy())
        edit_menu.addAction(copy_action)

        paste_action = QAction("Pegar", self)
        paste_action.setShortcut(QKeySequence("Ctrl+V"))
        paste_action.triggered.connect(lambda: self.text.paste())
        edit_menu.addAction(paste_action)

        # ---- Layout general: lista izquierda + editor ----
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(8)

        # Panel de lista de archivos (ahora a la izquierda) — ancho fijo
        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self.on_list_item_clicked)
        self.list_widget.itemActivated.connect(self.on_list_item_activated)
        self.list_widget.setVisible(False)

        # Mantener ancho fijo y política de tamaño adecuada
        self.list_widget.setFixedWidth(self.LIST_WIDTH)
        self.list_widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        # Usar barra de scroll nativa (política por defecto)
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        main_layout.addWidget(self.list_widget, stretch=0)  # stretch 0 -> mantiene tamaño fijo

        # Panel derecho: editor y barra inferior
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Editor
        self.text = QTextEdit()
        self.text.setFont(QFont("Segoe UI Emoji", 12))
        self.text.textChanged.connect(self.on_text_modified)
        self.text.cursorPositionChanged.connect(self.update_status)
        # Asegurarnos de que use scrollbar nativo
        self.text.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        right_layout.addWidget(self.text)

        # Barra inferior
        status_layout = QHBoxLayout()
        self.status_label = QLabel("Línea: 1, Columna: 0")
        status_layout.addWidget(self.status_label, stretch=1)
        self.btn_paste = QPushButton("Paste")
        self.btn_paste.clicked.connect(self.paste_text)
        status_layout.addWidget(self.btn_paste)
        self.btn_save = QPushButton("Save")
        self.btn_save.clicked.connect(self.save_file)
        self.btn_prev = QPushButton("Prev")
        self.btn_prev.clicked.connect(self.prev_file)
        self.btn_next = QPushButton("Next")
        self.btn_next.clicked.connect(self.next_file)
        for btn in (self.btn_save, self.btn_prev, self.btn_next):
            status_layout.addWidget(btn)
        right_layout.addLayout(status_layout)

        main_layout.addWidget(right_widget, stretch=1)

        # Estado
        self.text.document().modificationChanged.connect(self.on_text_modified)
        self.text.setAcceptRichText(False)

        # Atajos con QShortcut
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self.save_file)
        QShortcut(QKeySequence("Alt+Left"), self).activated.connect(self.prev_file)
        QShortcut(QKeySequence("Alt+Right"), self).activated.connect(self.next_file)
        QShortcut(QKeySequence("Alt+Shift+C"), self).activated.connect(self.copiar_nombre_sin_extension)

    # === Funciones de apertura ===
    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Selecciona una carpeta")
        if folder:
            self.load_txt_files(folder)

    def select_file(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Abrir archivo", filter="Todos los archivos (*)")
        if filename:
            self.txt_files = [filename]
            self.current_index = 0
            self.list_widget.clear()
            self.list_widget.setVisible(False)
            self.open_file(filename)

    def load_txt_files(self, folder):
        self.txt_files = [
            os.path.join(folder, f)
            for f in os.listdir(folder)
            if f.lower().endswith(('.txt', '.md', '.ini', '.py', '.pyw', '.yaml', '.yml', '.html', '.htm'))
        ]
        self.txt_files.sort()
        self.current_index = 0
        self.updating_list = True
        self.list_widget.clear()
        for p in self.txt_files:
            self.list_widget.addItem(os.path.basename(p))
        # siempre mantenemos el ancho fijo; solo cambiamos visibilidad
        self.list_widget.setVisible(len(self.txt_files) > 0)
        self.updating_list = False

        if self.txt_files:
            self.open_file(self.txt_files[0])
        else:
            self.current_file = None
            self.text.blockSignals(True)
            self.text.clear()
            self.text.blockSignals(False)
            self.update_status()
            self.setWindowTitle("LyricsBook")

    # === Operaciones con archivos ===
    def open_file(self, filepath):
        if self.text_modified and not self.ask_save_changes():
            return
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            QMessageBox.warning(self, "Error al abrir", f"No se pudo abrir el archivo:\n{e}")
            return

        self.text.blockSignals(True)
        self.text.setPlainText(content)
        self.text.blockSignals(False)
        self.current_file = filepath
        self.text.document().setModified(False)
        self.text_modified = False

        if filepath in self.txt_files:
            idx = self.txt_files.index(filepath)
            self.current_index = idx
            if not self.updating_list:
                self.updating_list = True
                self.list_widget.setCurrentRow(idx)
                self.updating_list = False
        else:
            # si abrimos un archivo suelto, ocultamos la lista pero no cambiamos su ancho
            self.list_widget.setVisible(False)
            self.txt_files = [filepath]
            self.current_index = 0

        self.update_status()
        self.setWindowTitle(f"LyricsBook - {os.path.basename(filepath)}")

    def save_file(self):
        if not self.current_file:
            return self.save_file_as()
        try:
            with open(self.current_file, 'w', encoding='utf-8') as f:
                f.write(self.text.toPlainText())
            self.text.document().setModified(False)
            self.text_modified = False
            self.update_status()
        except Exception as e:
            QMessageBox.warning(self, "Error al guardar", f"No se pudo guardar el archivo:\n{e}")

    def save_file_as(self):
        suggested_name = os.path.basename(self.current_file) if self.current_file else ""
        filename, _ = QFileDialog.getSaveFileName(self, "Guardar como", suggested_name, "Text files (*.txt);;All files (*)")
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.text.toPlainText())
                self.current_file = filename
                # si se guardó en la misma carpeta con lista cargada, recargar lista
                if self.txt_files and os.path.dirname(filename) == (os.path.dirname(self.txt_files[0]) if self.txt_files else None):
                    self.load_txt_files(os.path.dirname(filename))
                    if filename in self.txt_files:
                        self.current_index = self.txt_files.index(filename)
                self.text.document().setModified(False)
                self.text_modified = False
                self.update_status()
                self.setWindowTitle(f"TXT-Book Editor - {os.path.basename(filename)}")
            except Exception as e:
                QMessageBox.warning(self, "Error al guardar", f"No se pudo guardar el archivo:\n{e}")

    def prev_file(self):
        if self.txt_files and self.current_index > 0:
            if self.text_modified and not self.ask_save_changes():
                return
            self.current_index -= 1
            self.open_file(self.txt_files[self.current_index])

    def next_file(self):
        if self.txt_files and self.current_index < len(self.txt_files) - 1:
            if self.text_modified and not self.ask_save_changes():
                return
            self.current_index += 1
            self.open_file(self.txt_files[self.current_index])

    # === utilidades ===
    def ask_save_changes(self):
        if not self.text_modified:
            return True
        res = QMessageBox.question(
            self, "Guardar cambios",
            "¿Deseas guardar los cambios antes de continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
        )
        if res == QMessageBox.StandardButton.Cancel:
            return False
        if res == QMessageBox.StandardButton.Yes:
            self.save_file()
        return True

    def closeEvent(self, event):
        if self.text_modified:
            res = QMessageBox.question(
                self, "Guardar cambios",
                "¿Deseas guardar los cambios antes de salir?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            if res == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
            if res == QMessageBox.StandardButton.Yes:
                self.save_file()
        event.accept()

    def update_status(self):
        cursor = self.text.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.columnNumber()
        total = len(self.txt_files)
        actual = self.current_index + 1 if total > 0 else 0
        archivo_info = f"Archivo: {actual:02}/{total:02}" if total > 0 else "Archivo: 00/00"
        nombre = os.path.basename(self.current_file) if self.current_file else ""
        self.status_label.setText(f"Línea: {line}, Columna: {col}    {archivo_info}    {nombre}")

    def on_text_modified(self):
        self.text_modified = self.text.document().isModified()

    def set_theme(self, mode):
        """
        Usa QPalette para evitar tocar estilos de scrollbars. Mantiene apariencia
        oscura/clara con scrollbars nativos del sistema.
        """
        app = QApplication.instance()
        if not app:
            return

        pal = QPalette()

        if mode == 'dark':
            # palette basada en tonos oscuros
            pal.setColor(QPalette.ColorRole.Window, QColor("#232629"))
            pal.setColor(QPalette.ColorRole.WindowText, QColor("#f0f0f0"))
            pal.setColor(QPalette.ColorRole.Base, QColor("#1e1f21"))
            pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#2a2b2d"))
            pal.setColor(QPalette.ColorRole.Text, QColor("#f0f0f0"))
            pal.setColor(QPalette.ColorRole.Button, QColor("#333333"))
            pal.setColor(QPalette.ColorRole.ButtonText, QColor("#f0f0f0"))
            pal.setColor(QPalette.ColorRole.Highlight, QColor("#3a6ea5"))
            pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        elif mode == 'light':
            pal = QApplication().style().standardPalette()
        elif mode == 'system':
            # intentar detectar modo del sistema en Windows; si falla -> light
            if platform.system() == 'Windows':
                try:
                    import winreg
                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                        r"Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize") as key:
                        apps_use_light = winreg.QueryValueEx(key, "AppsUseLightTheme")[0]
                    if apps_use_light == 0:
                        self.set_theme('dark')
                        return
                    else:
                        self.set_theme('light')
                        return
                except Exception:
                    pal = QApplication().style().standardPalette()
            else:
                pal = QApplication().style().standardPalette()

        app.setPalette(pal)

    def paste_text(self):
        QApplication.clipboard()
        self.text.insertPlainText(QApplication.clipboard().text())

    def copiar_nombre_sin_extension(self):
        if self.current_file:
            nombre = os.path.splitext(os.path.basename(self.current_file))[0]
            QApplication.clipboard().setText(nombre)

    def on_list_item_clicked(self, item):
        if self.updating_list:
            return
        idx = self.list_widget.row(item)
        if idx == self.current_index:
            return
        if self.text_modified and not self.ask_save_changes():
            self.updating_list = True
            self.list_widget.setCurrentRow(self.current_index)
            self.updating_list = False
            return
        self.current_index = idx
        self.open_file(self.txt_files[idx])

    def on_list_item_activated(self, item):
        # activación por teclado (Enter) o doble-click
        self.on_list_item_clicked(item)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = LirycsBook()
    # tema por defecto
    editor.set_theme('dark')

    if len(sys.argv) > 1:
        path_arg = sys.argv[1]
        if os.path.isdir(path_arg):
            editor.load_txt_files(path_arg)
            editor.list_widget.setVisible(len(editor.txt_files) > 0)
        elif os.path.isfile(path_arg):
            editor.txt_files = [path_arg]
            editor.current_index = 0
            editor.list_widget.clear()
            editor.list_widget.setVisible(False)
            editor.open_file(path_arg)
        else:
            QMessageBox.warning(None, "Ruta no válida", f"No se encontró la ruta especificada:\n{path_arg}")
    else:
        editor.list_widget.setVisible(False)

    editor.show()
    sys.exit(app.exec())
