# -*- coding: utf-8 -*-
"""
Módulo para generar el Plan de Carrera en PDF.
Independiente de SVGmain.py.
"""

import os
import math
import json
import tempfile
import io
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm, cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.graphics.shapes import Drawing, Rect, String, Circle
from reportlab.lib.utils import ImageReader
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_agg import FigureCanvasAgg
import SVGreader
import Biblioteca

# ============================================================================
# CONSTANTES Y CONFIGURACIÓN
# ============================================================================

# Dimensiones de la página A4 (en puntos, 1 punto = 1/72 pulgada)
A4_ANCHO, A4_ALTO = A4
MARGEN = 15 * mm  # 15 mm de margen
ANCHO_DISPONIBLE = A4_ANCHO - 2 * MARGEN
ALTO_DISPONIBLE = A4_ALTO - 2 * MARGEN

# Colores por tipo de terreno (para el perfil)
COLORES_TERRENO = {
    "i": "#4CAF50",  # inicio - verde
    "p": "#8BC34A",  # plano - verde claro
    "d": "#FF9800",  # demarraje - naranja
    "s": "#F44336",  # subida - rojo
    "b": "#2196F3",  # bajada - azul
    "a": "#9C27B0",  # adoquín - púrpura
    "m": "#FFD700",  # meta - dorado
    "r": "#795548",  # repostaje - marrón
    "e": "#607D8B",  # escurridizo - gris azulado
}

NOMBRES_TERRENO = {
    "i": "Inicio",
    "p": "Plano",
    "d": "Demarraje",
    "s": "Subida",
    "b": "Bajada",
    "a": "Adoquín",
    "m": "Meta",
    "r": "Repostaje",
    "e": "Escurridizo",
}

NOMBRES_METEORO = {
    "CT": "Clima tranquilo",
    "VF": "Viento de frente",
    "VL": "Viento lateral",
    "VC": "Viento de cola",
    "SM": "Suelo mojado",
}

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def calcular_perfil(secuencia_claves):
    """
    Calcula el perfil de elevación a partir de la secuencia de losetas.
    Retorna: lista de (posición, elevación, terreno)
    """
    perfil = []
    elevacion = 0
    posicion = 0
    
    for clave in secuencia_claves:
        datos = Biblioteca.Losetas[clave]
        terrenos = datos[2]  # tupla de terrenos
        casillas = datos[3]  # tupla de casillas
        
        for i, terreno in enumerate(terrenos):
            # Calcular incremento de elevación según terreno
            if terreno == "s":  # subida
                elevacion += 1
            elif terreno == "b":  # bajada
                elevacion -= 1
            # else: plano o demarraje (sin cambio)
            
            perfil.append({
                "posicion": posicion,
                "elevacion": elevacion,
                "terreno": terreno,
                "casillas": casillas[i] if i < len(casillas) else 1,
            })
            posicion += casillas[i] if i < len(casillas) else 1
    
    return perfil

def contar_casillas(secuencia_claves):
    """
    Cuenta el total de casillas y por tipo de terreno.
    """
    total = 0
    por_terreno = {t: 0 for t in COLORES_TERRENO.keys()}
    
    for clave in secuencia_claves:
        datos = Biblioteca.Losetas[clave]
        terrenos = datos[2]
        casillas = datos[3]
        
        for i, terreno in enumerate(terrenos):
            num_casillas = casillas[i] if i < len(casillas) else 1
            total += num_casillas
            por_terreno[terreno] = por_terreno.get(terreno, 0) + num_casillas
    
    return total, por_terreno

def dibujar_secuencia_losetas(secuencia_claves, meteoros_por_loseta=None, ancho=None, alto=None):
    """
    Dibuja la secuencia de losetas como una fila de cuadros con borde redondeado.
    Los meteoros se dibujan al lado de su loseta, con separación ajustada.
    Retorna un Drawing de reportlab.
    """
    if meteoros_por_loseta is None:
        meteoros_por_loseta = {}
    
    if ancho is None:
        ancho = ANCHO_DISPONIBLE
    if alto is None:
        alto = 12 * mm
    
    from reportlab.lib.colors import black, white, Color
    
    # Parámetros de tamaño
    tamaño_cuadro = 8  # en puntos (1/72 pulgada)
    separacion = 2      # separación entre losetas
    radio_meteo = 4     # radio del círculo del meteoro
    separacion_meteo = 1  # espacio entre loseta y meteoro
    separacion_despues_meteo = 3  # <-- NUEVO: espacio después del meteoro antes de la siguiente loseta
    
    # Calcular el ancho total necesario
    anchos = []
    for clave in secuencia_claves:
        ancho_loseta = tamaño_cuadro + separacion
        if clave in meteoros_por_loseta:
            # Meteoro ocupa: radio*2 (dos círculos) + separacion_meteo + separacion_despues_meteo
            ancho_loseta += radio_meteo * 2 + separacion_meteo + separacion_despues_meteo
        anchos.append(ancho_loseta)
    
    ancho_total = sum(anchos) - separacion  # restar la última separación
    
    # Si el ancho total es mayor que el ancho disponible, escalar
    if ancho_total > ancho:
        escala = ancho / ancho_total
        tamaño_cuadro *= escala
        separacion *= escala
        radio_meteo *= escala
        separacion_meteo *= escala
        separacion_despues_meteo *= escala
        # Recalcular anchos con la escala
        anchos = []
        for clave in secuencia_claves:
            ancho_loseta = tamaño_cuadro + separacion
            if clave in meteoros_por_loseta:
                ancho_loseta += radio_meteo * 2 + separacion_meteo + separacion_despues_meteo
            anchos.append(ancho_loseta)
        ancho_total = sum(anchos) - separacion
    
    # Crear el drawing
    drawing = Drawing(ancho, alto)
    
    # Posición inicial (centrado)
    x_inicial = (ancho - ancho_total) / 2.0
    y_centro = alto / 2.0
    
    x_actual = x_inicial
    
    for i, clave in enumerate(secuencia_claves):
        y = y_centro - tamaño_cuadro / 2.0
        
        # Determinar color de fondo según si es prima
        if clave.endswith("'"):
            color_fondo = black
            color_texto = white
            texto = clave[0].upper()
        else:
            color_fondo = white
            color_texto = black
            texto = clave
        
        # --- DIBUJAR LA LOSETA (cuadrado) ---
        rect = Rect(x_actual, y, tamaño_cuadro, tamaño_cuadro, 
                    rx=tamaño_cuadro*0.2, ry=tamaño_cuadro*0.2,
                    fillColor=color_fondo, strokeColor=black, strokeWidth=0.5)
        drawing.add(rect)
        
        # Texto de la clave (centrado verticalmente)
        if texto:
            # Ajuste Y para centrar: la línea base está en la mitad inferior del cuadro
            # Usamos y + tamaño_cuadro/2 como centro, y reportlab ajusta la línea base internamente
            texto_objeto = String(x_actual + tamaño_cuadro/2,
                                  y + 1.7, #- tamaño_cuadro/2 * 0.2,
                                  texto,
                                  fontSize=tamaño_cuadro*0.8,
                                  fillColor=color_texto,
                                  fontName='Helvetica-Bold',
                                  textAnchor='middle',
                                  alignment='center')
            drawing.add(texto_objeto)
        
        # Avanzar la posición X después de la loseta
        x_actual += tamaño_cuadro + separacion
        
        # --- DIBUJAR EL METEORO (si existe) ---
        if clave in meteoros_por_loseta:
            abrev = meteoros_por_loseta[clave]
            radio = radio_meteo
            
            # Posición del meteoro (justo después de la loseta)
            cx = x_actual + radio
            cy = y_centro
            
            # Colores según tipo de meteoro
            if abrev == "CT":
                color_meteo = white
                color_texto_meteo = black
            else:
                color_meteo = black
                color_texto_meteo = white
            
            # Primer círculo
            circulo1 = Circle(cx - radio*0.3, cy, radio, 
                             fillColor=color_meteo, strokeColor=black, strokeWidth=0.3)
            drawing.add(circulo1)

            # Segundo círculo (ligeramente desplazado para formar el 8)
            circulo2 = Circle(cx + radio*0.3, cy, radio, 
                             fillColor=color_meteo, strokeColor=black, strokeWidth=0.3)
            drawing.add(circulo2)

            
            # Circulo de "trampantojo" para que no se vea la media lnuna
            circulo_t = Circle(cx - radio*0.3, cy, radio -0.5, 
                             fillColor=color_meteo, strokeColor=color_meteo, strokeWidth=0.2)
            drawing.add(circulo_t)    

            # Texto de la abreviatura (centrado entre los dos círculos)
            texto_meteo = String(cx, cy -2, abrev,
                                 fontSize=radio*1.5,
                                 fillColor=color_texto_meteo,
                                 fontName='Helvetica-Bold',
                                 textAnchor='middle',
                                 alignment='center')
            drawing.add(texto_meteo)
            
            # Avanzar la posición X después del meteoro (incluyendo la separación extra)
            x_actual += radio * 2 + separacion_meteo + separacion_despues_meteo
    
    return drawing

def generar_grafico_perfil(perfil, ancho=None, alto=None):
    """
    Genera un gráfico de perfil de elevación con colores según terreno.
    Retorna un Image de reportlab.platypus (listo para insertar en el PDF).
    """
    if ancho is None:
        ancho = ANCHO_DISPONIBLE
    if alto is None:
        alto = 50 * mm
    
    # Preparar datos
    if not perfil:
        return None
    
    posiciones = [p["posicion"] for p in perfil]
    elevaciones = [p["elevacion"] for p in perfil]
    terrenos = [p["terreno"] for p in perfil]
    
    # Crear figura de matplotlib
    fig, ax = plt.subplots(figsize=(ancho/25.4, alto/25.4), dpi=100)
    
    # Dibujar líneas coloreadas por terreno
    for i in range(len(perfil) - 1):
        x = [posiciones[i], posiciones[i+1]]
        y = [elevaciones[i], elevaciones[i+1]]
        color = COLORES_TERRENO.get(terrenos[i], "#888888")
        ax.plot(x, y, color=color, linewidth=3, solid_capstyle='round')
    
    # Personalizar gráfico
    ax.set_xlabel("Posición (casillas)", fontsize=8)
    ax.set_ylabel("Elevación", fontsize=8)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_facecolor('#f8f9fa')
    
    # Añadir leyenda de colores
    patches = []
    for terreno, color in COLORES_TERRENO.items():
        if terreno in terrenos:
            patches.append(mpatches.Patch(color=color, label=NOMBRES_TERRENO.get(terreno, terreno)))
    if patches:
        ax.legend(handles=patches, loc='upper left', fontsize=6, ncol=3)
    
    # Guardar en buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=120)
    buf.seek(0)
    plt.close(fig)
    
    # Convertir a Image de reportlab.platypus
    img = Image(buf, width=ancho, height=alto)
    
    return img

def cargar_svg_como_drawing(svg_path, ancho_maximo, alto_maximo):
    """
    Carga un archivo SVG y lo convierte a un Drawing de reportlab,
    escalándolo para que quepa en ancho_maximo x alto_maximo.
    """
    try:
        from svglib.svglib import svg2rlg
        
        drawing = svg2rlg(svg_path)
        if drawing is None:
            return None
        
        # Obtener dimensiones originales
        ancho_orig = drawing.width
        alto_orig = drawing.height
        
        if ancho_orig <= 0 or alto_orig <= 0:
            # Si las dimensiones no son válidas, intentar usar boundingBox
            bbox = drawing.getBounds()
            if bbox and len(bbox) == 4:
                ancho_orig = bbox[2] - bbox[0]
                alto_orig = bbox[3] - bbox[1]
            else:
                ancho_orig = 100
                alto_orig = 100
        
        # Calcular factor de escala para que quepa en el espacio disponible
        escala_x = ancho_maximo / ancho_orig
        escala_y = alto_maximo / alto_orig
        escala = min(escala_x, escala_y, 1.0)  # No escalar más de 1.0 (no ampliar)
        
        # Aplicar escala
        if escala < 1.0:
            drawing.scale(escala, escala)
            # Ajustar dimensiones después del escalado
            drawing.width = ancho_orig * escala
            drawing.height = alto_orig * escala
        
        return drawing
        
    except Exception as e:
        print(f"⚠️ Error al cargar SVG {svg_path}: {e}")
        return None

# ============================================================================
# FUNCIÓN PRINCIPAL PARA GENERAR PDF
# ============================================================================

def generar_plan_carrera(nombre_tour, etapas, output_path="plan_carrera.pdf"):
    """
    Genera el PDF del plan de carrera.
    
    Args:
        nombre_tour (str): Nombre del tour (para la portada)
        etapas (list): Lista de diccionarios con los datos de cada etapa:
            {
                "sesion": 1,
                "etapa": 1,
                "secuencia": ["a", "b'", "c", ...],
                "meteoros": {"a": "CT", "c": "VF", ...}  # opcional
                "svg_path": "path/to/circuito_etapa_1.svg"
            }
        output_path (str): Ruta donde guardar el PDF.
    """
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak, KeepTogether
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm, cm
    
    # Configurar documento
    doc = SimpleDocTemplate(output_path, pagesize=A4,
                           leftMargin=15*mm, rightMargin=15*mm,
                           topMargin=15*mm, bottomMargin=15*mm)
    styles = getSampleStyleSheet()
    
    # Estilos
    style_titulo = ParagraphStyle(
        'TituloGrande',
        parent=styles['Title'],
        fontSize=24,
        alignment=TA_CENTER,
        spaceAfter=20
    )
    
    style_subtitulo = ParagraphStyle(
        'Subtitulo',
        parent=styles['Heading2'],
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=10
    )
    
    style_normal = ParagraphStyle(
        'NormalCentrado',
        parent=styles['Normal'],
        alignment=TA_CENTER,
        fontSize=10,
        spaceAfter=8
    )
    
    style_etapa = ParagraphStyle(
        'EtapaTitulo',
        parent=styles['Heading2'],
        fontSize=14,
        alignment=TA_CENTER,
        spaceAfter=5,
        spaceBefore=10
    )
    
    # Lista de elementos del PDF
    elementos = []
    
    # ========================================================================
    # PORTADA
    # ========================================================================
    elementos.append(Spacer(1, 80*mm))
    elementos.append(Paragraph("PLAN DE CARRERA", style_titulo))
    elementos.append(Spacer(1, 30*mm))
    elementos.append(Paragraph(nombre_tour.upper(), style_subtitulo))
    elementos.append(Spacer(1, 30*mm))
    elementos.append(Paragraph("~ ~ ~", style_normal))
    elementos.append(Paragraph("Flamme Rouge - Generador de Circuitos", style_normal))
    elementos.append(Spacer(1, 20*mm))
    elementos.append(Paragraph("(Portada en blanco)", style_normal))
    elementos.append(PageBreak())
    
    # ========================================================================
    # HOJAS DE ETAPAS
    # ========================================================================
    for idx, etapa_data in enumerate(etapas):
        sesion = etapa_data["sesion"]
        etapa = etapa_data["etapa"]
        secuencia = etapa_data["secuencia"]
        meteoros = etapa_data.get("meteoros", {})
        svg_path = etapa_data.get("svg_path")
        
        # Título de la etapa
# =============================================================================
#         titulo = f"Sesión {sesion} - Etapa {etapa}"
#         elementos.append(Paragraph(titulo, style_etapa))
# =============================================================================
# === TÍTULO DE LA ETAPA ===
        nombre_personalizado = etapa_data.get("nombre_personalizado", "")
        if nombre_personalizado:
            titulo = f"{nombre_personalizado} (S:{sesion} E:{etapa})"
        else:
            titulo = f"Sesión {sesion} - Etapa {etapa}"
        elementos.append(Paragraph(titulo, style_etapa))
        elementos.append(Spacer(1, 3*mm))
        
        # === IMAGEN DEL CIRCUITO ===
        if svg_path and os.path.exists(svg_path):
            alto_imagen = 80 * mm
            ancho_imagen = ANCHO_DISPONIBLE
            
            drawing_circuito = cargar_svg_como_drawing(svg_path, ancho_imagen, alto_imagen)
            
            if drawing_circuito:
                elementos.append(drawing_circuito)
            else:
                elementos.append(Paragraph("(Imagen del circuito no disponible)", style_normal))
        else:
            elementos.append(Paragraph("(Imagen del circuito no disponible)", style_normal))
        
        elementos.append(Spacer(1, 3*mm))
        
        # === PERFIL DE ELEVACIÓN ===
        perfil = calcular_perfil(secuencia)
        grafico_perfil = generar_grafico_perfil(perfil, ancho=ANCHO_DISPONIBLE, alto=40*mm)
        if grafico_perfil:
            elementos.append(grafico_perfil)
        else:
            elementos.append(Paragraph("(Perfil no disponible)", style_normal))
        
        elementos.append(Spacer(1, 3*mm))
        
        # === SECUENCIA DE LOSETAS ===
        secuencia_dibujo = dibujar_secuencia_losetas(
            secuencia, meteoros, 
            ancho=ANCHO_DISPONIBLE, 
            alto=10*mm
        )
        if secuencia_dibujo:
            elementos.append(secuencia_dibujo)
        else:
            elementos.append(Paragraph("(Secuencia no disponible)", style_normal))
        
        elementos.append(Spacer(1, 3*mm))
        
        # === ESTADÍSTICAS ===
        total_casillas, casillas_por_terreno = contar_casillas(secuencia)
        
        # Crear tabla de estadísticas (dos columnas)
        data = [
            ["Estadística", "Valor"],
            ["Total de losetas", str(len(secuencia))],
            ["Total de casillas", str(total_casillas)],
        ]
        
        # Añadir casillas por tipo de terreno (solo los que tienen valor > 0)
        for terreno, cantidad in casillas_por_terreno.items():
            if cantidad > 0:
                nombre = NOMBRES_TERRENO.get(terreno, terreno)
                data.append([nombre, str(cantidad)])
        
        # Añadir meteoros si hay
        if meteoros:
            data.append(["", ""])
            data.append(["Clima", ""])
            for clave, abrev in meteoros.items():
                nombre = NOMBRES_METEORO.get(abrev, abrev)
                data.append([f"Loseta {clave}", nombre])
        
        # Crear tabla
        ancho_tabla = min(ANCHO_DISPONIBLE * 0.6, 100*mm)
        tabla = Table(data, colWidths=[ancho_tabla*0.6, ancho_tabla*0.4])
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 3),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elementos.append(tabla)
        
        # Placeholders para valores futuros
        elementos.append(Spacer(1, 2*mm))
        elementos.append(Paragraph("Metas volantes: (por implementar)", style_normal))
        elementos.append(Paragraph("Puntos de sprint: (por implementar)", style_normal))
        elementos.append(Paragraph("Puntos de montaña: (por implementar)", style_normal))
        
        # Salto de página (excepto en la última etapa)
        if idx < len(etapas) - 1:
            elementos.append(PageBreak())
    
    # Generar PDF
    doc.build(elementos)
    print(f"✅ PDF generado en: {output_path}")
    return output_path

# ============================================================================
# FUNCIÓN DE PRUEBA
# ============================================================================

# =============================================================================
# if __name__ == "__main__":
#     # Prueba con datos de ejemplo
#     ejemplo_etapas = [
#         {
#             "sesion": 1,
#             "etapa": 1,
#             "secuencia": ["a", "b'", "c", "d", "e", "f'", "g", "h", "i", "j'", "k", "l", "m", "n'", "o", "p", "q", "r'", "s", "t"],
#             "meteoros": {"b'": "CT", "f'": "VF", "n'": "SM"},
#             "svg_path": "results/circuito_etapa_1.svg"
#         },
#         {
#             "sesion": 1,
#             "etapa": 2,
#             "secuencia": ["a'", "b", "c'", "d'", "e'", "f", "g'", "h'", "i'", "j", "k'", "l'", "m'", "n", "o'", "p'", "q'", "r", "s'", "t'"],
#             "meteoros": {"c'": "CT", "h'": "VC", "m'": "VL"},
#             "svg_path": "results/circuito_etapa_2.svg"
#         }
#     ]
#     
#     generar_plan_carrera("Tour de Prueba", ejemplo_etapas, "plan_carrera_prueba.pdf")
# =============================================================================


if __name__ == "__main__":
    import glob
    import json
    
    # Buscar todos los JSON de etapas en results/
    archivos_json = sorted(glob.glob("results/circuito_etapa_*.json"))
    etapas = []
    
    for json_path in archivos_json:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extraer número de etapa del nombre del archivo
        import re
        match = re.search(r'circuito_etapa_(\d+)\.json', json_path)
        if match:
            etapa_num = int(match.group(1))
            # Necesitamos la secuencia original (no la versión con -upp)
            # Aquí asumimos que la secuencia está en el JSON como "tiles"
            tiles = data.get("tiles", [])
            # Convertir de vuelta: -upp -> '
            secuencia = []
            for tile in tiles:
                if tile.endswith("-upp"):
                    secuencia.append(tile.replace("-upp", "'"))
                else:
                    secuencia.append(tile)
            
            etapas.append({
                "sesion": 1,  # No tenemos ese dato en el JSON, lo ponemos a 1
                "etapa": etapa_num,
                "secuencia": secuencia,
                "meteoros": data.get("weather", {}),
                "svg_path": f"results/circuito_etapa_{etapa_num}.svg"
            })
    
    if etapas:
        generar_plan_carrera("Tour desde archivos", etapas, "plan_carrera_completo.pdf")
    else:
        print("No se encontraron archivos de etapas en results/")
