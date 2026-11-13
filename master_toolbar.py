from PyQt6 import QtCore, QtGui, QtWidgets

class MasterToolBar(QtWidgets.QToolBar):
    """
    QToolBar nativo con soporte automático de desbordamiento (overflow / botón >>)
    para las acciones y un alto mínimo de 30px.
    """
    def __init__(self, parent=None):
        super().__init__("Master ToolBar", parent)
        self.setMovable(False)
        self.setStyleSheet("""
            QToolBar {
                background: transparent;
                border: none;
                spacing: 3px;
            }
            QToolButton {
                color: white;
                border-radius: 4px;
                padding: 4px 8px;
                min-height: 20px;
            }
            QToolButton:hover {
                background-color: #383838;
            }
            QToolButton:pressed {
                background-color: #202020;
            }
            QToolButton:checked {
                background-color: #1a4f8a;
                border: 1px solid #05478a;
            }
            QToolButton:disabled {
                color: #555555;
            }
            QToolButton#CheckMDButton {
                color: white;
                border-radius: 4px;
                min-height: 30px;
            }
            QToolButton#CheckMDButton:hover {
                background-color: #075cb5;
            }
            QToolButton#CheckMDButton:pressed {
                background-color: #032f5c;
            }
            QToolButton#CheckMDButton:disabled {
                background-color: #162638;
                color: #507090;
                border: 1px solid #1e3550;
            }
        """)

    def add_simplified_action(self, text: str, slot=None, tooltip: str = "", object_name: str = "", visible: bool = True, enabled: bool = True, checkable: bool = False) -> QtGui.QAction:
        """
        Agrega una acción nativa a la QToolBar, permitiendo configurar visibilidad, estado y si es checkable.
        """
        action = QtGui.QAction(text, self)
        if object_name:
            action.setObjectName(object_name)
        if tooltip:
            action.setToolTip(tooltip)
        
        action.setCheckable(checkable)
        if slot:
            if checkable:
                action.toggled.connect(slot)
            else:
                action.triggered.connect(slot)
        
        action.setVisible(visible)
        action.setEnabled(enabled)
        self.addAction(action)
        return action

    def add_custom_widget(self, widget: QtWidgets.QWidget):
        """
        Agrega widgets adicionales (como QLabel o QCheckBox) a la barra.
        """
        return self.addWidget(widget)
    
    def add_dropdown_button(self, text: str, menu_items: list[tuple[str, callable]], tooltip: str = "", object_name: str = "") -> QtWidgets.QToolButton:
        """
        Agrega un botón con menú desplegable (dropdown) a la QToolBar.
        """
        btn = QtWidgets.QToolButton(self)
        btn.setText(text)
        if object_name:
            btn.setObjectName(object_name)
        if tooltip:
            btn.setToolTip(tooltip)
        
        menu = QtWidgets.QMenu(btn)
        for item_text, slot in menu_items:
            action = menu.addAction(item_text)
            if slot:
                action.triggered.connect(slot)
                
        btn.setMenu(menu)
        btn.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
        
        self.addWidget(btn)
        return btn