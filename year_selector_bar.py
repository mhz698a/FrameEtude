from __future__ import annotations

import datetime

from PyQt6 import QtCore, QtWidgets


class YearSelectorBar(QtWidgets.QTableWidget):
    yearSelected = QtCore.pyqtSignal(str)
    hiddenYearSelected = QtCore.pyqtSignal(str)
    createNewYearRequested = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMaximumWidth(100)
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self._years: list[str] = []
        self._cell_width = 30
        self._cell_height = 24

        self.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectItems)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.setShowGrid(True)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setVisible(False)

        self.setStyleSheet("""
        QTableWidget::item:selected {
            background-color: #0078d7;
            color: white;
        }
        QTableWidget::item:selected:active {
            background-color: #0078d7;
            color: white;
        }
        QTableWidget::item:selected:!active {
            background-color: #0078d7;
            color: white;
        }
        """)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )

        self.itemSelectionChanged.connect(self._emit_selection)

    def sizeHint(self):
        return QtCore.QSize(180, 240)

    def set_years(self, years: list[str]) -> None:
        self._years = [str(y) for y in years]
        self._rebuild()

    def select_year(self, year: str, emit: bool = False) -> None:
        if not year:
            self.clearSelection()
            self.setCurrentItem(None)
            return

        year = str(year)

        for row in range(self.rowCount()):
            for col in range(self.columnCount()):
                item = self.item(row, col)
                if item and item.text() == year:
                    old = self.blockSignals(True)
                    try:
                        self.setCurrentItem(item)
                        self.scrollToItem(
                            item,
                            QtWidgets.QAbstractItemView.ScrollHint.PositionAtCenter,
                        )
                    finally:
                        self.blockSignals(old)

                    if emit:
                        self.yearSelected.emit(year)
                    return

    def current_year(self) -> str:
        item = self.currentItem()
        return item.text() if item else ""

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._rebuild(preserve=self.current_year())

    def _emit_selection(self) -> None:
        item = self.currentItem()
        if item:
            self.yearSelected.emit(item.text())

    def _show_context_menu(self, pos: QtCore.QPoint) -> None:
        menu = QtWidgets.QMenu(self)

        hidden_years_menu = menu.addMenu("Seleccionar años ocultos")
        for y in ["1999", "2000", "2001", "2002", "2003"]:
            action = hidden_years_menu.addAction(y)
            action.triggered.connect(lambda checked, year=y: self.hiddenYearSelected.emit(year))

        create_action = menu.addAction("Crear nuevo año")
        create_action.triggered.connect(self.createNewYearRequested.emit)

        menu.exec(self.mapToGlobal(pos))

    def _rebuild(self, preserve: str = "", lim_col = True) -> None:
        years = self._years[:]

        if not years:
            old = self.blockSignals(True)
            try:
                self.clear()
                self.setRowCount(0)
                self.setColumnCount(0)
            finally:
                self.blockSignals(old)
            return

        viewport_width = max(1, self.viewport().width())
        cols = max(1, viewport_width // self._cell_width) if lim_col is False else 2
        rows = max(1, (len(years) + cols - 1) // cols)

        old = self.blockSignals(True)
        try:
            self.clear()
            self.setRowCount(rows)
            self.setColumnCount(cols if lim_col is False else 2)

            if lim_col:
                col_width = max(1, viewport_width // 2)
                for col in range(2):
                    self.setColumnWidth(col, col_width)
            else:
                col_width = max(self._cell_width, viewport_width // cols)
                for col in range(cols):
                    self.setColumnWidth(col, col_width)

            for row in range(rows):
                self.setRowHeight(row, self._cell_height)

            idx = 0
            for row in range(rows):
                for col in range(cols):
                    if idx >= len(years):
                        break

                    item = QtWidgets.QTableWidgetItem(years[idx])
                    item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                    item.setFlags(
                        QtCore.Qt.ItemFlag.ItemIsSelectable
                        | QtCore.Qt.ItemFlag.ItemIsEnabled
                    )
                    self.setItem(row, col, item)
                    idx += 1
        finally:
            self.blockSignals(old)

        if preserve:
            self.select_year(preserve, emit=False)
        else:
            self.select_year(str(datetime.date.today().year), emit=False)
