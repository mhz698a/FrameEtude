import json
from config import OVERWRITE_DATABASE

def get_overwrite_data(key_const):
    """
    Abre el archivo, busca la clave y devuelve los valores como una tupla.
    Example: 
    * OVERWRITE_0 = get_overwrite_data("ov_0")
    * regresa: (time_num, review_date, info)
    """
    
    with open(OVERWRITE_DATABASE, "r", encoding="utf-8") as archivo:
        datos = json.load(archivo)

    item = datos[key_const]
    return (item["id"], item["fecha"], item["descripcion"])