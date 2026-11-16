import os, re, struct, datetime, cv2, win32clipboard, subprocess, sys
from PyQt6 import QtCore, QtGui, QtWidgets
from settings_dialog import SettingsDialog
from file_table_widget import FileTableWidget
from smb_dialog import SMBDialog
import config
from utils import *
from infoutils import get_overwrite_data
from workframe_dialog import WorkframeDialog
from rename_dialog import RenameDialog
from lyric_vision_panel import LyricVisionPanel
from about_season_dialog import AboutSeasonDialog
from year_selector_bar import YearSelectorBar
from folder_selector_bar import FolderSelectorBar
from master_toolbar import MasterToolBar
import year_creator

class VideoEtude(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.lyric_mode = False
        self._workframe_dialogs = {}
        self._editor_splitter_active = False
        self.setWindowTitle("FrameEtude")
        self.resize(1300, 620)
        self._build_ui()
        
        # populate left panel combos
        try:
            self.populate_years()
            self.update_lyrics_check_button_visibility()
        except Exception:
            pass

    def _build_ui(self):
        # 1. LAYOUT PRINCIPAL VERTICAL (Ventana entera)
        w = QtWidgets.QWidget()
        self.setCentralWidget(w)
        self.main_layout = QtWidgets.QVBoxLayout(w)
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.main_layout.setSpacing(6)
        
        # ---------------- ARRIBA: MasterToolBar Global ----------------
        self.master_toolbar = MasterToolBar(self)
        
        self.master_toolbar.add_simplified_action("Settings", self.open_settings_dialog)
        self.master_toolbar.add_simplified_action("Open other video", self.open_video_dialog)
        self.master_toolbar.add_simplified_action("Refresh", self.rescan_current_master_folder)
        self.master_toolbar.add_simplified_action("Backup", self.run_backup_csv)
        self.master_toolbar.add_simplified_action("Etude", self.open_etude_file)
        self.master_toolbar.add_dropdown_button("Get Ov Reg",
            [
                ("Get Ov1 Reg", lambda: self.get_reg_ov_temp("1")),
                ("Get Ov2 Reg", lambda: self.get_reg_ov_temp("2")),
            ]
        )
        self.master_toolbar.add_simplified_action("Get Titles Ep", self.get_episode_titles_temp)
        self.master_toolbar.add_simplified_action("Gen Plan.md", self.phase_gen_exec)
        self.btn_check = self.master_toolbar.add_simplified_action(
            "Check MD", self.open_lyrics_manager, object_name="CheckMDButton", enabled=False
        )
        self.master_toolbar.add_dropdown_button("Overwrite",
            [
                ("Overwrite P", lambda: self.showOverwriteInfo("ov_0")),
                ("Overwrite I", lambda: self.showOverwriteInfo("ov_1")),
                ("Overwrite II", lambda: self.showOverwriteInfo("ov_2")),
                ("Overwrite III", lambda: self.showOverwriteInfo("ov_3")),
                ("Anachronic Overwrite", lambda: self.showOverwriteInfo(
                    "anachronic_overwriting", database_path=config.A_OVERWRITE_DATABASE,
                    label="Anachronic Overwrite",
                )),
            ]
        )
        self.action_load_selected = self.master_toolbar.add_simplified_action(
            "Load to Workframe", self.load_selected_file, enabled=False
        )
        self.master_toolbar.add_simplified_action("Check SMB", self.open_smb_dialog)
        self.master_toolbar.add_simplified_action("About", self.open_about_dialog)
        self.chk_lyric = self.master_toolbar.add_simplified_action(
            "View Lyrics?", self.on_lyric_checkbox_toggled, checkable=True, enabled=False
        )
        
        # Añadir la barra arriba de todo en la ventana principal
        self.main_layout.addWidget(self.master_toolbar)

        # ---------------- Panel principal: tabla + editor integrado opcional ----------------
        self.left_panel = QtWidgets.QWidget()
        self.left_panel.setMinimumWidth(400)
        left_layout = QtWidgets.QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(4, 4, 4, 4)
        left_layout.setSpacing(6)

        self.year_selector_bar = YearSelectorBar()
        self.year_selector_bar.yearSelected.connect(self.on_year_bar_selected)
        self.year_selector_bar.hiddenYearSelected.connect(self.on_hidden_year_selected)
        self.year_selector_bar.createNewYearRequested.connect(self.on_create_new_year_requested)

        self.folder_selector_bar = FolderSelectorBar()
        self.folder_selector_bar.folderSelected.connect(self.on_master_changed)
        self.folder_selector_bar.folderChanged.connect(
            lambda: self.load_year_data(self.year_selector_bar.current_year())
        )

        self.file_table = FileTableWidget()
        self.file_table.itemSelectionChanged.connect(self.on_file_selected)
        self.file_table.row_count_changed.connect(self.on_file_count_changed)

        files_row = QtWidgets.QHBoxLayout()
        files_row.setSpacing(6)
        files_row.addWidget(self.year_selector_bar)
        files_row.addWidget(self.folder_selector_bar)
        files_row.addWidget(self.file_table, 1)
        left_layout.addLayout(files_row, 1)

        # El editor de letras sigue integrado. El splitter solo existe visualmente
        # mientras ese editor está abierto; el visor de video usa ventanas propias.
        self.right_widget = QtWidgets.QWidget()
        self.right_stack = QtWidgets.QStackedLayout(self.right_widget)
        self.lyric_panel = LyricVisionPanel(self)
        self.right_stack.addWidget(self.lyric_panel)
        self.right_stack.setCurrentWidget(self.lyric_panel)
        self.right_widget.setMinimumWidth(0)

        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(6)
        self.splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #2b2b2b;
            }
            QSplitter::handle:hover {
                background-color: #05478a;
            }
        """)
        self.splitter.hide()
        self.main_layout.addWidget(self.left_panel, 1)

        # ---------------- ABAJO: Progress Row Global ----------------
        progress_row = QtWidgets.QHBoxLayout()
        progress_row.setContentsMargins(5, 5, 5, 5)
        progress_row.setSpacing(8)
        
        self.folder_count_label = QtWidgets.QLabel("0 MediaFiles")
        self.folder_count_label.setStyleSheet("""
            color: white;
            background: #4f4f4f;
            border-radius: 4px;
            padding: 4px 8px;
            font-style: italic;
        """)
        progress_row.addWidget(self.folder_count_label)
        
        self.metadata_progress_label = QtWidgets.QLabel("0/0")
        progress_row.addWidget(self.metadata_progress_label)

        self.metadata_progress_bar = QtWidgets.QProgressBar()
        self.metadata_progress_bar.setRange(0, 100)
        self.metadata_progress_bar.setValue(0)
        progress_row.addWidget(self.metadata_progress_bar, 1)
        
        # Añadir la barra de progreso abajo del todo en la ventana principal
        self.main_layout.addLayout(progress_row)
        
        self.file_table.set_progress_widgets(
            self.metadata_progress_bar,
            self.metadata_progress_label,
        )
        
        self.status = QtWidgets.QLabel("FrameEtude Loaded Resources")
        self.main_layout.addWidget(self.status)
        

    def showOverwriteInfo(self, key: str, database_path: str | None = None,
                          label: str = "Overwrite"):
        if database_path is None:
            times_num = get_overwrite_data(key)
        else:
            times_num = get_overwrite_data(
                key, database_path=database_path, database_label=label
            )
        QtWidgets.QMessageBox.information(
            self, f"{label} {times_num[0]} Review: {times_num[1]}", times_num[2]
        )

    # ---------------- Left panel helpers ----------------
    def populate_years(self, select_year_str: str = None):
        # Listar carpetas reales en BASE_INTERNAL_ROOT que sean años numéricos >= 2004
        years = []
        try:
            for name in os.listdir(config.BASE_INTERNAL_ROOT):
                if name.isdigit() and len(name) == 4 and int(name) >= 2004:
                    years.append(name)
            years.sort()
        except Exception:
            years = [str(y) for y in range(2004, datetime.date.today().year + 1)]

        self.year_selector_bar.set_years(years)

        target_year = select_year_str if select_year_str else (years[-1] if years else str(datetime.date.today().year))
        
        self.year_selector_bar.select_year(target_year, emit=False)
        self.load_year_data(target_year)
    
    def on_year_bar_selected(self, year: str):
        if not year:
            return
        self.load_year_data(year)
        
    def on_hidden_year_selected(self, year: str):
        self.year_selector_bar.select_year("", emit=False)
        self.load_year_data(year)
        
    def on_create_new_year_requested(self):
        # Get the highest year currently in the interface
        years = self.year_selector_bar.get_years()
        if not years:
            return

        last_year = max(years)
        next_year = int(last_year) + 1

        msg = f"el siguiente año es {next_year} y se creara con la estrucutura del año pasado, ¿Desea continuar?"
        confirm = QtWidgets.QMessageBox.question(
            self, "Crear nuevo año", msg,
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
        )

        if confirm == QtWidgets.QMessageBox.StandardButton.Yes:
            success, result = year_creator.create_new_year_folder(config.BASE_INTERNAL_ROOT, last_year)
            if success:
                self.populate_years(select_year_str=result)
            else:
                QtWidgets.QMessageBox.warning(self, "Error", result)
        
    def load_year_data(self, year: str):
        self.exit_lyric_mode(uncheck=True)
        self.chk_lyric.setEnabled(False)
        self.file_table.load_folder("")
        self.folder_selector_bar.set_folders([])
        self.btn_check.setEnabled(False)
        
        if not year or year == "(no encontrado)":
            return
        
        year_path = os.path.join(config.BASE_INTERNAL_ROOT, year)
        
        # buscar carpeta que contenga "___[" en su nombre
        found = None
        try:
            for name in os.listdir(year_path):
                full = os.path.join(year_path, name)
                if os.path.isdir(full) and "___[" in name:
                    found = full
                    break
        except Exception:
            found = None
        
        if not found:
            return
        
        try:
            hide_overwrite_1 = int(year) >= 2026
        except ValueError:
            hide_overwrite_1 = False

        self.file_table.set_overwrite_1_hidden(hide_overwrite_1)
        
        # listar subcarpetas de found
        try:
            subs = [os.path.join(found, d) for d in os.listdir(found) if os.path.isdir(os.path.join(found, d))]
            subs_sorted = sorted(subs, key=lambda x: os.path.basename(x))
            self.folder_selector_bar.set_folders(subs_sorted)
            if subs_sorted:
                self.folder_selector_bar.setCurrentRow(0)
        except Exception:
            pass

    def on_master_changed(self, path: str):
        self.exit_lyric_mode(uncheck=True)

        self.update_lyrics_check_button_visibility()

        if not path or path == '(no encontrado)':
            self.file_table.load_folder("")
            self.action_load_selected.setEnabled(False)
            self._sync_lyric_checkbox_for_folder("")
            return

        base = path
        if not os.path.isdir(base):
            base = os.path.dirname(path)

        self.file_table.load_folder(base)
        self.action_load_selected.setEnabled(False)
        self._sync_lyric_checkbox_for_folder(base)

    def rescan_current_master_folder(self):
        path = self.folder_selector_bar.current_folder_path()
        if not path or path == '(no encontrado)':
            return

        base = path
        if not os.path.isdir(base):
            base = os.path.dirname(path)

        self.file_table.invalidate_folder(base)
        self.on_master_changed(path)

    def open_etude_file(self):
        year = self.year_selector_bar.current_year()
        px = f"{int(year) - 2003:02d}"
        os.startfile(f"{'E:/_Internal'}/{year}/{px}. identity/{px}. le_etude.overwrite.xlsx")

    def phase_gen_exec(self):
        py_execute = sys.executable
        year = self.year_selector_bar.current_year()
        cur_fr_script = os.path.dirname(os.path.abspath(__file__))
        child_script = os.path.join(cur_fr_script, "phase_gen.pyw")
        CREATE_NO_WINDOW = 0x08000000
        
        subprocess.Popen(
            [py_execute, child_script, year],
            creationflags=CREATE_NO_WINDOW
        )

    def get_reg_ov_temp(self, ov_ver: str):
        py_execute = sys.executable
        cur_fr_script = os.path.dirname(os.path.abspath(__file__))
        child_script = os.path.join(cur_fr_script, "temp_ov_dtrng.pyw")
        year = self.year_selector_bar.current_year()
        CREATE_NO_WINDOW = 0x08000000

        subprocess.Popen(
            [py_execute, child_script, year, ov_ver],
            creationflags=CREATE_NO_WINDOW
        )

    def get_episode_titles_temp(self):
        py_execute = sys.executable  
        cur_fr_script = os.path.dirname(os.path.abspath(__file__))
        child_script = os.path.join(cur_fr_script, "temp_eps_list_get.pyw")
        year = self.year_selector_bar.current_year()
        CREATE_NO_WINDOW = 0x08000000

        subprocess.Popen(
            [py_execute, child_script, year],
            creationflags=CREATE_NO_WINDOW
        )

    def open_about_dialog(self):
        year = self.year_selector_bar.current_year().strip()
        if not year or year == "(no encontrado)":
            QtWidgets.QMessageBox.information(self, "About", "No hay un año válido seleccionado.")
            return

        master_path = self.folder_selector_bar.current_folder_path().strip()
        master_folder_name = ""
        if master_path and master_path != "(no encontrado)":
            master_folder_name = os.path.basename(master_path)

        dlg = AboutSeasonDialog(
            self,
            year=year,
            master_folder_name=master_folder_name,
        )
        dlg.exec()

    def on_file_selected(self):
        has_file = bool(self.file_table.current_file_path())
        self.action_load_selected.setEnabled(has_file)

        if self.lyric_mode and has_file:
            self.load_current_lyric_entry()
        
    def load_selected_file(self):
        self.exit_lyric_mode(uncheck=True)
        video_path = self.file_table.current_file_path()
        if not video_path:
            return

        if not os.path.exists(video_path):
            QtWidgets.QMessageBox.critical(self, 'Error', f'No se encontró: {video_path}')
            return

        self.open_workframe(video_path)

    
    def rescan_selected_row(self):
        row = self.file_table.currentRow()

        if row < 0:
            return

        video_path = self.file_table.current_file_path()

        if not video_path:
            return

        try:
            folder = os.path.dirname(video_path)

            if folder in self.file_table._folder_cache:
                cached_rows = self.file_table._folder_cache[folder]

                for i, cached in enumerate(cached_rows):
                    if cached.get("full_path") == video_path:
                        cached_rows[i] = self.file_table._read_file_row(video_path)
                        row_data = cached_rows[i]
                        break
                else:
                    row_data = self.file_table._read_file_row(video_path)
            else:
                row_data = self.file_table._read_file_row(video_path)

            for column, (_, key) in enumerate(self.file_table.COLUMNS):
                item = self.file_table.item(row, column)
                if item is None:
                    item = QtWidgets.QTableWidgetItem()
                    self.file_table.setItem(row, column, item)

                value = str(row_data.get(key, ""))
                if key == "duration" and not value and item.text():
                    value = item.text()

                item.setText(value)

                if key == "filename":
                    item.setData(
                        QtCore.Qt.ItemDataRole.UserRole,
                        row_data.get("full_path", "")
                    )

        except Exception:
            pass

    # ---------------- UI <-> Worker lifecycle ----------------
    def open_workframe(self, video_path: str):
        if not video_path or not os.path.isfile(video_path):
            return

        key = os.path.normcase(os.path.abspath(video_path))
        existing = self._workframe_dialogs.get(key)
        if existing is not None:
            existing.showNormal()
            existing.raise_()
            existing.activateWindow()
            return

        try:
            dialog = WorkframeDialog(video_path, self)
        except Exception as error:
            QtWidgets.QMessageBox.critical(
                self, "Workframe", f"No se pudo abrir el video.\n\n{error}"
            )
            return

        self._workframe_dialogs[key] = dialog
        dialog.destroyed.connect(
            lambda _object=None, path_key=key: self._workframe_dialogs.pop(path_key, None)
        )
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def open_video_dialog(self):
        self.exit_lyric_mode(uncheck=True)
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open Video", "", "Video files (*.mp4 *.avi *.mov *.mkv *.wmv *.flv)"
        )
        if path:
            self.open_workframe(path)

    def open_rename_dialog(self, video_path: str):
        if not video_path or not os.path.isfile(video_path):
            return

        try:
            self._rename_dialog = RenameDialog(video_path, self)
            self._rename_dialog.setWindowFlag(
                QtCore.Qt.WindowType.Window, True
            )
            if config.ICON_PATH and os.path.isfile(config.ICON_PATH):
                self._rename_dialog.setWindowIcon(QtGui.QIcon(config.ICON_PATH))
            self._rename_dialog.show()
            self._rename_dialog.raise_()
            self._rename_dialog.activateWindow()
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Rename dialog",
                f"No se pudo abrir el editor de nombre y metadatos.\n\n{e}",
            )

    def edit_selected_metadata(self):
        video_path = self.file_table.current_file_path()
        if not video_path:
            return
        self.open_rename_dialog(video_path)

    def ensure_workframe_visible(self):
        self._set_workframe_visible(True)

    def _set_workframe_visible(self, visible: bool):
        if visible:
            if not self._editor_splitter_active:
                self.main_layout.removeWidget(self.left_panel)
                self.splitter.addWidget(self.left_panel)
                self.splitter.addWidget(self.right_widget)
                self.main_layout.insertWidget(1, self.splitter, 1)
                self._editor_splitter_active = True

            self.right_widget.show()
            self.splitter.show()
            total_width = max(self.splitter.width(), self.width() - 24)
            left_width = min(660, max(400, int(total_width * 0.55)))
            self.splitter.setSizes([left_width, max(360, total_width - left_width)])
        else:
            if not self._editor_splitter_active:
                return

            self.main_layout.removeWidget(self.splitter)
            self.splitter.hide()
            self.left_panel.setParent(self.centralWidget())
            self.right_widget.hide()
            self.right_widget.setParent(self.centralWidget())
            self.main_layout.insertWidget(1, self.left_panel, 1)
            self._editor_splitter_active = False

    def _get_valid_lyrics_base_path(self):
        path = self.folder_selector_bar.current_folder_path().strip()
        
        # Ignorar rutas vacías o el placeholder de error
        if not path or path == '(no encontrado)':
            return None

        # Obtener el directorio base
        base = path if os.path.isdir(path) else os.path.dirname(path)
        if not base:
            return None

        # Verificar si el nombre de la carpeta termina en los sufijos permitidos
        folder_name = os.path.basename(base.rstrip("\\/")).lower()
        
        if folder_name.endswith(config.VALID_FOLDER_SUFFIXES):
            return base
            
        return None

    def update_lyrics_check_button_visibility(self):
        is_valid = self._get_valid_lyrics_base_path() is not None
        self.btn_check.setEnabled(is_valid)

    def open_lyrics_manager(self):
        base = self._get_valid_lyrics_base_path()
        if not base:
            return

        script_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(script_dir, "lirycs_mgr.pyw") 

        if not os.path.exists(script_path):
            QtWidgets.QMessageBox.critical(self, "Error", f"No se encontró el archivo:\n{script_path}")
            return

        pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        launcher = pythonw if os.path.exists(pythonw) else sys.executable

        subprocess.Popen([launcher, script_path, base], cwd=script_dir, close_fds=True)

    def current_smb_folder(self):
        folder = self.file_table.current_folder_path()
        if folder:
            return folder
        video_path = self.file_table.current_file_path()
        return os.path.dirname(video_path) if video_path else ""

    def open_smb_dialog(self):
        folder = self.current_smb_folder()
        if not folder:
            QtWidgets.QMessageBox.information(self, "Check SMB", "No hay carpeta activa.")
            return

        dialog = SMBDialog(folder, self)
        dialog.exec()

    def on_file_count_changed(self, count):
        self.folder_count_label.setText(f"{count} MediaFiles")

    def _current_master_folder(self) -> str:
        path = self.folder_selector_bar.current_folder_path().strip()
        if not path or path == '(no encontrado)':
            return ""
        return path if os.path.isdir(path) else os.path.dirname(path)

    def _folder_is_vocal(self, folder: str) -> bool:
        if not folder:
            return False
        return os.path.basename(folder.rstrip("\\/")).lower().endswith("vocals")

    def _sync_lyric_checkbox_for_folder(self, folder: str):
        show = self._folder_is_vocal(folder)

        if not show:
            self.exit_lyric_mode(uncheck=True)
            self.chk_lyric.blockSignals(True)
            self.chk_lyric.setChecked(False)
            self.chk_lyric.blockSignals(False)
            self.chk_lyric.setEnabled(False)
            return

        self.chk_lyric.setEnabled(True)

    def on_lyric_checkbox_toggled(self, checked: bool):
        if checked:
            if not self._folder_is_vocal(self._current_master_folder()):
                self.chk_lyric.blockSignals(True)
                self.chk_lyric.setChecked(False)
                self.chk_lyric.blockSignals(False)
                return
            self.enter_lyric_mode()
        else:
            self.exit_lyric_mode(uncheck=False)

    def enter_lyric_mode(self):
        folder = self._current_master_folder()
        if not self._folder_is_vocal(folder):
            self.exit_lyric_mode(uncheck=True)
            return

        if self.file_table.rowCount() <= 0:
            self.lyric_mode = True
            self.lyric_panel.clear()
            self.right_stack.setCurrentWidget(self.lyric_panel)
            self.ensure_workframe_visible()
            return

        if self.file_table.currentRow() < 0:
            self.file_table.setCurrentCell(0, 0)

        self.lyric_mode = True
        self.ensure_workframe_visible()
        self.right_stack.setCurrentWidget(self.lyric_panel)
        self.load_current_lyric_entry()

    def exit_lyric_mode(self, uncheck: bool = False):
        self.lyric_mode = False

        if hasattr(self, "right_stack"):
            self.right_stack.setCurrentWidget(self.lyric_panel)
        self._set_workframe_visible(False)

        if uncheck and hasattr(self, "chk_lyric"):
            self.chk_lyric.blockSignals(True)
            self.chk_lyric.setChecked(False)
            self.chk_lyric.blockSignals(False)

    def _selected_row_index_for_lyrics(self) -> int:
        row = self.file_table.currentRow()
        if row < 0 and self.file_table.rowCount() > 0:
            row = 0
            self.file_table.setCurrentCell(0, 0)
        return row

    def load_current_lyric_entry(self):
        if not self.lyric_mode:
            return

        row = self._selected_row_index_for_lyrics()
        if row < 0:
            self.lyric_panel.clear()
            return

        video_path = self.file_table.current_file_path()
        if not video_path:
            return

        indirect_path = self.lyric_panel.build_indirect_path(video_path)
        total = self.file_table.rowCount()
        name = os.path.basename(indirect_path)

        if os.path.exists(indirect_path):
            try:
                text = self.lyric_panel.read_utf8(indirect_path)
                self.lyric_panel.set_document(video_path, indirect_path, text, row + 1, total)
            except Exception:
                self.lyric_panel.set_missing_document(video_path, indirect_path, row + 1, total)
        else:
            self.lyric_panel.set_missing_document(video_path, indirect_path, row + 1, total)

    def next_lyric_entry(self):
        if self.file_table.rowCount() <= 0:
            return

        row = self._selected_row_index_for_lyrics()
        next_row = 0 if row + 1 >= self.file_table.rowCount() else row + 1
        self.file_table.setCurrentCell(next_row, 0)
        self.load_current_lyric_entry()
        
    def prev_lyric_entry(self):
        if self.file_table.rowCount() <= 0:
            return

        row = self._selected_row_index_for_lyrics()
        # Si la fila actual es 0 o menor (ninguna selección), va a la última fila, si no, resta 1.
        prev_row = self.file_table.rowCount() - 1 if row <= 0 else row - 1
        
        self.file_table.setCurrentCell(prev_row, 0)
        self.load_current_lyric_entry()
    
    def run_backup_csv(self):
        py_execute = sys.executable
        cur_fr_script = os.path.dirname(os.path.abspath(__file__))
        child_script = os.path.join(cur_fr_script, "backup_csv.pyw")
        CREATE_NO_WINDOW = 0x08000000
        
        subprocess.Popen(
            [py_execute, child_script],
            creationflags=CREATE_NO_WINDOW
        )
    
    def open_settings_dialog(self):
        dlg = SettingsDialog(self)
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.file_table.set_audio_check_enabled(config.CHECK_AUDIO)
            for workframe in tuple(self._workframe_dialogs.values()):
                if workframe.worker is not None:
                    workframe.worker.cache_size = config.CACHE_SIZE

    def closeEvent(self, event):
        for workframe in tuple(self._workframe_dialogs.values()):
            try:
                workframe.close()
            except Exception:
                pass
        try:
            self.file_table.stop_folder_loading()
        except Exception:
            pass
        super().closeEvent(event)
