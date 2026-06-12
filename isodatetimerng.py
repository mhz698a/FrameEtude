import re
from datetime import datetime, timedelta, timezone

def is_standardized(time_range: str) -> bool:
    """
    Comprueba si el rango de tiempo ya cuenta con el formato estandarizado:
    AAAA-MM-DDTHH:MM:SS-06:00/AAAA-MM-DDTHH:MM:SS-06:00
    """
    # Expresión regular para validar el formato final esperado
    pattern = (
        r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}/"
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$"
    )
    return bool(re.match(pattern, time_range))

def standardize_time_range(time_range: str, disable_z_ajust: bool = False) -> str:
    """
    Transforma un rango de tiempo en formato propio a ISO 8601 estándar con timezone -06:00.
    """
    # Si ya tiene el formato correcto, no hacemos nada
    if is_standardized(time_range):
        return time_range
        
    # Caso 1: Formato "AAAA-MM-DD HH:MM:SS-HH:MM:SS"
    match_custom1 = re.match(r"^(\d{4}-\d{2}-\d{2})\s(\d{2}:\d{2}:\d{2})-(\d{2}:\d{2}:\d{2})$", time_range)
    if match_custom1:
        date_str, start_time_str, end_time_str = match_custom1.groups()
        
        # Convertimos a objetos datetime
        local_tz = datetime.now().astimezone().tzinfo

        start_dt = datetime.strptime(
            f"{date_str} {start_time_str}",
            "%Y-%m-%d %H:%M:%S"
        ).replace(tzinfo=local_tz)

        end_dt = datetime.strptime(
            f"{date_str} {end_time_str}",
            "%Y-%m-%d %H:%M:%S"
        ).replace(tzinfo=local_tz)
        
        # Lógica de medianoche: Si la hora de fin es menor, sumamos 1 día
        if end_dt < start_dt:
            end_dt += timedelta(days=1)
            
        # Retornamos formateado
        start_iso = start_dt.isoformat()
        end_iso = end_dt.isoformat()
        return f"{start_iso}/{end_iso}"

    # Caso 2: Formato "AAAA-MM-DDTHH:MM:SSZ/AAAA-MM-DDTHH:MM:SSZ" (UTC)
    if not disable_z_ajust:
        return time_range
    
    match_custom2 = re.match(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})Z/(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})Z$", time_range)
    
    if match_custom2:
        
        start_str, end_str = match_custom2.groups()
        
        # Definimos las fechas como UTC (Z)
        start_dt = datetime.strptime(start_str, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        end_dt = datetime.strptime(end_str, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        
        # Las convertimos al timezone -06:00
        start_dt_local = start_dt.astimezone(datetime.now().astimezone().tzinfo)
        end_dt_local = end_dt.astimezone(datetime.now().astimezone().tzinfo)
        
        return f"{start_dt_local.isoformat()}/{end_dt_local.isoformat()}"
        
    raise ValueError(f"Formato no reconocido: {time_range}")

# --- Pruebas del módulo ---
if __name__ == "__main__":
    # Prueba 1: Tu caso específico de cruce de medianoche
    test_1 = "2023-01-07 11:58:19-00:22:31"
    print(f"Original: {test_1}\nEstandarizado: {standardize_time_range(test_1)}\n")
    
    # Prueba 2: Caso de formato UTC (Z) convirtiendo a -06:00 
    # (Restará 6 horas matemáticamente a la fecha)
    test_2 = "2023-01-07T12:00:00Z/2023-01-07T14:00:00Z"
    print(f"Original: {test_2}\nEstandarizado: {standardize_time_range(test_2, False)}\n")

    # Prueba 3: Comprobador
    test_3 = "2023-01-07T11:58:19-06:00/2023-01-08T00:22:31-06:00"
    print(f"¿El Test 3 ya está estandarizado?: {is_standardized(test_3)}")