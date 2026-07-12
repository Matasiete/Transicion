# SVGreader.py
import os
import re
import copy
import xml.etree.ElementTree as ET
from shapely.geometry import Polygon, Point as ShapelyPoint
from svgelements import SVG, Path, Rect

DIR_H = "H_"
DIR_D = "D_"
DIR_L = "L_"
DIR_RESULTS = "results"

_geometria_cache = {}
_contenido_cache = {}

def _construir_ruta(tipo, nombre):
    if tipo == "H":
        return os.path.join(DIR_H, f"{nombre}.svg")
    elif tipo == "D":
        return os.path.join(DIR_D, f"{nombre}.svg")
    elif tipo == "L":
        return os.path.join(DIR_L, f"{nombre}.svg")
    else:
        raise ValueError(f"Tipo desconocido: {tipo}")

def _limpiar_transformaciones(elemento):
    """Elimina recursivamente TODOS los atributos 'transform' de todos los elementos."""
    if 'transform' in elemento.attrib:
        del elemento.attrib['transform']
    for hijo in elemento:
        _limpiar_transformaciones(hijo)
    return elemento

def _limpiar_contenido_svg(contenido):
    """Limpia un SVG: elimina declaraciones XML, extrae hijos de <svg> y elimina transformaciones internas."""
    if not contenido:
        return None
    
    try:
        # 1. Eliminar declaraciones XML
        contenido_limpio = re.sub(r'<\?xml.*?\?>', '', contenido)
        contenido_limpio = contenido_limpio.strip()
        
        # 2. Intentar parsear
        root = ET.fromstring(contenido_limpio)
        
        # 3. Si la raíz es <svg>, extraer sus hijos y eliminar transformaciones
        if root.tag == 'svg':
            # ¡ELIMINAR TODAS LAS TRANSFORMACIONES INTERNAS!
            for child in root:
                _limpiar_transformaciones(child)
            # Extraer el contenido de los hijos
            contenido_interno = ''.join(ET.tostring(child, encoding='unicode') for child in root)
            return contenido_interno
        else:
            return contenido_limpio
            
    except ET.ParseError as e:
        print(f"⚠️ Error parseando SVG: {e}")
        return re.sub(r'<\?xml.*?\?>', '', contenido)

def extraer_geometria_loseta_completa(nombre_forma):
    """
    Carga el archivo H_{nombre_forma}.svg y extrae hitbox, entrada, salida.
    Devuelve diccionario con 'hitbox', 'entrada', 'salida'.
    Usa caché por nombre_forma.
    """
    if nombre_forma in _geometria_cache:
        return copy.deepcopy(_geometria_cache[nombre_forma])

    ruta = _construir_ruta("H", nombre_forma)
    if not os.path.exists(ruta):
        raise FileNotFoundError(f"No se encontró el archivo {ruta}")

    # Cargar el SVG y extraer geometría
    svg = SVG.parse(ruta)
    puntos_hitbox = []
    pt_entrada = None
    pt_salida = None
    objeto_principal_encontrado = False

    for elemento in svg.elements():
        if elemento.id == nombre_forma:
            objeto_principal_encontrado = True

        if elemento.id in ("R", "RC", "CD90", "CI90", "CD45", "CI45", "RTD", "RTI", "SCD", "SCI"):
            if isinstance(elemento, Path):
                for segmento in elemento:
                    if hasattr(segmento, 'start') and segmento.start is not None:
                        puntos_hitbox.append(elemento.transform.transform_point(segmento.start))
                puntos_hitbox = [(float(p[0]), float(p[1])) for p in puntos_hitbox]
            elif isinstance(elemento, Rect):
                puntos_hitbox = [
                    [elemento.x, elemento.y],
                    [elemento.x + elemento.width, elemento.y],
                    [elemento.x + elemento.width, elemento.y + elemento.height],
                    [elemento.x, elemento.y + elemento.height]
                ]
                if elemento.transform:
                    puntos_hitbox = [elemento.transform.transform_point(p) for p in puntos_hitbox]
                puntos_hitbox = [(float(p[0]), float(p[1])) for p in puntos_hitbox]

        if elemento.id == 'Centro-Entrada':
            for sub_el in elemento.select(lambda e: isinstance(e, Path)):
                for segmento in sub_el:
                    if hasattr(segmento, 'start') and segmento.start is not None:
                        pt_transformado = sub_el.transform.transform_point(segmento.start)
                        pt_entrada = ShapelyPoint(float(pt_transformado[0]), float(pt_transformado[1]))
                        break
                if pt_entrada:
                    break

        if elemento.id == 'Centro-Salida':
            for sub_el in elemento.select(lambda e: isinstance(e, Path)):
                for segmento in sub_el:
                    if hasattr(segmento, 'start') and segmento.start is not None:
                        pt_transformado = sub_el.transform.transform_point(segmento.start)
                        pt_salida = ShapelyPoint(float(pt_transformado[0]), float(pt_transformado[1]))
                        break
                if pt_salida:
                    break

    if not objeto_principal_encontrado:
        print(f"⚠️ Advertencia: No se encontró elemento raíz con ID '{nombre_forma}' en {ruta}")

    faltantes = []
    if not puntos_hitbox:
        faltantes.append("hitbox")
    if not pt_entrada:
        faltantes.append("Centro-Entrada")
    if not pt_salida:
        faltantes.append("Centro-Salida")
    if faltantes:
        raise ValueError(f"Faltan elementos críticos en {ruta}: {', '.join(faltantes)}")

    resultado = {
        "hitbox": Polygon(puntos_hitbox),
        "entrada": pt_entrada,
        "salida": pt_salida
    }
    _geometria_cache[nombre_forma] = resultado
    return copy.deepcopy(resultado)

def _cargar_contenido_svg(tipo, nombre):
    """Carga el contenido de un SVG de un tipo y nombre, con caché y limpieza automática."""
    clave = (tipo, nombre)
    if clave in _contenido_cache:
        return _contenido_cache[clave]
    
    ruta = _construir_ruta(tipo, nombre)
    if os.path.exists(ruta):
        try:
            with open(ruta, 'r', encoding='utf-8') as f:
                contenido = f.read()
            # Limpiar y extraer contenido interno
            contenido_limpio = _limpiar_contenido_svg(contenido)
            _contenido_cache[clave] = contenido_limpio
            return contenido_limpio
        except Exception as e:
            print(f"⚠️ Error al leer {ruta}: {e}")
            _contenido_cache[clave] = None
            return None
    else:
        _contenido_cache[clave] = None
        return None

def cargar_svg_representacion(clave, forma):
    """
    Devuelve el contenido SVG más adecuado para la loseta 'clave' con forma 'forma'.
    Prioridad: L_{clave}.svg, D_{forma}.svg, H_{forma}.svg.
    Retorna el contenido como string (ya limpio) o None si no se encuentra.
    """
    # Intentar L_ (específico por clave)
    contenido = _cargar_contenido_svg("L", clave)
    if contenido is not None:
        return contenido
    # Intentar D_ (por forma)
    contenido = _cargar_contenido_svg("D", forma)
    if contenido is not None:
        return contenido
    # Intentar H_ (por forma, fallback)
    contenido = _cargar_contenido_svg("H", forma)
    return contenido
