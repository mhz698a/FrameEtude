import os
import shutil
from PyQt6 import QtCore, QtGui, QtWidgets

class FolderSelectorBar(QtWidgets.QListWidget):
    folderSelected = QtCore.pyqtSignal(str)
    folderChanged = QtCore.pyqtSignal() # To signal that folders were created/renamed/deleted

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(110)
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.itemSelectionChanged.connect(self._emit_selection)
        
        self.setStyleSheet("""
            QListWidget {
                background-color: #121212;
                border: 1px solid #2b2b2b;
                color: #e0e0e0;
            }
            QListWidget::item:selected {
                background-color: #0078d7;
                color: white;
            }
        """)

    def set_folders(self, folder_paths: list[str]):
        self.blockSignals(True)
        self.clear()
        for path in folder_paths:
            name = os.path.basename(path.rstrip("\\/"))
            item = QtWidgets.QListWidgetItem(name)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, path)
            self.addItem(item)
        self.blockSignals(False)

    def select_folder(self, path: str):
        for i in range(self.count()):
            item = self.item(i)
            if item.data(QtCore.Qt.ItemDataRole.UserRole) == path:
                self.setCurrentItem(item)
                return

    def current_folder_path(self) -> str:
        item = self.currentItem()
        if item:
            return item.data(QtCore.Qt.ItemDataRole.UserRole)
        return ""

    def _emit_selection(self):
        path = self.current_folder_path()
        if path:
            self.folderSelected.emit(path)

    def show_context_menu(self, pos: QtCore.QPoint):
        item = self.itemAt(pos)
        menu = QtWidgets.QMenu(self)
        
        # We need at least one folder in the list to have a parent directory to create a new folder in,
        # or we need to know the base path. 
        # Usually, this list is populated within a year's "found" path.
        
        create_action = menu.addAction("Crear una nueva carpeta aqui")
        create_action.triggered.connect(lambda: self._create_folder(item))
        
        if item:
            path = item.data(QtCore.Qt.ItemDataRole.UserRole)
            
            rename_action = menu.addAction("Renombrar esta carpeta")
            rename_action.triggered.connect(lambda: self._rename_folder(item))

            copy_name_action = menu.addAction("Copy folder name")
            copy_name_action.triggered.connect(lambda: QtWidgets.QApplication.clipboard().setText(os.path.basename(path.rstrip("\\/"))))

            copy_path_action = menu.addAction("Copy folder path")
            copy_path_action.triggered.connect(lambda: QtWidgets.QApplication.clipboard().setText(path))
            
            delete_action = menu.addAction("Eliminar esta carpeta")
            is_empty = self._is_folder_empty_for_delete(path)
            delete_action.setEnabled(is_empty)
            delete_action.triggered.connect(lambda: self._delete_folder(item))
            
            open_action = menu.addAction("Abrir esta carpeta en el explorador")
            open_action.triggered.connect(lambda: os.startfile(path))
            
        menu.addSeparator()
        refresh_action = menu.addAction("Refresh master")
        refresh_action.triggered.connect(lambda: self.folderChanged.emit())

        menu.exec(self.mapToGlobal(pos))

    def _is_folder_empty_for_delete(self, path: str) -> bool:
        try:
            items = os.listdir(path)
            for item in items:
                full_path = os.path.join(path, item)
                if os.path.isdir(full_path):
                    return False # Has subfolders
                if item.lower() not in ["desktop.ini", "thumbs.db"]:
                    return False # Has other files
            return True
        except Exception:
            return False

    def _create_folder(self, item):
        # If item is None, we use the parent of the first item if exists
        base_dir = ""
        if item:
            base_dir = os.path.dirname(item.data(QtCore.Qt.ItemDataRole.UserRole))
        elif self.count() > 0:
            base_dir = os.path.dirname(self.item(0).data(QtCore.Qt.ItemDataRole.UserRole))
        
        if not base_dir:
            return

        name, ok = QtWidgets.QInputDialog.getText(self, "Nueva Carpeta", "Nombre de la carpeta:")
        if ok and name:
            new_path = os.path.join(base_dir, name)
            try:
                os.makedirs(new_path, exist_ok=False)
                self.folderChanged.emit()
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", f"No se pudo crear la carpeta: {e}")

    def _rename_folder(self, item):
        old_path = item.data(QtCore.Qt.ItemDataRole.UserRole)
        old_name = os.path.basename(old_path)
        base_dir = os.path.dirname(old_path)
        
        new_name, ok = QtWidgets.QInputDialog.getText(self, "Renombrar Carpeta", "Nuevo nombre:", text=old_name)
        if ok and new_name and new_name != old_name:
            new_path = os.path.join(base_dir, new_name)
            try:
                os.rename(old_path, new_path)
                self.folderChanged.emit()
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", f"No se pudo renombrar la carpeta: {e}")

    def _delete_folder(self, item):
        path = item.data(QtCore.Qt.ItemDataRole.UserRole)
        confirm = QtWidgets.QMessageBox.question(
            self, "Eliminar Carpeta", 
            f"¿Estás seguro de que deseas eliminar la carpeta '{os.path.basename(path)}'?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
        )
        if confirm == QtWidgets.QMessageBox.StandardButton.Yes:
            try:
                # Since we checked it's "empty" (only desktop.ini/thumbs.db), 
                # we can use shutil.rmtree or just os.rmdir if we delete those files first.
                # User said "eliminar esta carpeta (desabilitar si no esta vacia)", 
                # usually this implies it might have those excluded files.
                shutil.rmtree(path)
                self.folderChanged.emit()
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", f"No se pudo eliminar la carpeta: {e}")
