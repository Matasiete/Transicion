# -*- coding: utf-8 -*-
"""
Created on Sat Jun 20 19:38:40 2026

@author: Matasiete
Proyecto McPy.


Versiones:


"""

# -*- coding: utf-8 -*-
"""
Created on Thu Jun 18 18.54 2026

@author: Matasiete
Proyecto McPy.


Versiones: V22 
    

Eventos: 
    Post:   Renombrado de Arcs21provisional a app.py
            Separacion de generadores.py
            Separacion de geometria.py
            Separacion de catalog.py
            
            Incorporacion de icon.png
            Seeparacion de config.py
            
"""
# app.py

# 0. IMPORTACIONES EXTERNAS

import pygame
import sys
import math
import os

# 1. IMPORTACIÓNES INTERNAS
import config
import catalog
import geometria
import generadores

### ============================================================================
###### Inicialización del entorno
### ============================================================================

# --- CONFIGURACIÓN DE LA INTERFAZ ---

def inicializar_entorno():
    pygame.init()

    icon = pygame.image.load('ICON.png')
    pygame.display.set_icon(icon)

    screen = pygame.display.set_mode(
        (config.ANCHO_PANTALLA, config.ALTO_PANTALLA)
    )
    pygame.display.set_caption(config.WIN_CAPTION)
   
    clock = pygame.time.Clock()

    return screen, clock


def crear_superficies_base():
    surf_recta = generadores.dibujar_recta(
    19 * config.ESCALA,
    6 * config.ESCALA,
    config.AMARILLO_DERECHO,
    config.GRIS_LINEAS,
    GROSOR_AMARILLO,
    GROSOR_LINEA,
    GROSOR_DECORATIVO
)
    
    #surf_recta = pygame.Surface((LARGO_RECTA, ANCHO_VIA), pygame.SRCALPHA)

    tam_seguro = 2000
    surf_rtd_gt, enganche_rtd = generadores.dibujar_rotonda(
        "D",
        config.ESCALA,
        tam_seguro,
        config.GRIS_LINEAS,
        config.AMARILLO_DERECHO
    )
    surf_rti_gt, enganche_rti = generadores.dibujar_rotonda(
        "I",
        config.ESCALA,
        tam_seguro,
        config.GRIS_LINEAS,
        config.AMARILLO_DERECHO
    )

    w_rtd, h_rtd = surf_rtd_gt.get_width(), surf_rtd_gt.get_height()
    w_rti, h_rti = surf_rti_gt.get_width(), surf_rti_gt.get_height()

    ex_rtd = enganche_rtd["entrada_x"]
    ey_rtd = enganche_rtd["entrada_y"]
    sx_rtd = enganche_rtd["salida_x"]
    sy_rtd = enganche_rtd["salida_y"]

    ex_rti = enganche_rti["entrada_x"]
    ey_rti = enganche_rti["entrada_y"]
    sx_rti = enganche_rti["salida_x"]
    sy_rti = enganche_rti["salida_y"]

#=================================================================
#=================================================================
#=================================================================

    surf_rc_real = generadores.dibujar_recta(
        9.6 * config.ESCALA,
        6 * config.ESCALA,
        config.AMARILLO_DERECHO,
        config.GRIS_LINEAS,
        GROSOR_AMARILLO,
        GROSOR_LINEA,
        GROSOR_DECORATIVO
    )
    #surf_rc_real = pygame.Surface((ANCHO_RC_REAL, ALTO_RC_REAL), pygame.SRCALPHA)

    return {
        "surf_recta": surf_recta,
        "surf_rc_real": surf_rc_real,
        "surf_rtd_gt": surf_rtd_gt,
        "surf_rti_gt": surf_rti_gt,
        "w_rtd": w_rtd,
        "h_rtd": h_rtd,
        "ex_rtd": ex_rtd,
        "ey_rtd": ey_rtd,
        "sx_rtd": sx_rtd,
        "sy_rtd": sy_rtd,
        "w_rti": w_rti,
        "h_rti": h_rti,
        "ex_rti": ex_rti,
        "ey_rti": ey_rti,
        "sx_rti": sx_rti,
        "sy_rti": sy_rti,
    }


def crear_catalogo_piezas(superficies):
    return catalog.inicializar_catalogo(
        superficies["surf_recta"],
        superficies["surf_rc_real"],
        superficies["surf_rtd_gt"],
        superficies["surf_rti_gt"],
        superficies["w_rtd"],
        superficies["h_rtd"],
        superficies["ex_rtd"],
        superficies["ey_rtd"],
        superficies["sx_rtd"],
        superficies["sy_rtd"],
        superficies["w_rti"],
        superficies["h_rti"],
        superficies["ex_rti"],
        superficies["ey_rti"],
        superficies["sx_rti"],
        superficies["sy_rti"],
    )

screen, clock = inicializar_entorno()


# ============================================================================
### Declaracones
# ============================================================================

# --- CONSTANTES DE DISEÑO INTERNAS ---
ANCHO_VIA = 6 * config.ESCALA  
GROSOR_LINEA = 2         
GROSOR_DECORATIVO = 1    
GROSOR_AMARILLO = 3      
ANGULO_INICIAL = 0 
# Dimensiones reales físicas de la Recta Corta (RC)
ANCHO_RC_REAL = int(9.6 * config.ESCALA)
ALTO_RC_REAL = int(ANCHO_VIA)  # = 6 * config.ESCALA

## ============================================================
## ### Catalogo Piezas A  START
## ============================================================

# Definiciones Ad-HOC
LARGO_RECTA = 19 * config.ESCALA
TAM_SEGURO = 2000

## ============================================================
## ### Cadena de piezas a dibujar.
## ============================================================
#CADENA_ENTRADA = "R, CD90, CD90, R, RTI, RC, R"
#CADENA_ENTRADA = "R, CD90, CD90, CD90, RC, R"
CADENA_ENTRADA = "R, SCD, R, CD90, RC, CD90, SCI, RTD, R"  # Entrada parametrizada del usuario
#CADENA_ENTRADA = "R, RC, R, CD90, RC, RC, CI45, RC"



# =============================================================================
# =============================================================================


superficies = crear_superficies_base()

surf_recta = superficies["surf_recta"]
surf_rc_real = superficies["surf_rc_real"]
surf_rtd_gt = superficies["surf_rtd_gt"]
surf_rti_gt = superficies["surf_rti_gt"]

w_rtd = superficies["w_rtd"]
h_rtd = superficies["h_rtd"]
ex_rtd = superficies["ex_rtd"]
ey_rtd = superficies["ey_rtd"]
sx_rtd = superficies["sx_rtd"]
sy_rtd = superficies["sy_rtd"]

w_rti = superficies["w_rti"]
h_rti = superficies["h_rti"]
ex_rti = superficies["ex_rti"]
ey_rti = superficies["ey_rti"]
sx_rti = superficies["sx_rti"]
sy_rti = superficies["sy_rti"]


CATALOGO_PIEZAS = crear_catalogo_piezas(superficies)


# =============================================================================
# ====================   MOLDES DE PIEZAS  1 START ===================================
# =============================================================================

# --- FABRICACIÓN DE MOLDES MAESTROS ---

# =============================================================================
# 1. PROTO GENERAL: RECTA (R) - Convenio General (Entrada Abierta, Salida Cerrada)
# =============================================================================

#LARGO_RECTA = 19 * config.ESCALA
#surf_recta = pygame.Surface((LARGO_RECTA, ANCHO_VIA), pygame.SRCALPHA)
cx_local, cy_local = 0, ANCHO_VIA

# Márgenes longitudinales de la calzada
pygame.draw.line(surf_recta, config.AMARILLO_DERECHO, (cx_local, cy_local), (cx_local + LARGO_RECTA, cy_local), 5)
pygame.draw.line(surf_recta, config.AMARILLO_DERECHO, (cx_local, cy_local), (cx_local + LARGO_RECTA, cy_local), GROSOR_AMARILLO)
pygame.draw.line(surf_recta, config.GRIS_LINEAS, (cx_local, cy_local - ANCHO_VIA), (cx_local + LARGO_RECTA, cy_local - ANCHO_VIA), GROSOR_LINEA)

# ❌ Entrada Abierta: Aquí NO se dibuja ninguna línea en cx_local
# 🟢 Salida Cerrada: Sella su final de forma estricta con 1 píxel fino
pygame.draw.line(surf_recta, config.GRIS_LINEAS, (cx_local + LARGO_RECTA, cy_local), (cx_local + LARGO_RECTA, cy_local - ANCHO_VIA), GROSOR_DECORATIVO)

# Eje central divisorio de carriles
pygame.draw.line(surf_recta, config.GRIS_LINEAS, (cx_local, cy_local - ANCHO_VIA / 2), (cx_local + LARGO_RECTA, cy_local - ANCHO_VIA / 2), GROSOR_DECORATIVO)

# Subdivisión interna de las 6 casillas de juego
ancho_casilla = LARGO_RECTA / 6.0
for i in range(1, 6):
    x_t = cx_local + i * ancho_casilla
    pygame.draw.line(surf_recta, config.GRIS_LINEAS, (x_t, cy_local), (x_t, cy_local - ANCHO_VIA), GROSOR_DECORATIVO)


# =============================================================================
# ====================   MOLDES DE PIEZAS 1 END  ===================================
# =============================================================================




# --- PROCESAMIENTO DINÁMICO DE LA PISTA ---

despieze = [token.strip().upper() for token in CADENA_ENTRADA.split(",") if token.strip()]

punto_conexion_actual = pygame.Vector2(450, 550)
angulo_carrera_actual = ANGULO_INICIAL

# ////////////////////////////////////////////////////////////


# =============================================================================
# ====================   MOLDES DE PIEZAS  2 START ===================================
# =============================================================================


    # --- FABRICACIÓN GRÁFICA DE SUPERFICIE PARA RECTA CORTA (RC) REAL (9.6 U) ---
cfg_rc = CATALOGO_PIEZAS["RC"]
surf_rc_local = cfg_rc["superficie"]
#pygame.Surface((int(cfg_rc["ancho"]), int(cfg_rc["alto"])), pygame.SRCALPHA)

l_corta = 9.6 * config.ESCALA
ancho_via_local = 6 * config.ESCALA

# Líneas perimetrales (Regla de Oro: derecha es Amarilla)
pygame.draw.line(surf_rc_local, config.GRIS_LINEAS, (0, 0), (l_corta, 0), GROSOR_LINEA)
pygame.draw.line(surf_rc_local, config.AMARILLO_DERECHO, (0, ancho_via_local), (l_corta, ancho_via_local), GROSOR_LINEA + 1)

# Bocas de cierre de la loseta de cartón
pygame.draw.line(surf_rc_local, config.GRIS_LINEAS, (0, 0), (0, ancho_via_local), GROSOR_LINEA)
pygame.draw.line(surf_rc_local, config.GRIS_LINEAS, (l_corta, 0), (l_corta, ancho_via_local), GROSOR_LINEA)

# Línea central divisoria de carriles
pygame.draw.line(surf_rc_local, config.GRIS_LINEAS, (0, ancho_via_local // 2), (l_corta, ancho_via_local // 2), GROSOR_LINEA)

# 2 travesaños internos para formar exactamente las 3 casillas reales de carrera (3.2 unidades cada una)
ancho_casilla_rc = l_corta / 3.0
for i in range(1, 3):
    x_t = i * ancho_casilla_rc
    pygame.draw.line(surf_rc_local, config.GRIS_LINEAS, (x_t, 0), (x_t, ancho_via_local), GROSOR_LINEA)


# =============================================================================
# ====================   MOLDES DE PIEZAS  2 END ===================================
# =============================================================================


# Guardar la superficie e inyectar el promedio de enganche en el motor
CATALOGO_PIEZAS["RC"]["superficie"] = surf_rc_local
CATALOGO_PIEZAS["RC"]["promedio_entrada_local"] = (cfg_rc["ent_local_A"] + cfg_rc["ent_local_B"]) / 2.0




# ////////////////////////////////////////////////////////////

# --- INVOCACIÓN GRÁFICA DIRECTA DE TU FUNCIÓN NATIVA PARA CALLEJONES (SCD / SCI) ---
for mano_cod in ["SCD", "SCI"]:
    cfg_sc = CATALOGO_PIEZAS[mano_cod]
    letra_mano = "D" if mano_cod == "SCD" else "I"
    
    # CORRECCIÓN: Se sustituye TAM_SURF por el valor literal 800 píxeles exigido por el lienzo
    surf_fabricada = generadores.dibujar_sharp_corners(letra_mano, config.ESCALA, GROSOR_LINEA, 800, config.GRIS_LINEAS, config.AMARILLO_DERECHO)
    
    # Inyectar la superficie y calcular el promedio de entrada exigido por el motor rígido
    CATALOGO_PIEZAS[mano_cod]["superficie"] = surf_fabricada
    CATALOGO_PIEZAS[mano_cod]["promedio_entrada_local"] = (cfg_sc["ent_local_A"] + cfg_sc["ent_local_B"]) / 2.0

# ////////////////////////////////////////////////////////////

piezas_calculadas = []

# --- BLOQUE 2: FABRICACIÓN GRÁFICA DE SUPERFICIES PARA CURVAS ESTÁNDAR ---
# CORRECCIÓN DEFINITIVA: Unificación de grosores y calibración de centros de arco
for codigo in ["CD90", "CI90", "CD45", "CI45"]:
    cfg = CATALOGO_PIEZAS[codigo]
    ancho_local = int(cfg["ancho"])
    alto_local = int(cfg["alto"])
    
    # Crear la superficie local transparente
    surf_local = pygame.Surface((ancho_local, alto_local), pygame.SRCALPHA)
    
    es_90 = '90' in codigo
    es_izq = 'I' in codigo
    r_int = 2 * config.ESCALA if es_90 else 6 * config.ESCALA
    r_ext = 8 * config.ESCALA if es_90 else 12 * config.ESCALA
    angulo_giro = 90 if es_90 else 45

    # Configuración de centros de arco locales según quiralidad
    if es_izq:
        cx_arco, cy_arco = 0.0, alto_local - r_ext
        ang_i, ang_f = 270, 270 + angulo_giro
    else:
        cx_arco, cy_arco = 0.0, r_ext
        ang_i, ang_f = 90 - angulo_giro, 90

    # Generación de puntos del arco vectorial
    puntos_ext = []
    puntos_int = []
    for grado in range(int(ang_i), int(ang_f) + 1):
        rad = math.radians(grado)
        puntos_ext.append((cx_arco + r_ext * math.cos(rad), cy_arco - r_ext * math.sin(rad)))
        puntos_int.append((cx_arco + r_int * math.cos(rad), cy_arco - r_int * math.sin(rad)))

    # Dibujo de líneas perimetrales (Unificado a GROSOR_LINEA estricto para evitar gaps)
    if len(puntos_ext) >= 2:
        pygame.draw.lines(surf_local, config.AMARILLO_DERECHO if es_izq else config.GRIS_LINEAS, False, puntos_ext, GROSOR_LINEA)
        pygame.draw.lines(surf_local, config.GRIS_LINEAS if es_izq else config.AMARILLO_DERECHO, False, puntos_int, GROSOR_LINEA)

    # Bocas de entrada y salida (Líneas de cierre estancas)
    pygame.draw.line(surf_local, config.GRIS_LINEAS, puntos_ext[0], puntos_int[0], GROSOR_LINEA)
    pygame.draw.line(surf_local, config.GRIS_LINEAS, puntos_ext[-1], puntos_int[-1], GROSOR_LINEA)

    # Línea central transmedia en curva
    r_med = (r_int + r_ext) / 2.0
    puntos_centro = []
    for grado in range(int(ang_i), int(ang_f) + 1):
        rad = math.radians(grado)
        puntos_centro.append((cx_arco + r_med * math.cos(rad), cy_arco - r_med * math.sin(rad)))
    if len(puntos_centro) >= 2:
        pygame.draw.lines(surf_local, config.GRIS_LINEAS, False, puntos_centro, GROSOR_LINEA)

    # Travesaño intermedio angular para dividir las casillas
    grado_medio = ang_i + (angulo_giro / 2.0)
    rad_m = math.radians(grado_medio)
    pygame.draw.line(surf_local, config.GRIS_LINEAS, 
                     (cx_arco + r_int * math.cos(rad_m), cy_arco - r_int * math.sin(rad_m)), 
                     (cx_arco + r_ext * math.cos(rad_m), cy_arco - r_ext * math.sin(rad_m)), GROSOR_LINEA)

    # Asignar la superficie fabricada y calcular el promedio requerido
    CATALOGO_PIEZAS[codigo]["superficie"] = surf_local
    CATALOGO_PIEZAS[codigo]["promedio_entrada_local"] = (cfg["ent_local_A"] + cfg["ent_local_B"]) / 2.0

# ////////////////////////////////////////////////////////////

for tipo in despieze:
    resultado = geometria.procesar_y_conectar_pieza(
    tipo,
    punto_conexion_actual,
    angulo_carrera_actual,
    CATALOGO_PIEZAS
    )
    if resultado is not None:
        surf_rot, rect_p, sal_C, sal_D, siguiente_angulo = resultado
        piezas_calculadas.append({
            "superficie": surf_rot,
            "rect": rect_p,
            "sal_C": sal_C,
            "sal_D": sal_D
        })
        
    
        punto_conexion_actual = (sal_C + sal_D) / 2.0
        angulo_carrera_actual = siguiente_angulo






        #Debug
        # Inserta esto justo después de calcular el punto_conexion_actual en tu bucle de despiece
        print(f"Pieza: {tipo:5} | Conexión global entrante: X={punto_conexion_actual.x:.4f}, Y={punto_conexion_actual.y:.4f}")

# =========================================================================
# --- CÁLCULO DE CAJA CONTENEDORA Y MATRIZ DE VISUALIZACIÓN (CORREGIDO) ---
# =========================================================================
todos_los_puntos = []
for p in piezas_calculadas:
    rect = p["rect"]
    # Añadimos las cuatro esquinas del rectángulo de la pieza (abarca toda su geometría)
    todos_los_puntos.append(pygame.Vector2(rect.left, rect.top))
    todos_los_puntos.append(pygame.Vector2(rect.right, rect.top))
    todos_los_puntos.append(pygame.Vector2(rect.left, rect.bottom))
    todos_los_puntos.append(pygame.Vector2(rect.right, rect.bottom))
    # También mantenemos los puntos de salida por seguridad
    todos_los_puntos.append(p["sal_C"])
    todos_los_puntos.append(p["sal_D"])

# Si hay al menos una pieza, calculamos la caja
if todos_los_puntos:
    xs = [p.x for p in todos_los_puntos]
    ys = [p.y for p in todos_los_puntos]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    # Añadir un margen en el mundo para que los bordes no queden pegados
    MARGEN_MUNDO = 10  # píxeles adicionales en el espacio del mundo
    min_x -= MARGEN_MUNDO
    max_x += MARGEN_MUNDO
    min_y -= MARGEN_MUNDO
    max_y += MARGEN_MUNDO

    ancho_pista = max_x - min_x if (max_x - min_x) > 0 else 1.0
    alto_pista = max_y - min_y if (max_y - min_y) > 0 else 1.0
    centro_pista = pygame.Vector2((min_x + max_x) / 2.0, (min_y + max_y) / 2.0)
else:
    # Fallback en caso de que no haya piezas
    ancho_pista, alto_pista = 1.0, 1.0
    centro_pista = pygame.Vector2(0, 0)
    
# ////////////////////////////////////////////////////////////

# --- CÁLCULO CEÑIDO AL CIRCUITO REAL MEDIANTE DICCIONARIOS DE ENTORNO ---
if piezas_calculadas:
    # En tu script real, cada elemento de la lista es un diccionario.
    # Extraemos el centro en X e Y leyendo la clave de texto "rect"
    puntos_x = [pieza["rect"].centerx for pieza in piezas_calculadas]
    puntos_y = [pieza["rect"].centery for pieza in piezas_calculadas]
    
    # Margen de protección física ceñido para que las curvas anchas no se recorten en los bordes
    margen_loseta = 15.0 * config.ESCALA 
    
    min_x = min(puntos_x) - margen_loseta
    max_x = max(puntos_x) + margen_loseta
    min_y = min(puntos_y) - margen_loseta
    max_y = max(puntos_y) + margen_loseta

    ancho_pista = max_x - min_x if (max_x - min_x) > 0 else 1.0
    alto_pista = max_y - min_y if (max_y - min_y) > 0 else 1.0
    
    # Imponer el 5% de margen lateral mínimo por cada lado (90% de pantalla útil total)
    escala_x = (config.WIDTH * 0.90) / ancho_pista
    escala_y = (config.HEIGHT * 0.90) / alto_pista
    FACTOR_CAMARA = min(escala_x, escala_y)
    
    centro_pista = pygame.Vector2((min_x + max_x) / 2.0, (min_y + max_y) / 2.0)
    centro_pantalla = pygame.Vector2(config.WIDTH / 2.0, config.HEIGHT / 2.0)

# ////////////////////////////////////////////////////////////

# --- EXPORTACIÓN AUTOMÁTICA A PNG INCREMENTAL ---
superficie_export = pygame.Surface((config.WIDTH, config.HEIGHT))
superficie_export.fill(config.COLOR_FONDO)

for idx, pieza in enumerate(piezas_calculadas):
    w_original, h_original = pieza["superficie"].get_size()
    surf_escalada = pygame.transform.scale(pieza["superficie"], (int(w_original * FACTOR_CAMARA), int(h_original * FACTOR_CAMARA)))
    rect_escalado = surf_escalada.get_rect()
    centro_pieza_mundo = pygame.Vector2(pieza["rect"].center)
    centro_pieza_camara = centro_pantalla + (centro_pieza_mundo - centro_pista) * FACTOR_CAMARA
    #rect_escalado.center = (int(centro_pieza_camara.x), int(centro_pieza_camara.y))
    rect_escalado.center = (int(round(centro_pieza_camara.x)), int(round(centro_pieza_camara.y)))

    
    superficie_export.blit(surf_escalada, rect_escalado.topleft)
    
    p_C_camara = centro_pantalla + (pieza["sal_C"] - centro_pista) * FACTOR_CAMARA
    p_D_camara = centro_pantalla + (pieza["sal_D"] - centro_pista) * FACTOR_CAMARA
    pygame.draw.line(superficie_export, config.GRIS_LINEAS, p_C_camara, p_D_camara, GROSOR_DECORATIVO)
    
    if idx == 0 and len(despieze) > 0:
        cfg_primera = CATALOGO_PIEZAS[despieze[0]]
        angulo_r1 = ANGULO_INICIAL + cfg_primera["ang_correccion"]
        centro_m1 = pygame.Vector2(pieza["rect"].center)
        p_ent_A_mundo = centro_m1 + geometria.rotar_punto_local(cfg_primera["ent_local_A"], cfg_primera["centro_local"], angulo_r1)
        p_ent_B_mundo = centro_m1 + geometria.rotar_punto_local(cfg_primera["ent_local_B"], cfg_primera["centro_local"], angulo_r1)
        p_A_camara = centro_pantalla + (p_ent_A_mundo - centro_pista) * FACTOR_CAMARA
        p_B_camara = centro_pantalla + (p_ent_B_mundo - centro_pista) * FACTOR_CAMARA
        pygame.draw.line(superficie_export, config.GRIS_LINEAS, p_A_camara, p_B_camara, GROSOR_DECORATIVO)

nombre_script = "Arc17_Jauja_remejorado"
contador = 1
while os.path.exists(f"{nombre_script}_{contador}.png"):
    contador += 1
nombre_archivo_final = f"{nombre_script}_{contador}.png"
pygame.image.save(superficie_export, nombre_archivo_final)
print(f"[SISTEMA] Archivo exportado con éxito: {nombre_archivo_final}")





# ////////////////////////////////////////////////////////////
# ////////////////////////////////////////////////////////////
# ////////////////////////////////////////////////////////////
# ////////////////////////////////////////////////////////////







# # ==========================================
# # --- LOGICA DE VISUALIZACIÓN DINÁMICA DE LA CARRERA ---
# ////////////////////////////////////////////////////////////

# --- BUCLE DE INTERFAZ GRÁFICA INTERACTIVA CON AUTOCIERRE ---
paso_actual = 1
running = True
tiempo_ultima_actividad = pygame.time.get_ticks()

while running:
    tiempo_inactivo = (pygame.time.get_ticks() - tiempo_ultima_actividad) / 1000.0
    if tiempo_inactivo >= 60.0:
        print("=== APAGADO AUTOMÁTICO: Ventana cerrada por inactividad tras 1 minuto ===")
        running = False
        break

    screen.fill(config.COLOR_FONDO)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            tiempo_ultima_actividad = pygame.time.get_ticks()
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_SPACE:
                if paso_actual < len(piezas_calculadas):
                    paso_actual += 1

    for idx in range(paso_actual):
        if idx < len(piezas_calculadas):
            pieza = piezas_calculadas[idx]
            w_orig, h_orig = pieza["superficie"].get_size()
            surf_vis = pygame.transform.scale(pieza["superficie"], (int(w_orig * FACTOR_CAMARA), int(h_orig * FACTOR_CAMARA)))
            rect_vis = surf_vis.get_rect()
            
            centro_m = pygame.Vector2(pieza["rect"].center)
            centro_c = centro_pantalla + (centro_m - centro_pista) * FACTOR_CAMARA
            #rect_vis.center = (int(centro_c.x), int(centro_c.y))
            rect_vis.center = (int(round(centro_c.x)), int(round(centro_c.y)))
            
            screen.blit(surf_vis, rect_vis.topleft)
            
            p_C_camara = centro_pantalla + (pieza["sal_C"] - centro_pista) * FACTOR_CAMARA
            p_D_camara = centro_pantalla + (pieza["sal_D"] - centro_pista) * FACTOR_CAMARA
            pygame.draw.line(screen, config.GRIS_LINEAS, p_C_camara, p_D_camara, GROSOR_DECORATIVO)

            if idx == 0 and len(despieze) > 0:
                cfg_primera = CATALOGO_PIEZAS[despieze[0]]
                angulo_r1 = ANGULO_INICIAL + cfg_primera["ang_correccion"]
                centro_m1 = pygame.Vector2(pieza["rect"].center)
                p_ent_A_mundo = centro_m1 + geometria.rotar_punto_local(cfg_primera["ent_local_A"], cfg_primera["centro_local"], angulo_r1)
                p_ent_B_mundo = centro_m1 + geometria.rotar_punto_local(cfg_primera["ent_local_B"], cfg_primera["centro_local"], angulo_r1)
                pygame.draw.line(screen, config.GRIS_LINEAS, centro_pantalla + (p_ent_A_mundo - centro_pista) * FACTOR_CAMARA, centro_pantalla + (p_ent_B_mundo - centro_pista) * FACTOR_CAMARA, GROSOR_DECORATIVO)

            #Debug
            #pygame.draw.circle(screen, config.ROSA, (int(p_C_camara.x), int(p_C_camara.y)), int(max(3, 5 * FACTOR_CAMARA)))
            #pygame.draw.circle(screen, config.ROJO, (int(p_D_camara.x), int(p_D_camara.y)), int(max(3, 5 * FACTOR_CAMARA)))

    # --- TEXTO INFORMATIVO DE PRESENTACIÓN ---
    font = pygame.font.SysFont(None, 22)
    txt_info = f"Paso: {paso_actual}/{len(piezas_calculadas)} | String: '{CADENA_ENTRADA}' | Archivo: {nombre_archivo_final}"
    txt = font.render(txt_info, True, config.COLOR_LINEA)
    screen.blit(txt, (20, 20))
    
    pygame.display.flip()
    clock.tick(60)

# Cierre limpio del hilo tras salir del bucle while running
pygame.quit()
sys.exit()

# ////////////////////////////////////////////////////////////
# --- DESPUÉS (LÍNEAS QUE NO CAMBIAN) ---
# # FIN DEL ARCHIVO
# ////////////////////////////////////////////////////////////
              
