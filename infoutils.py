import os
import json
import config

def get_overwrite_data(key_const, database_path=None, database_label=None):
    """Lee una entrada {id, fecha, descripcion} desde la base JSON indicada."""
    if database_path is None:
        database_path = config.OVERWRITE_DATABASE
        setting_name = "Overwrite DB"
    else:
        setting_name = database_label or "A. Overwrite DB"

    fallback = ("?", "?", f"Especifique el archivo {setting_name} en Settings.")
    if not database_path or not os.path.isfile(database_path):
        return fallback

    try:
        with open(database_path, "r", encoding="utf-8") as archivo:
            datos = json.load(archivo)
        item = datos.get(key_const)
        if not isinstance(item, dict):
            return fallback
        return (
            item.get("id", "?"),
            item.get("fecha", "?"),
            item.get("descripcion", "Sin descripción"),
        )
    except Exception:
        return fallback
