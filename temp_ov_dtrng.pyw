import sys
import openpyxl
from PyQt6.QtWidgets import QApplication, QMessageBox


# Ajusta solo esto si cambian los criterios
SHEET_NAME = "overwrite_registry"
FILTER_Q_VALUE_1 = "Overwrite I - Sobrescritura de FlamaNova & HormaNova"
FILTER_Q_VALUES_2 = {
    "Overwrite II - Le Etude de Dorothée",
    "Overwrite II - Sobrescritura de Dorothy & Lissette"
}
FILTER_E_VALUE = "Episodio"

def msgbox(title, message,
           type_icon=QMessageBox.Icon.Information):
    msg = QMessageBox()
    msg.setIcon(type_icon)
    msg.setWindowTitle(title)
    msg.setText(message)
    msg.exec()


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    
    if not len(sys.argv) > 2:
        errmsg = QMessageBox()
        errmsg.setIcon(QMessageBox.Icon.Critical)
        errmsg.setWindowTitle("Faltan Argumentos")
        errmsg.setText(f"Añade en la ejecucion el argumento del año para poder abrirlo")
        errmsg.exec()
        exit(1)
    
    if sys.argv[2] == "1":
        FILTER_Q_VALUES = {FILTER_Q_VALUE_1}
    elif sys.argv[2] == "2":
        FILTER_Q_VALUES = FILTER_Q_VALUES_2
    else:
        errmsg = QMessageBox()
        errmsg.setIcon(QMessageBox.Icon.Critical)
        errmsg.setWindowTitle("Argumento de version iconrrecta")
        errmsg.setText(f"Señala con 1 o 2 la version de sobrescritura")
        errmsg.exec()
        exit(1)
   
    year = sys.argv[1]
    px = f"{int(year) - 2003:02d}"
    EXCEL_PATH = f"{'E:/_Internal'}/{year}/{px}. identity/{px}. le_etude.overwrite.xlsx"
    
    # data_only=True para leer el valor calculado de las fórmulas en Q
    wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)
    if SHEET_NAME not in wb.sheetnames:
        raise KeyError(f"La hoja '{SHEET_NAME}' no existe en el archivo.")

    ws = wb[SHEET_NAME]

    copied_values: list[str] = []

    # Encabezados en la fila 3; los datos empiezan en la 4
    for row in range(4, ws.max_row + 1):
        q_value = ws[f"Q{row}"].value
        e_value = ws[f"E{row}"].value
            
        if q_value in FILTER_Q_VALUES and e_value == FILTER_E_VALUE:
            l_value = ws[f"L{row}"].value
            if l_value is None:
                continue
            copied_values.append(str(l_value))

    clipboard_text = "\n".join(copied_values)
    app.clipboard().setText(clipboard_text)

    msg_correct = (
        f"Los datos se obtuvieron con éxito.\n"
        f"Filtrados: {len(copied_values)}\n"
        f"Copiados al portapapeles desde la columna L."
    )    
    
    msgbox(
        "Exito", 
        msg_correct, 
        QMessageBox.Icon.Information
        )  

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
