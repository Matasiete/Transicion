# -*- coding: utf-8 -*-
"""
Versión definitiva con cabecera comentada para PDF, nombres personalizados de etapas
e integración con PDFGenerator.
"""

import copy
import math
import os
import json
import random
import xml.etree.ElementTree as ET
import SVGreader
import Biblioteca
import arquitecto
import Survey
from geometria import alinear_pieza
from Biblioteca import DESVIACION_BRUJULA, METEOROS

def limpiar_transformaciones(elemento):
    if 'transform' in elemento.attrib:
        del elemento.attrib['transform']
    for hijo in elemento:
        limpiar_transformaciones(hijo)
    return elemento

def rotar_punto(x, y, cx, cy, angulo_grados):
    ang_rad = math.radians(angulo_grados)
    dx = x - cx
    dy = y - cy
    x_new = cx + dx * math.cos(ang_rad) - dy * math.sin(ang_rad)
    y_new = cy + dx * math.sin(ang_rad) + dy * math.cos(ang_rad)
    return x_new, y_new

def flip_punto(x, y, cx, cy, flip_horizontal, flip_vertical):
    """
    Aplica flip horizontal y/o vertical a un punto alrededor de (cx, cy).
    flip_horizontal: True para reflejar en X (espejo horizontal)
    flip_vertical: True para reflejar en Y (espejo vertical)
    """
    dx = x - cx
    dy = y - cy
    if flip_horizontal:
        dx = -dx
    if flip_vertical:
        dy = -dy
    return cx + dx, cy + dy

def construir_y_guardar_circuito_svg(secuencia_claves, cabecera_tour, cadena_losetas_limpia,
                                      nombre_archivo="circuito.svg", meteoros_por_loseta=None):
    if not secuencia_claves:
        return None, None

    if meteoros_por_loseta is None:
        meteoros_por_loseta = {}

    # 1. Cargar geometrías
    catalogo = {}
    for clave in secuencia_claves:
        datos_loseta = Biblioteca.Losetas[clave]
        forma = datos_loseta[1] if isinstance(datos_loseta, (tuple, list)) else datos_loseta
        try:
            catalogo[clave] = SVGreader.extraer_geometria_loseta_completa(forma)
            catalogo[clave]["id_pieza"] = clave
            catalogo[clave]["forma"] = forma
        except Exception as e:
            print(f"⚠️ Error cargando geometría para {clave} (forma: {forma}): {e}")
            return None, None

    circuito_colocado = []
    rumbo_acumulado = 0

    for i, clave in enumerate(secuencia_claves):
        if clave not in catalogo:
            continue
        pieza_base = copy.deepcopy(catalogo[clave])
        datos_loseta = Biblioteca.Losetas[clave]
        forma = datos_loseta[1] if isinstance(datos_loseta, (tuple, list)) else datos_loseta

        if i == 0:
            pieza_base["colisiona"] = False
            pieza_base["rotacion"] = 0
            circuito_colocado.append(pieza_base)
            rumbo_acumulado += DESVIACION_BRUJULA.get(forma, 0)
        else:
            ultima_colocada = circuito_colocado[-1]
            pieza_alineada = alinear_pieza(ultima_colocada, pieza_base, rumbo_acumulado)
            pieza_alineada["id_pieza"] = clave
            pieza_alineada["colisiona"] = False
            pieza_alineada["rotacion"] = rumbo_acumulado
            circuito_colocado.append(pieza_alineada)
            rumbo_acumulado += DESVIACION_BRUJULA.get(forma, 0)

    if not circuito_colocado:
        print("❌ No se pudo posicionar ninguna pieza.")
        return None, None

    # 2. Calcular bounding box original (se mantiene)
    min_x = min_y = float('inf')
    max_x = max_y = float('-inf')
    for pieza in circuito_colocado:
        for x, y in pieza["hitbox"].exterior.coords:
            if x < min_x: min_x = x
            if y < min_y: min_y = y
            if x > max_x: max_x = x
            if y > max_y: max_y = y

    # 3. Calcular rotación global (se mantiene igual)
    primera_pieza = circuito_colocado[0]
    vx = primera_pieza["salida"].x - primera_pieza["entrada"].x
    vy = primera_pieza["salida"].y - primera_pieza["entrada"].y
    ang_actual = math.degrees(math.atan2(vy, vx))

    if abs(ang_actual - (-90)) < abs(ang_actual - 0):
        ang_deseado = -90
    else:
        ang_deseado = 0

    rotacion_global = ang_deseado - ang_actual
    rotacion_global = ((rotacion_global + 180) % 360) - 180
    if abs(rotacion_global) < 0.5:
        rotacion_global = 0

    cx = (min_x + max_x) / 2.0
    cy = (min_y + max_y) / 2.0

    # 4. Construir contenido del circuito (VERSIÓN LIMPIA)
    contenido_piezas = ""
    etiquetas = []
    meteoros_list = []

    for idx, pieza in enumerate(circuito_colocado):
        clave = pieza["id_pieza"]
        forma = catalogo[clave]["forma"]
        entrada_original = catalogo[clave]["entrada"]

        contenido_svg = SVGreader.cargar_svg_representacion(clave, forma)

        if contenido_svg:
            try:
                root = ET.fromstring(contenido_svg)
                
                # LIMPIEZA AGRESIVA
                for elem in root.iter():
                    if 'transform' in elem.attrib:
                        del elem.attrib['transform']
                    if '}' in elem.tag:
                        elem.tag = elem.tag.split('}', 1)[1]
                
                contenido_interno = ''.join(
                    ET.tostring(child, encoding='unicode')
                    for child in root
                    if child.tag != 'svg'
                )
            except Exception as e:
                print(f"   Warning parsing {clave}: {e}")
                contenido_interno = contenido_svg

            # Transformación
            if idx == 0:
                grupo = f'<g>\n{contenido_interno}\n</g>'
            else:
                ultima_colocada = circuito_colocado[idx-1]
                salida_anterior = ultima_colocada["salida"]
                tx = salida_anterior.x - entrada_original.x
                ty = salida_anterior.y - entrada_original.y
                rotacion = pieza.get("rotacion", 0)
                
                transform_str = f"translate({tx:.4f}, {ty:.4f}) rotate({rotacion:.2f}, {entrada_original.x:.4f}, {entrada_original.y:.4f})"
                grupo = f'<g transform="{transform_str}">\n{contenido_interno}\n</g>'

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
            # (tu código de meteoros aquí - se mantiene igual)
            abrev = meteoros_por_loseta[clave]
            # ... resto del código de meteoros ...
            pass  # reemplaza con tu código original de meteoros

    # Resto de la función (rotación global, viewBox, etc.) se mantiene igual
    # Copia desde aquí hacia abajo lo que tenías originalmente

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

# 5. Aplicar rotación global
    if abs(rotacion_global) > 0.5:
        contenido_piezas = f'<g transform="rotate({rotacion_global}, {cx}, {cy})">\n{contenido_piezas}\n</g>'

    # 6. Calcular bounding box después de rotar
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

    # 7. SI EL CIRCUITO ES PORTRAIT: ROTAR CONTENIDO Y AJUSTAR VIEWBOX
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


# =============================================================================
#     # 8. APLICAR FLIP PARA CORREGIR ORIENTACIÓN DE SALIDA
#     flip_horizontal = False
#     flip_vertical = False
#     
#     vx_primera = primera_pieza["salida"].x - primera_pieza["entrada"].x
#     vy_primera = primera_pieza["salida"].y - primera_pieza["entrada"].y
#     
#     if abs(rotacion_global) > 0.5:
#         ang_rad = math.radians(rotacion_global)
#         vx_primera, vy_primera = (
#             vx_primera * math.cos(ang_rad) - vy_primera * math.sin(ang_rad),
#             vx_primera * math.sin(ang_rad) + vy_primera * math.cos(ang_rad)
#         )
#     
#     if abs(rotacion_landscape) > 0.5:
#         ang_rad = math.radians(rotacion_landscape)
#         vx_primera, vy_primera = (
#             vx_primera * math.cos(ang_rad) - vy_primera * math.sin(ang_rad),
#             vx_primera * math.sin(ang_rad) + vy_primera * math.cos(ang_rad)
#         )
#     
#     ang_final = math.degrees(math.atan2(vy_primera, vx_primera))
#     
#     if abs(ang_final - 180) < 45 or abs(ang_final + 180) < 45:
#         flip_horizontal = True
#     elif abs(ang_final + 90) < 45 or abs(ang_final - 270) < 45:
#         flip_vertical = True
#     
#     if flip_horizontal or flip_vertical:
#         transform_flip = ""
#         if flip_horizontal and flip_vertical:
#             transform_flip = f"scale(-1, -1) translate({-2*cx}, {-2*cy})"
#         elif flip_horizontal:
#             transform_flip = f"scale(-1, 1) translate({-2*cx}, 0)"
#         elif flip_vertical:
#             transform_flip = f"scale(1, -1) translate(0, {-2*cy})"
#         
#         contenido_piezas = f'<g transform="{transform_flip}">\n{contenido_piezas}\n</g>'
#         
#         esquinas_flip = []
#         xs_ref = xs_l if alto_actual > ancho_actual else xs
#         ys_ref = ys_l if alto_actual > ancho_actual else ys
#         for x, y in zip(xs_ref, ys_ref):
#             if flip_horizontal:
#                 x = -x + 2*cx
#             if flip_vertical:
#                 y = -y + 2*cy
#             esquinas_flip.append((x, y))
#         
#         xs_f = [p[0] for p in esquinas_flip]
#         ys_f = [p[1] for p in esquinas_flip]
#         view_min_x = min(xs_f) - margen
#         view_min_y = min(ys_f) - margen
#         view_max_x = max(xs_f) + margen
#         view_max_y = max(ys_f) + margen
# =============================================================================

    # 9. AÑADIR MARGEN SUPERIOR PARA CABECERA
    margen_superior = 15
    view_min_y -= margen_superior

    # 10. DESPLAZAR PARA CABECERA (REDUCIDO PARA SVG SIN CABECERA)
    desplazamiento_y = 10  # REDUCIDO de 30 a 10 para SVG sin cabecera
    view_min_y += desplazamiento_y
    view_max_y += desplazamiento_y

    contenido_piezas = f'<g transform="translate(0, {desplazamiento_y})">\n{contenido_piezas}\n</g>'

    # 11. TRANSFORMAR ETIQUETAS Y METEOROS
    etiquetas_transformadas = []
    for x, y, texto, cf, ct, cb in etiquetas:
        if abs(rotacion_global) > 0.5:
            x, y = rotar_punto(x, y, cx, cy, rotacion_global)
        if abs(rotacion_landscape) > 0.5:
            x, y = rotar_punto(x, y, cx, cy, rotacion_landscape)
# =============================================================================
#         if flip_horizontal or flip_vertical:
#             x, y = flip_punto(x, y, cx, cy, flip_horizontal, flip_vertical)
# =============================================================================
        x, y = x, y + desplazamiento_y
        etiquetas_transformadas.append((x, y, texto, cf, ct, cb))

    meteoros_transformados = []
    for x_met, y_met, abrev, cf, ct, cb, sep, radio in meteoros_list:
        if abs(rotacion_global) > 0.5:
            x_met, y_met = rotar_punto(x_met, y_met, cx, cy, rotacion_global)
        if abs(rotacion_landscape) > 0.5:
            x_met, y_met = rotar_punto(x_met, y_met, cx, cy, rotacion_landscape)
# =============================================================================
#         if flip_horizontal or flip_vertical:
#             x_met, y_met = flip_punto(x_met, y_met, cx, cy, flip_horizontal, flip_vertical)
# =============================================================================
        x_met, y_met = x_met, y_met + desplazamiento_y
        meteoros_transformados.append((x_met, y_met, abrev, cf, ct, cb, sep, radio))

    # 12. CONSTRUIR SVG FINAL
    ancho_final = view_max_x - view_min_x
    alto_final = view_max_y - view_min_y
    svg_header = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view_min_x} {view_min_y} {ancho_final} {alto_final}" width="100%" height="100%">'
    svg_footer = "</svg>"

    # FONDO
    svg_body = f'<rect x="{view_min_x}" y="{view_min_y}" width="{ancho_final}" height="{alto_final}" fill="#f0f0f0" />'

    # ---------- CABECERA COMENTADA (se añade en el PDF) ----------
    # COMENTADO PARA EL PDF - La cabecera se añade en el PDFGenerator
    # cabecera_y = view_min_y + 30
    # svg_body += f'<text x="{view_min_x + 10}" y="{cabecera_y}" font-size="14" font-weight="bold" fill="black">{cabecera_tour}</text>'
    # svg_body += f'<text x="{view_min_x + 10}" y="{cabecera_y + 18}" font-size="12" fill="black">Secuencia: {cadena_losetas_limpia}</text>'

    # Leyenda de meteoros COMENTADA (se añade en el PDF)
    # if meteoros_por_loseta:
    #     leyenda_y = view_min_y + 48
    #     svg_body += f'<text x="{view_min_x + 10}" y="{leyenda_y}" font-size="12" fill="black" font-weight="bold">Clima:</text>'
    #     for i, (clave, abrev) in enumerate(meteoros_por_loseta.items()):
    #         texto = f"{clave}: {abrev}"
    #         svg_body += f'<text x="{view_min_x + 80 + i*80}" y="{leyenda_y}" font-size="11" fill="black">{texto}</text>'

    # PIEZAS
    svg_body += contenido_piezas

    # ETIQUETAS
    for x, y, texto, cf, ct, cb in etiquetas_transformadas:
        svg_body += f'<rect x="{x - 10}" y="{y - 10}" width="20" height="20" rx="4" fill="{cf}" stroke="{cb}" stroke-width="1.5" />'
        svg_body += f'<text x="{x}" y="{y + 1}" fill="{ct}" font-size="12" font-weight="bold" text-anchor="middle" dominant-baseline="middle">{texto}</text>'

    # METEOROS
    for x_met, y_met, abrev, cf, ct, cb, sep, radio in meteoros_transformados:
        svg_body += f'<circle cx="{x_met - sep/2}" cy="{y_met}" r="{radio}" fill="{cf}" stroke="{cb}" />'
        svg_body += f'<circle cx="{x_met + sep/2}" cy="{y_met}" r="{radio}" fill="{cf}" stroke="{cb}" />'
        svg_body += f'<text x="{x_met}" y="{y_met + 1}" fill="{ct}" font-size="9" font-weight="bold" text-anchor="middle" dominant-baseline="middle">{abrev}</text>'

    # GUARDAR
    os.makedirs(SVGreader.DIR_RESULTS, exist_ok=True)
    ruta_salida = os.path.join(SVGreader.DIR_RESULTS, nombre_archivo)
    svg_completo = svg_header + svg_body + svg_footer
    with open(ruta_salida, 'w', encoding='utf-8') as f:
        f.write(svg_completo)

    print(f"✅ SVG guardado como '{ruta_salida}'")
    return ruta_salida, rumbo_acumulado



def generar_json_etapa(secuencia, nombre_tour, sesion, etapa, rumbo_final, 
                       meteoros_por_loseta=None, nombre_personalizado=""):
    if meteoros_por_loseta is None:
        meteoros_por_loseta = {}
    
    # Usar nombre personalizado si existe
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
        "weather": meteoros_por_loseta
    }
    
    os.makedirs(SVGreader.DIR_RESULTS, exist_ok=True)
    nombre_json = f"circuito_etapa_{etapa}.json"
    ruta_json = os.path.join(SVGreader.DIR_RESULTS, nombre_json)
    with open(ruta_json, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ JSON guardado como '{ruta_json}'")
    return ruta_json

def asignar_meteoros(secuencia):
    if len(secuencia) < 3:
        return {}
    elegibles = []
    for idx, clave in enumerate(secuencia):
        if idx == 0 or idx == len(secuencia)-1:
            continue
        forma = Biblioteca.Losetas[clave][1]
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

if __name__ == "__main__":
    config_tour = Survey.ejecutar_cuestionario()
    creador_logico = arquitecto.crear_arquitecto(config_tour["expansiones_activas"])

    etapa_global = 1
    etapas_generadas = []  # Para el PDF
    
    for sesion in range(1, config_tour["total_sesiones"] + 1):
        for etapa_en_sesion in range(1, config_tour["etapas_por_sesion"] + 1):
            print(f"\nGenerando matemáticas para: Sesión {sesion}, Etapa {etapa_en_sesion}...")
            secuencia_perfecta = creador_logico.generar_circuito_valido()

            if secuencia_perfecta:
                meteoros_por_loseta = {}
                if config_tour["expansiones_activas"].get("Meteo", False):
                    #if random.random() < 0.3:
                    if random.random() < 1:
                        print("🌦️  Esta etapa tendrá fenómenos climáticos.")
                        meteoros_por_loseta = asignar_meteoros(secuencia_perfecta)
                    else:
                        print("☀️  Esta etapa no tendrá clima especial.")

                # Obtener nombre personalizado
                clave_etapa = f"S{sesion}E{etapa_global}"
                nombre_personalizado = config_tour["nombres_etapas"].get(clave_etapa, "")
                
                # Construir cabecera
                if nombre_personalizado:
                    nombre_etapa = f"{nombre_personalizado} (S:{sesion} E:{etapa_en_sesion})"
                else:
                    nombre_etapa = f"Sesión {sesion} - Etapa {etapa_en_sesion}"
                
                cabecera = f"Tour: {config_tour['nombre_tour']} | {nombre_etapa}"
                cadena_limpia = Survey.formatear_secuencia_limpia(secuencia_perfecta)
                nombre_svg = f"circuito_etapa_{etapa_global}.svg"
                
                ruta_svg, rumbo_final = construir_y_guardar_circuito_svg(
                    secuencia_perfecta, cabecera, cadena_limpia, nombre_svg,
                    meteoros_por_loseta=meteoros_por_loseta
                )
                
                if ruta_svg:
                    generar_json_etapa(
                        secuencia_perfecta,
                        config_tour['nombre_tour'],
                        sesion,
                        etapa_global,
                        rumbo_final,
                        meteoros_por_loseta=meteoros_por_loseta,
                        nombre_personalizado=nombre_personalizado
                    )
                    
                    # Guardar para el PDF
                    etapas_generadas.append({
                        "sesion": sesion,
                        "etapa": etapa_global,
                        "secuencia": secuencia_perfecta,
                        "meteoros": meteoros_por_loseta,
                        "svg_path": ruta_svg,
                        "nombre_personalizado": nombre_personalizado
                    })
                    
                etapa_global += 1
            else:
                print(f"No se pudo generar la Etapa {etapa_global}. Cancelando Tour.")
                break
    
    # Generar PDF al final
    if etapas_generadas:
        try:
            import PDFGenerator
            PDFGenerator.generar_plan_carrera(
                config_tour['nombre_tour'], 
                etapas_generadas, 
                f"plan_carrera_{config_tour['nombre_tour']}.pdf"
            )
        except Exception as e:
            print(f"⚠️ Error al generar PDF: {e}")
