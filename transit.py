# -*- coding: utf-8 -*-
from Npp import notepad, editor
from datetime import datetime

def generar_referencias():
    # 1. Obtener el texto seleccionado actual
    seleccion = editor.getSelText().strip()
    if not seleccion:
        notepad.messageBox("Por favor, selecciona primero la referencia de origen (ej. TA261015003A;)", "Error")
        return
    
    # Extraer solo el codigo antes del primer punto y coma y quitar espacios
    partes = seleccion.split(';')
    ref_origen = partes[0].strip()
    
    if len(ref_origen) < 11 or not ref_origen.startswith("TA"):
        notepad.messageBox("La seleccion no tiene el formato correcto (ej. TA261015003A;)", "Error")
        return
    
    # 2. Extraer datos de la referencia seleccionada
    fecha_ref_str = ref_origen[2:8]     # "261015"
    num_ref_str = ref_origen[8:11]      # "003"
    letra_ref = ref_origen[11]          # "A"
    
    # 3. Obtener la fecha actual del sistema (Formato AAMMDD)
    fecha_hoy_str = datetime.now().strftime("%y%m%d")
    
    lineas_a_insertar = []
    
    # CASO A: Mismo dia -> Generar la consecutiva inmediata + 4 consecutivas mas (Total 5 arriba)
    if fecha_ref_str == fecha_hoy_str:
        num_actual = int(num_ref_str)
        for _ in range(5):
            num_actual += 1
            nueva_ref = "TA{}{:03d}{};".format(fecha_hoy_str, num_actual, letra_ref)
            lineas_a_insertar.insert(0, nueva_ref)
            
    # CASO B: Dia distinto -> Empezar en 000A con guiones + 5 consecutivas mas arriba (Total 6)
    else:
        # Primero la base: 000A con guiones
        base_ref = "TA{}{:03d}{}; -------------------------------------------------------------------------------------;".format(fecha_hoy_str, 0, letra_ref)
        lineas_a_insertar.insert(0, base_ref)
        
        # Luego las 5 consecutivas por encima (de la 001 a la 005)
        num_actual = 0
        for _ in range(5):
            num_actual += 1
            nueva_ref = "TA{}{:03d}{};".format(fecha_hoy_str, num_actual, letra_ref)
            lineas_a_insertar.insert(0, nueva_ref)

    # 4. Preparar el bloque de texto e insertarlo por encima de la linea seleccionada
    texto_final = "\r\n".join(lineas_a_insertar) + "\r\n"
    
    # Obtener la posicion de la linea donde empieza la seleccion actual
    linea_actual = editor.lineFromPosition(editor.getSelectionStart())
    posicion_inicio_linea = editor.positionFromLine(linea_actual)
    
    # Insertar el texto justo al inicio de esa linea (por encima)
    editor.insertText(posicion_inicio_linea, texto_final)

# Ejecutar la funcion
generar_referencias()
