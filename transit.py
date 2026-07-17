# -*- coding: utf-8 -*-
"""
rerenderizador.py - Generación de SVG y JSON para ReMcPy.
Refactorizado sin flip, solo rotaciones para orientación.
Incluye metas volantes (sprint y montaña).
"""

import os
import math
import json
import copy
import random
import xml.etree.ElementTree as ET
import rebiblioteca
import regeometria
import resvg_loader
from rebiblioteca import DESVIACION_BRUJULA, METEOROS

# ============================================================================
# CONSTANTES
# ============================================================================

DIR_RESULTS = "results"

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def limpiar_transformaciones(elemento):
    """Elimina recursivamente el atributo 'transform' de todos los elementos."""
    if 'transform' in elemento.attrib:
        del elemento.attrib['transform']
    for hijo in elemento:
        limpiar_transformaciones(hijo)
    return elemento

def rotar_punto(x, y, cx, cy, angulo_grados):
    """Rota un punto alrededor de (cx, cy) y devuelve (x', y')."""
    ang_rad = math.radians(angulo_grados)
    dx = x - cx
    dy = y - cy
    x_new = cx + dx * math.cos(ang_rad) - dy * math.sin(ang_rad)
    y_new = cy + dx * math.sin(ang_rad) + dy * math.cos(ang_rad)
    return x_new, y_new

# ============================================================================
# ASIGNACIÓN DE METEOROS
# ============================================================================

def asignar_meteoros(secuencia):
    """
    Asigna meteoros a las losetas de forma 'R' que no sean salida ni meta.
    Retorna un diccionario {clave: abreviatura}.
    """
    if len(secuencia) < 3:
        return {}
    
    elegibles = []
    for idx, clave in enumerate(secuencia):
        if idx == 0 or idx == len(secuencia) - 1:
            continue
        datos = rebiblioteca.Losetas[clave]
        forma = datos[1] if isinstance(datos, (tuple, list)) else datos
        if forma == "R":
            elegibles.append(clave)
    
    if not elegibles:
        return {}
    
    meteoros_disponibles = random.sample(METEOROS, len(METEOROS))
    asignacion = {}
    for i, clave in enumerate(elegibles):
        if i < len(meteoros_disponibles):
            asignacion[clave] = meteoros_disponibles[i]["abrev"]
        else:
            break
    return asignacion

# ============================================================================
# METAS VOLANTES
# ============================================================================

def _es_recta(forma):
    """Determina si una forma es considerada 'recta'."""
    return forma in ["R", "RC"]

def _es_curva_45(forma):
    """Determina si una forma es una curva de 45°."""
    return forma in ["CI45", "CD45"]

def _es_curva_90(forma):
    """Determina si una forma es una curva de 90°."""
    return forma in ["CI90", "CD90"]

def _es_subida(terreno):
    """Determina si un terreno es de subida."""
    return terreno == "s"

def _es_bajada(terreno):
    """Determina si un terreno es de bajada."""
    return terreno == "b"

def verificar_meta_sprint(secuencia, catalogo):
    """
    Verifica si se puede colocar una meta volante al sprint.
    Retorna el índice de la loseta anterior a la linde, o None si no es posible.
    """
    if len(secuencia) < 7:
        return None
    
    limite_superior = len(secuencia) - 5
    if limite_superior < 2:
        return None
    
    for idx in range(2, limite_superior + 1):
        if idx < 2:
            continue
        
        formas_anteriores = []
        for i in range(max(0, idx - 3), idx + 1):
            clave = secuencia[i]
            forma = catalogo[clave]["forma"]
            formas_anteriores.append(forma)
        
        if any(_es_curva_90(f) for f in formas_anteriores):
            continue
        
        if len(formas_anteriores) >= 2:
            if _es_recta(formas_anteriores[-1]) and _es_recta(formas_anteriores[-2]):
                return idx
        
        if len(formas_anteriores) >= 4:
            if (_es_recta(formas_anteriores[-4]) and 
                _es_recta(formas_anteriores[-3]) and 
                _es_curva_45(formas_anteriores[-2]) and 
                _es_recta(formas_anteriores[-1])):
                return idx
    
    return None

def calcular_elevacion_acumulada(secuencia, catalogo):
    """
    Calcula la elevación acumulada en cada linde.
    Retorna lista de (indice_loseta, elevacion)
    """
    elevacion = 0
    resultado = []
    
    for i, clave in enumerate(secuencia):
        datos = catalogo[clave]
        # Obtener terrenos de la loseta
        terrenos = datos.get("terrenos", [])
        if not terrenos:
            # Si no tenemos terrenos en catalogo, los obtenemos de Biblioteca
            import rebiblioteca
            terrenos = rebiblioteca.Losetas[clave][2]
        
        for terreno in terrenos:
            if _es_subida(terreno):
                elevacion += 1
            elif _es_bajada(terreno):
                elevacion -= 1
        
        resultado.append((i, elevacion))
    
    return resultado

def verificar_meta_montana(secuencia, catalogo, umbral_subidas_consecutivas=4, umbral_subidas_totales=20):
    """
    Verifica si se puede colocar una meta volante de montaña.
    Retorna el índice de la loseta anterior a la linde, o None si no es posible.
    """
    import rebiblioteca
    
    # 1. Verificar requisitos globales del circuito
    total_subidas = 0
    max_consecutivas = 0
    consecutivas_actual = 0
    
    for clave in secuencia:
        datos = rebiblioteca.Losetas[clave]
        terrenos = datos[2]
        for terreno in terrenos:
            if _es_subida(terreno):
                total_subidas += 1
                consecutivas_actual += 1
                if consecutivas_actual > max_consecutivas:
                    max_consecutivas = consecutivas_actual
            else:
                consecutivas_actual = 0
    
    if max_consecutivas < umbral_subidas_consecutivas and total_subidas < umbral_subidas_totales:
        return None
    
    if len(secuencia) < 2:
        return None
    
    perfil = calcular_elevacion_acumulada(secuencia, catalogo)
    limite_inferior = max(0, len(secuencia) - 5)
    
    mejores_candidatos = []
    
    for idx in range(len(secuencia) - 2, limite_inferior - 1, -1):
        clave_actual = secuencia[idx]
        clave_siguiente = secuencia[idx + 1] if idx + 1 < len(secuencia) else None
        
        if not clave_siguiente:
            continue
        
        datos_actual = rebiblioteca.Losetas[clave_actual]
        datos_siguiente = rebiblioteca.Losetas[clave_siguiente]
        
        terrenos_actual = datos_actual[2]
        terrenos_siguiente = datos_siguiente[2]
        
        ultimo_terreno_actual = terrenos_actual[-1] if terrenos_actual else None
        primer_terreno_siguiente = terrenos_siguiente[0] if terrenos_siguiente else None
        
        if (ultimo_terreno_actual == "s" and 
            primer_terreno_siguiente in ["p", "d", "b", "i", "m", "r", "e"]):
            
            elevacion_en_linde = None
            for idx_perfil, elev in perfil:
                if idx_perfil == idx:
                    elevacion_en_linde = elev
                    break
            
            if elevacion_en_linde is not None:
                mejores_candidatos.append((idx, elevacion_en_linde))
    
    if mejores_candidatos:
        mejores_candidatos.sort(key=lambda x: x[1], reverse=True)
        return mejores_candidatos[0][0]
    
    return None

def asignar_metas_volantes(secuencia, catalogo, probabilidad=0.8):
    """
    Asigna metas volantes al sprint y de montaña.
    Retorna un diccionario con las posiciones.
    """
    metas = {
        "sprint": None,
        "montana": None
    }
    
    if random.random() < probabilidad:
        pos_sprint = verificar_meta_sprint(secuencia, catalogo)
        if pos_sprint is not None:
            metas["sprint"] = pos_sprint
    
    if random.random() < probabilidad:
        pos_montana = verificar_meta_montana(secuencia, catalogo)
        if pos_montana is not None:
            metas["montana"] = pos_montana
    
    return metas

def dibujar_meta_svg(svg_body, pieza_actual, tipo_meta):
    """
    Dibuja una línea de meta volante PARALELA a la dirección de la pista,
    centrada en el punto de salida de la loseta.
    """
    # Punto central (salida de la loseta)
    cx = pieza_actual["salida"].x
    cy = pieza_actual["salida"].y
    
    # Vector de dirección de la salida (dirección de marcha)
    vx = pieza_actual["salida"].x - pieza_actual["entrada"].x
    vy = pieza_actual["salida"].y - pieza_actual["entrada"].y
    longitud = math.sqrt(vx**2 + vy**2)
    
    if longitud > 0:
        vx /= longitud
        vy /= longitud
    else:
        # Fallback (horizontal)
        vx, vy = 1.0, 0.0

# === CONTROL DEL GIRO DE 90° ===
    # Cambia este valor a -1 si está girada 90°
    flip = -1        # Prueba con 1 primero. Si está girada, cambia a -1
    
    vx = vx * flip
    vy = vy * flip
    
    # Longitud de la meta
    half_length = 35   # ≈ 70 píxeles totales    
    
    # Puntos de la línea (paralela a la dirección de la pista)
    x1 = cx - vx * half_length
    y1 = cy - vy * half_length
    x2 = cx + vx * half_length
    y2 = cy + vy * half_length
    
    # Estilo según tipo de meta
    if tipo_meta == "sprint":
        color = "#90EE90"  # light green
        stroke_width = 8
        svg_body += f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{stroke_width}" opacity="0.85" />'
    elif tipo_meta == "montana":
        # Línea base blanca
        color = "#FFFFFF"
        stroke_width = 8
        svg_body += f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{stroke_width}" opacity="0.9" />'
        # Línea superior rosa con rayas
        svg_body += f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#FF69B4" stroke-width="{stroke_width}" stroke-dasharray="6,4" opacity="0.85" />'
    
    return svg_body

# ============================================================================
# GENERACIÓN DE SVG
# ============================================================================

def generar_svg_etapa(secuencia, nombre_etapa, nombre_tour, sesion, etapa_global,
                      nombre_archivo="circuito.svg", meteoros_por_loseta=None,
                      nombre_personalizado=""):
    """
    Genera el SVG de una etapa.
    
    Args:
        secuencia (list): Lista de claves de losetas.
        nombre_etapa (str): Nombre de la etapa (para cabecera).
        nombre_tour (str): Nombre del tour.
        sesion (int): Número de sesión.
        etapa_global (int): Número de etapa global.
        nombre_archivo (str): Nombre del archivo SVG.
        meteoros_por_loseta (dict): Meteoros asignados a las losetas.
        nombre_personalizado (str): Nombre personalizado de la etapa.
    
    Returns:
        tuple: (ruta_svg, rumbo_final, metas) o (None, None, None) si falla.
    """
    if not secuencia:
        return None, None, None

    if meteoros_por_loseta is None:
        meteoros_por_loseta = {}

    # 1. Cargar geometrías (hitboxes) para todas las losetas
    catalogo = {}
    for clave in secuencia:
        datos = rebiblioteca.Losetas[clave]
        forma = datos[1] if isinstance(datos, (tuple, list)) else datos
        try:
            catalogo[clave] = resvg_loader.cargar_geometria_base(forma)
            catalogo[clave]["id_pieza"] = clave
            catalogo[clave]["forma"] = forma
            # Guardar terrenos para uso posterior
            catalogo[clave]["terrenos"] = datos[2]
        except Exception as e:
            print(f"⚠️ Error cargando geometría para {clave} (forma: {forma}): {e}")
            return None, None, None

    # 2. Colocar piezas (posicionamiento original, SIN ROTAR)
    circuito_colocado = []
    rumbo_acumulado = 0

    for i, clave in enumerate(secuencia):
        if clave not in catalogo:
            continue
        pieza_base = copy.deepcopy(catalogo[clave])
        datos = rebiblioteca.Losetas[clave]
        forma = datos[1] if isinstance(datos, (tuple, list)) else datos

        if i == 0:
            pieza_base["rotacion"] = 0
            circuito_colocado.append(pieza_base)
            rumbo_acumulado += DESVIACION_BRUJULA.get(forma, 0)
        else:
            ultima_colocada = circuito_colocado[-1]
            pieza_alineada = regeometria.alinear_pieza(
                ultima_colocada, pieza_base, rumbo_acumulado
            )
            pieza_alineada["id_pieza"] = clave
            pieza_alineada["rotacion"] = rumbo_acumulado
            circuito_colocado.append(pieza_alineada)
            rumbo_acumulado += DESVIACION_BRUJULA.get(forma, 0)

    if not circuito_colocado:
        print("❌ No se pudo posicionar ninguna pieza.")
        return None, None, None

    # 3. Asignar metas volantes
    metas = asignar_metas_volantes(secuencia, catalogo)

    # 4. Calcular bounding box original
    min_x = min_y = float('inf')
    max_x = max_y = float('-inf')
    for pieza in circuito_colocado:
        for x, y in pieza["hitbox"].exterior.coords:
            if x < min_x: min_x = x
            if y < min_y: min_y = y
            if x > max_x: max_x = x
            if y > max_y: max_y = y

    # 5. Calcular rotación global (solo para orientar la salida al Norte o Este)
    primera_pieza = circuito_colocado[0]
    vx = primera_pieza["salida"].x - primera_pieza["entrada"].x
    vy = primera_pieza["salida"].y - primera_pieza["entrada"].y
    ang_actual = math.degrees(math.atan2(vy, vx))

    if abs(ang_actual - (-90)) < abs(ang_actual - 0):
        ang_deseado = -90  # Norte
    else:
        ang_deseado = 0    # Este

    rotacion_global = ang_deseado - ang_actual
    rotacion_global = ((rotacion_global + 180) % 360) - 180
    if abs(rotacion_global) < 0.5:
        rotacion_global = 0

    cx = (min_x + max_x) / 2.0
    cy = (min_y + max_y) / 2.0

    # 6. Construir el contenido del SVG (piezas, etiquetas, meteoros, metas)
    contenido_piezas = ""
    etiquetas = []
    meteoros_list = []

    for idx, pieza in enumerate(circuito_colocado):
        clave = pieza["id_pieza"]
        forma = catalogo[clave]["forma"]
        entrada_original = catalogo[clave]["entrada"]

        contenido_svg = resvg_loader.cargar_svg_representacion(clave, forma)

        if contenido_svg:
            try:
                root = ET.fromstring(contenido_svg)
                if root.tag == 'svg':
                    for child in root:
                        limpiar_transformaciones(child)
                    contenido_interno = ''.join(ET.tostring(child, encoding='unicode') for child in root)
                else:
                    contenido_interno = contenido_svg
            except ET.ParseError:
                contenido_interno = contenido_svg

            if idx == 0:
                grupo = f'<g>\n{contenido_interno}\n</g>'
            else:
                ultima_colocada = circuito_colocado[idx-1]
                salida_anterior = ultima_colocada["salida"]
                tx = salida_anterior.x - entrada_original.x
                ty = salida_anterior.y - entrada_original.y
                rotacion = pieza["rotacion"]
                transform = f"translate({tx}, {ty}) rotate({rotacion}, {entrada_original.x}, {entrada_original.y})"
                grupo = f'<g transform="{transform}">\n{contenido_interno}\n</g>'
            contenido_piezas += grupo
        else:
            x, y = pieza["hitbox"].exterior.xy
            puntos = " ".join(f"{px},{py}" for px, py in zip(x, y))
            contenido_piezas += f'<polygon points="{puntos}" fill="#44aa00" stroke="black" stroke-width="1.5" />'

        # ---------- ETIQUETA CON CLAVE ----------
        ang_rad = math.radians(pieza.get("rotacion", 0))
        if idx == 0:
            X_ent = entrada_original.x
            Y_ent = entrada_original.y
        else:
            salida_anterior = circuito_colocado[idx-1]["salida"]
            X_ent = salida_anterior.x
            Y_ent = salida_anterior.y

        x_etiqueta = X_ent + 5 + 20 * math.sin(ang_rad)
        y_etiqueta = Y_ent - 20 * math.cos(ang_rad)

        if clave.endswith("'"):
            color_fondo = "black"
            color_texto = "white"
            color_borde = "white"
            texto_contenido = f"{clave[0].capitalize()}"
        else:
            color_fondo = "white"
            color_texto = "black"
            color_borde = "black"
            texto_contenido = clave

        etiquetas.append((x_etiqueta, y_etiqueta, texto_contenido, color_fondo, color_texto, color_borde))

        # ---------- METEORO ----------
        if clave in meteoros_por_loseta:
            abrev = meteoros_por_loseta[clave]
            radio = 8
            separacion_centros = 2.0
            x_met = x_etiqueta + 10 + 0.6 + (separacion_centros / 2) + radio
            y_met = y_etiqueta - 10

            if abrev == "CT":
                color_fondo = "white"
                color_texto = "black"
                color_borde = "white"
            else:
                color_fondo = "black"
                color_texto = "white"
                color_borde = "black"

            meteoros_list.append((x_met, y_met, abrev, color_fondo, color_texto, color_borde, separacion_centros, radio))

    # 7. Aplicar rotación global
    if abs(rotacion_global) > 0.5:
        contenido_piezas = f'<g transform="rotate({rotacion_global}, {cx}, {cy})">\n{contenido_piezas}\n</g>'

    # 8. Calcular bounding box después de rotar
    esquinas = [(min_x, min_y), (max_x, min_y), (max_x, max_y), (min_x, max_y)]
    nuevas_esquinas = []
    for x, y in esquinas:
        nx, ny = rotar_punto(x, y, cx, cy, rotacion_global)
        nuevas_esquinas.append((nx, ny))
    xs = [p[0] for p in nuevas_esquinas]
    ys = [p[1] for p in nuevas_esquinas]
    
    margen = 30
    view_min_x = min(xs) - margen
    view_min_y = min(ys) - margen
    view_max_x = max(xs) + margen
    view_max_y = max(ys) + margen

    # 9. Si el circuito es portrait, rotar para landscape
    ancho_actual = view_max_x - view_min_x
    alto_actual = view_max_y - view_min_y
    rotacion_landscape = 0
    
    if alto_actual > ancho_actual:
        rotacion_landscape = -90
        contenido_piezas = f'<g transform="rotate({rotacion_landscape}, {cx}, {cy})">\n{contenido_piezas}\n</g>'
        nuevas_esquinas_landscape = []
        for x, y in esquinas:
            nx, ny = rotar_punto(x, y, cx, cy, rotacion_landscape)
            nuevas_esquinas_landscape.append((nx, ny))
        xs_l = [p[0] for p in nuevas_esquinas_landscape]
        ys_l = [p[1] for p in nuevas_esquinas_landscape]
        view_min_x = min(xs_l) - margen
        view_min_y = min(ys_l) - margen
        view_max_x = max(xs_l) + margen
        view_max_y = max(ys_l) + margen

    # 10. Transformar coordenadas de etiquetas y meteoros
    etiquetas_transformadas = []
    for x, y, texto, cf, ct, cb in etiquetas:
        if abs(rotacion_global) > 0.5:
            x, y = rotar_punto(x, y, cx, cy, rotacion_global)
        if abs(rotacion_landscape) > 0.5:
            x, y = rotar_punto(x, y, cx, cy, rotacion_landscape)
        etiquetas_transformadas.append((x, y, texto, cf, ct, cb))

    meteoros_transformados = []
    for x_met, y_met, abrev, cf, ct, cb, sep, radio in meteoros_list:
        if abs(rotacion_global) > 0.5:
            x_met, y_met = rotar_punto(x_met, y_met, cx, cy, rotacion_global)
        if abs(rotacion_landscape) > 0.5:
            x_met, y_met = rotar_punto(x_met, y_met, cx, cy, rotacion_landscape)
        meteoros_transformados.append((x_met, y_met, abrev, cf, ct, cb, sep, radio))

    # 11. Construir el SVG final
    ancho_final = view_max_x - view_min_x
    alto_final = view_max_y - view_min_y
    svg_header = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view_min_x} {view_min_y} {ancho_final} {alto_final}" width="100%" height="100%">'
    svg_footer = "</svg>"

    # Fondo
    svg_body = f'<rect x="{view_min_x}" y="{view_min_y}" width="{ancho_final}" height="{alto_final}" fill="#f0f0f0" />'

    # Piezas
    svg_body += contenido_piezas

    # Etiquetas
    for x, y, texto, cf, ct, cb in etiquetas_transformadas:
        svg_body += f'<rect x="{x - 10}" y="{y - 10}" width="20" height="20" rx="4" fill="{cf}" stroke="{cb}" stroke-width="1.5" />'
        svg_body += f'<text x="{x}" y="{y + 1}" fill="{ct}" font-size="12" font-weight="bold" text-anchor="middle" dominant-baseline="middle">{texto}</text>'

    # Meteoros
    for x_met, y_met, abrev, cf, ct, cb, sep, radio in meteoros_transformados:
        svg_body += f'<circle cx="{x_met - sep/2}" cy="{y_met}" r="{radio}" fill="{cf}" stroke="{cb}" />'
        svg_body += f'<circle cx="{x_met + sep/2}" cy="{y_met}" r="{radio}" fill="{cf}" stroke="{cb}" />'
        svg_body += f'<text x="{x_met}" y="{y_met + 1}" fill="{ct}" font-size="9" font-weight="bold" text-anchor="middle" dominant-baseline="middle">{abrev}</text>'

    # ---------- METAS VOLANTES (líneas en el SVG) ----------
    # Necesitamos las piezas en las coordenadas finales (rotadas)
    # Para simplificar, usamos las piezas originales y las rotamos
    circuito_final = []
    for idx, pieza in enumerate(circuito_colocado):
        pieza_final = copy.deepcopy(pieza)
        # Aplicar rotaciones a entrada y salida
        if abs(rotacion_global) > 0.5:
            nx, ny = rotar_punto(pieza_final["entrada"].x, pieza_final["entrada"].y, cx, cy, rotacion_global)
            pieza_final["entrada"] = type(pieza_final["entrada"])(nx, ny)
            nx, ny = rotar_punto(pieza_final["salida"].x, pieza_final["salida"].y, cx, cy, rotacion_global)
            pieza_final["salida"] = type(pieza_final["salida"])(nx, ny)
        if abs(rotacion_landscape) > 0.5:
            nx, ny = rotar_punto(pieza_final["entrada"].x, pieza_final["entrada"].y, cx, cy, rotacion_landscape)
            pieza_final["entrada"] = type(pieza_final["entrada"])(nx, ny)
            nx, ny = rotar_punto(pieza_final["salida"].x, pieza_final["salida"].y, cx, cy, rotacion_landscape)
            pieza_final["salida"] = type(pieza_final["salida"])(nx, ny)
        circuito_final.append(pieza_final)

    # Dibujar líneas de meta
    for idx, pieza in enumerate(circuito_final):
        #if metas.get("sprint") == idx:
        if metas.get("sprint") is not None and idx == metas["sprint"] -1:   # o -1 según convenga
            svg_body = dibujar_meta_svg(svg_body, pieza, "sprint")
        #if metas.get("montana") == idx:
        if metas.get("montana") is not None and idx == metas["montana"] -1:   # o -1 según convenga
            svg_body = dibujar_meta_svg(svg_body, pieza, "montana")

    # Guardar
    os.makedirs(DIR_RESULTS, exist_ok=True)
    ruta_salida = os.path.join(DIR_RESULTS, nombre_archivo)
    svg_completo = svg_header + svg_body + svg_footer
    with open(ruta_salida, 'w', encoding='utf-8') as f:
        f.write(svg_completo)

    print(f"✅ SVG guardado como '{ruta_salida}'")
    return ruta_salida, rumbo_acumulado, metas

# ============================================================================
# GENERACIÓN DE JSON
# ============================================================================

def generar_json_etapa(secuencia, nombre_tour, sesion, etapa, rumbo_final,
                       meteoros_por_loseta=None, nombre_personalizado="", metas=None):
    """
    Genera el archivo JSON de una etapa.
    """
    if meteoros_por_loseta is None:
        meteoros_por_loseta = {}
    
    if metas is None:
        metas = {}
    
    if nombre_personalizado:
        nombre_etapa = f"{nombre_personalizado} (S:{sesion} E:{etapa})"
    else:
        nombre_etapa = f"{nombre_tour}_S:{sesion}-E:{etapa}"
    
    tiles = []
    for clave in secuencia:
        if clave.endswith("'"):
            base = clave[:-1]
            tiles.append(f"{base}-upp")
        else:
            tiles.append(clave)
    
    data = {
        "version": 1,
        "name": nombre_etapa,
        "tiles": tiles,
        "checkpoints": [],
        "sprintPoints": 0,
        "komPoints": 0,
        "camera": {
            "rotation": rumbo_final if rumbo_final is not None else 0,
            "zoom": 1
        },
        "weather": meteoros_por_loseta,
        "metas": metas  # Añadimos las metas al JSON
    }
    
    os.makedirs(DIR_RESULTS, exist_ok=True)
    nombre_json = f"circuito_etapa_{etapa}.json"
    ruta_json = os.path.join(DIR_RESULTS, nombre_json)
    with open(ruta_json, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ JSON guardado como '{ruta_json}'")
    return ruta_json

# ============================================================================
# FUNCIÓN DE PRUEBA
# ============================================================================

if __name__ == "__main__":
    print("🧪 Probando rerenderizador...")
    prueba_secuencia = ["a", "b'", "c", "d", "e", "f'", "g", "h", "i", "j'", "k", "l", "m", "n'", "o", "p", "q", "r'", "s", "t"]
    prueba_meteoros = {"b'": "CT", "f'": "VF", "n'": "SM"}
    
    ruta, rumbo, metas = generar_svg_etapa(
        secuencia=prueba_secuencia,
        nombre_etapa="Prueba",
        nombre_tour="Tour de Prueba",
        sesion=1,
        etapa_global=1,
        nombre_archivo="prueba.svg",
        meteoros_por_loseta=prueba_meteoros,
        nombre_personalizado="Etapa de Prueba"
    )
    
    if ruta:
        print(f"✅ SVG generado: {ruta}")
        print(f"✅ Metas asignadas: {metas}")
        generar_json_etapa(
            secuencia=prueba_secuencia,
            nombre_tour="Tour de Prueba",
            sesion=1,
            etapa=1,
            rumbo_final=rumbo,
            meteoros_por_loseta=prueba_meteoros,
            nombre_personalizado="Etapa de Prueba",
            metas=metas
        )
