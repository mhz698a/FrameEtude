from datetime import datetime, timedelta, timezone

def convertir_rango_a_iso8601_local(rango_propio: str) -> str:
    """
    Convierte un rango de tiempo con posible cruce de medianoche
    al estándar ISO 8601 con huso horario UTC-06:00.
    """
    try:
        # 1. Definir el huso horario UTC-06:00
        tz_local = timezone(timedelta(hours=-6))
        
        # 2. Separar los componentes
        fecha_str, horas_str = rango_propio.split(" ")
        hora_inicio_str, hora_fin_str = horas_str.split("-")
        
        # 3. Parsear como objetos datetime iniciales (sin zona horaria aún para comparar fácil)
        formato_hora = "%H:%M:%S"
        h_inicio = datetime.strptime(hora_inicio_str, formato_hora).time()
        h_fin = datetime.strptime(hora_fin_str, formato_hora).time()
        
        # 4. Construir la fecha base
        fecha_base = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        
        # 5. Combinar fecha y hora
        dt_inicio = datetime.combine(fecha_base, h_inicio)
        dt_fin = datetime.combine(fecha_base, h_fin)
        
        # 6. REGLA CRÍTICA: Si la hora fin es menor, es el día siguiente
        if dt_fin < dt_inicio:
            dt_fin += timedelta(days=1)
            
        # 7. Asignar el huso horario UTC-06:00 a ambos extremos
        dt_inicio = dt_inicio.replace(tzinfo=tz_local)
        dt_fin = dt_fin.replace(tzinfo=tz_local)
        
        # 8. Convertir a ISO 8601 (isoformat() añade automáticamente el -06:00)
        return f"{dt_inicio.isoformat()}/{dt_fin.isoformat()}"

    except ValueError as e:
        raise ValueError(f"Formato inválido o error en datos. Error: {e}")

# --- Prueba del caso crítico ---
rango_critico = "2023-01-07 11:58:59-01:22:31"
resultado = convertir_rango_a_iso8601_local(rango_critico)

print(f"Original:      {rango_critico}")
print(f"Estandarizado: {resultado}")

# Salida: 2023-01-07T11:58:59-06:00/2023-01-08T01:22:31-06:00