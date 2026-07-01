import json
import config
import os

def get_overwrite_data(key_const):
    """
    Abre el archivo, busca la clave y devuelve los valores como una tupla.
    Example:
    * OVERWRITE_0 = get_overwrite_data("ov_0")
    * regresa: (time_num, review_date, info)
    """

    fallback = ("?", "?", "Especifique la base de datos en ajustes de overwrite ni seasons")

    if not os.path.exists(config.OVERWRITE_DATABASE):
        return fallback

    try:
        with open(config.OVERWRITE_DATABASE, "r", encoding="utf-8") as archivo:
            datos = json.load(archivo)

        item = datos.get(key_const)
        if not item:
            return fallback

        return (item.get("id", "?"), item.get("fecha", "?"), item.get("descripcion", "Sin descripción"))
    except Exception:
        return fallback
