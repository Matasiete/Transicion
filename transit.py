# -*- coding: utf-8 -*-
"""
Created on Tue Jun 16 15:41:59 2026

@author: SuperUser
"""

import pygame
import sys
import math
import os

# --- CONFIGURACIÓN DE LA INTERFAZ ---
pygame.init()
WIDTH, HEIGHT = 900, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Arc17_Jauja_remejorado: Motor de Escalado y Exportación")
clock = pygame.time.Clock()

# --- CONSTANTES DE DISEÑO UNIFICADAS ---
ESCALA = 16            
ANCHO_VIA = 6 * ESCALA  
GROSOR_LINEA = 2         # Grosor base para calzadas grises
GROSOR_DECORATIVO = 1    # Grosor fino para travesaños internos y juntas
GROSOR_AMARILLO = 3      # Variable global parametrizada para el hilo derecho

# Variables de control del circuito
COLOR_FONDO = (255, 255, 255) # Fondo blanco solicitado
ANGULO_INICIAL = 90.0         # Ángulo de control inicial para la primera pieza

# Paleta de colores unificada
COLOR_LINEA = (0, 0, 0)
ROSA = (255, 0, 255)
ROJO = (255, 0, 0)
COLOR_AZULADO = (140, 150, 230) 
AMARILLO_DERECHO = (255, 215, 0)
GRIS_LINEAS = (128, 128, 128)

# =============================================================================
# ### rotar_punto_local()
# =============================================================================
def rotar_punto_local(punto_local, centro_local, angulo_grados):
    '''
    Objetivo: Rota un punto alrededor del centro de su superficie original aplicando trigonometría en sentido antihorario.
    Parametros:
    P1: punto_local (pygame.Vector2) -> Coordenada X,Y original sin rotar dentro del molde de la pieza.
    P2: centro_local (pygame.Vector2) -> Punto medio de la superficie que actúa como eje de rotación.
    P3: angulo_grados (float) -> Ángulo de inclinación acumulado en el circuito.
    Returns:
    pygame.Vector2 -> Coordenada relativa calculada tras aplicar la rotación.
    LLama a: math.radians(), math.cos(), math.sin(), pygame.Vector2()
    LLamada por: procesar_y_conectar_pieza()
    '''
    angulo_rad = math.radians(-angulo_grados)
    rx = punto_local.x - centro_local.x
    ry = punto_local.y - centro_local.y
    nx = rx * math.cos(angulo_rad) - ry * math.sin(angulo_rad)
    ny = rx * math.sin(angulo_rad) + ry * math.cos(angulo_rad)
    return pygame.Vector2(nx, ny)

# ============================================================================
# DRAWER GT: ROTONDA CORREGIDA (CON RETORNO SEGURO SUBSURFACE Y GROSORES PARAMETRIZADOS)
# ============================================================================
def dibujar_rotonda(mano, escala, grosor_linea, tam_surf, gris, amarillo):
    surf_canvas = pygame.Surface((tam_surf, tam_surf), pygame.SRCALPHA)

    s = -1 if mano == "I" else 1
    color_ext = gris if mano == "I" else amarillo
    color_int = amarillo if mano == "I" else gris

    ancho_pieza = 6 * escala
    r_ext = (11.0 / 2.0) * escala
    r_int_real = 2.5 * escala
    l_brazo_largo = 11.5 * escala
    l_brazo_corto = 2.75 * escala

    x_origen = tam_surf // 2
    y_origen = tam_surf // 2 + 250

    cx = x_origen
    cy = y_origen - l_brazo_largo - math.sqrt(r_ext**2 - (ancho_pieza / 2.0)**2)
    desfase_c = ancho_pieza / 2.0

    cx_corto = cx - (2.15 * escala) * s
    cy_corto = cy + (2.15 * escala)

    rad_desvio = math.asin((ancho_pieza / 2.0) / r_ext)
    grado_desvio = math.degrees(rad_desvio)

    x_ext_in = cx + desfase_c * s
    x_int_in = cx - desfase_c * s
    y_junta_entrada = cy + math.sqrt(r_ext**2 - desfase_c**2)
    y_base_in = y_junta_entrada + l_brazo_largo

    y_ext_out = cy - desfase_c
    y_int_out = cy + desfase_c

    g_ini_int = 270.0 + 19.5 if mano == "I" else 180.0 + 19.5
    g_fin_int = 360.0 - 19.5 if mano == "I" else 270.0 - 19.5
    puntos_int = []
    for i in range(int((g_fin_int - g_ini_int) * 100) + 1):
        rad = math.radians(g_ini_int + (i / 100.0))
        puntos_int.append((cx_corto + r_int_real * math.cos(rad), cy_corto - r_int_real * math.sin(rad)))
    pygame.draw.lines(surf_canvas, color_int, False, puntos_int, grosor_linea)

    g_ini_ext = 0.0 + grado_desvio if mano == "I" else -90.0 + grado_desvio
    g_fin_ext = 270.0 - grado_desvio if mano == "I" else 180.0 - grado_desvio
    puntos_ext = []
    for i in range(int((g_fin_ext - g_ini_ext) * 100) + 1):
        rad = math.radians(g_ini_ext + (i / 100.0))
        puntos_ext.append((cx + r_ext * math.cos(rad), cy - r_ext * math.sin(rad)))
        
    # Inyección 1: Arco exterior de la rotonda
    grosor_arco_ext = GROSOR_AMARILLO if mano == "D" else grosor_linea
    pygame.draw.lines(surf_canvas, color_ext, False, puntos_ext, grosor_arco_ext)

    x_junta_rotonda_out = cx - math.sqrt(r_ext**2 - desfase_c**2) * s
    xc_C = x_junta_rotonda_out + l_brazo_corto * (-s)

    # 1. Tramos de Entrada (Verticales): Entrada Abierta
    grosor_ext_in = GROSOR_AMARILLO if mano == "D" else grosor_linea
    pygame.draw.line(surf_canvas, color_ext, (x_ext_in, y_base_in), (x_ext_in, y_junta_entrada), grosor_ext_in)
    pygame.draw.line(surf_canvas, color_int, (x_int_in, y_base_in), (x_int_in, y_junta_entrada), grosor_linea)
    # ❌ ENTRADA ABIERTA: Hemos borrado la línea que unía (x_ext_in, y_base_in) con (x_int_in, y_base_in)

    # 2. Tramos de Salida (Horizontales): Salida Cerrada
    grosor_ext_out = GROSOR_AMARILLO if mano == "I" else grosor_linea
    pygame.draw.line(surf_canvas, color_ext, (x_junta_rotonda_out, y_ext_out), (xc_C, y_ext_out), grosor_ext_out)
    pygame.draw.line(surf_canvas, color_int, (x_junta_rotonda_out, y_int_out), (xc_C, y_int_out), grosor_linea)
    
    # 🟢 SALIDA CERRADA: Sellamos el extremo de salida con 1 píxel fino (GROSOR_DECORATIVO)
    pygame.draw.line(surf_canvas, gris, (xc_C, y_ext_out), (xc_C, y_int_out), GROSOR_DECORATIVO)


    paso_entrada = l_brazo_largo / 4.0
    for i in range(1, 4):
        pygame.draw.line(surf_canvas, gris, (x_ext_in, y_base_in - i * paso_entrada), (x_int_in, y_base_in - i * paso_entrada), grosor_linea)
    pygame.draw.line(surf_canvas, gris, (cx, y_base_in), (cx, y_junta_entrada), grosor_linea)

    for i in range(8):
        ang_rad = math.radians(i * 45.0)
        pygame.draw.line(surf_canvas, gris, (cx + (2.0 * escala) * math.cos(ang_rad), cy - (2.0 * escala) * math.sin(ang_rad)), (cx + r_ext * math.cos(ang_rad), cy - r_ext * math.sin(ang_rad)), grosor_linea)
    pygame.draw.line(surf_canvas, gris, (x_junta_rotonda_out, cy), (xc_C, cy), grosor_linea)
    pygame.draw.circle(surf_canvas, gris, (int(cx), int(cy)), int(2.0 * escala), grosor_linea)

    margen = int(ancho_pieza // 2)
    x_min = int(min(cx - r_ext, xc_C if mano == "I" else x_origen) - margen)
    x_max = int(max(cx + r_ext, xc_C if mano == "D" else x_origen) + margen)
    y_min = int(cy - r_ext - margen)
    y_max = int(y_base_in + margen)

    surf_cortada = surf_canvas.subsurface(pygame.Rect(x_min, y_min, x_max - x_min, y_max - y_min)).copy()

    datos_enganche = {
        "entrada_x": x_origen - x_min,
        "entrada_y": y_base_in - y_min,
        "salida_x": xc_C - x_min,
        "salida_y": cy - y_min
    }
    return surf_cortada, datos_enganche

# --- FABRICACIÓN DE MOLDES MAESTROS ---

# 1. PROTO GENERAL: RECTA (R) - Convenio General (Entrada Abierta, Salida Cerrada)
LARGO_RECTA = 19 * ESCALA
surf_recta = pygame.Surface((LARGO_RECTA, ANCHO_VIA), pygame.SRCALPHA)
cx_local, cy_local = 0, ANCHO_VIA

# Márgenes longitudinales de la calzada
pygame.draw.line(surf_recta, AMARILLO_DERECHO, (cx_local, cy_local), (cx_local + LARGO_RECTA, cy_local), GROSOR_AMARILLO)
pygame.draw.line(surf_recta, GRIS_LINEAS, (cx_local, cy_local - ANCHO_VIA), (cx_local + LARGO_RECTA, cy_local - ANCHO_VIA), GROSOR_LINEA)

# ❌ Entrada Abierta: Aquí NO se dibuja ninguna línea en cx_local
# 🟢 Salida Cerrada: Sella su final de forma estricta con 1 píxel fino
pygame.draw.line(surf_recta, GRIS_LINEAS, (cx_local + LARGO_RECTA, cy_local), (cx_local + LARGO_RECTA, cy_local - ANCHO_VIA), GROSOR_DECORATIVO)

# Eje central divisorio de carriles
pygame.draw.line(surf_recta, GRIS_LINEAS, (cx_local, cy_local - ANCHO_VIA / 2), (cx_local + LARGO_RECTA, cy_local - ANCHO_VIA / 2), GROSOR_DECORATIVO)

# Subdivisión interna de las 6 casillas de juego
ancho_casilla = LARGO_RECTA / 6.0
for i in range(1, 6):
    x_t = cx_local + i * ancho_casilla
    pygame.draw.line(surf_recta, GRIS_LINEAS, (x_t, cy_local), (x_t, cy_local - ANCHO_VIA), GROSOR_DECORATIVO)


# Ejecución maestra para llenar las variables dinámicas de las rotondas
tam_seguro = 2000
surf_rtd_gt, enganche_rtd = dibujar_rotonda("D", ESCALA, GROSOR_LINEA, tam_seguro, GRIS_LINEAS, AMARILLO_DERECHO)
surf_rti_gt, enganche_rti = dibujar_rotonda("I", ESCALA, GROSOR_LINEA, tam_seguro, GRIS_LINEAS, AMARILLO_DERECHO)

# --- EXTRACCIÓN SEGURA DE VECTORES DE ANCLAJE ---
w_rtd, h_rtd = surf_rtd_gt.get_width(), surf_rtd_gt.get_height()
w_rti, h_rti = surf_rti_gt.get_width(), surf_rti_gt.get_height()

ex_rtd, ey_rtd, sx_rtd, sy_rtd = enganche_rtd["entrada_x"], enganche_rtd["entrada_y"], enganche_rtd["salida_x"], enganche_rtd["salida_y"]
ex_rti, ey_rti, sx_rti, sy_rti = enganche_rti["entrada_x"], enganche_rti["entrada_y"], enganche_rti["salida_x"], enganche_rti["salida_y"]

# --- DICCIONARIO DE CONFIGURACIÓN DE PIEZAS (Variables Complejas) ---
CATALOGO_PIEZAS = {
    "R": {
        "superficie": surf_recta,
        "centro_local": pygame.Vector2(LARGO_RECTA / 2.0, ANCHO_VIA / 2.0),
        "ent_local_A": pygame.Vector2(0.0, 0.0),
        "ent_local_B": pygame.Vector2(0.0, ANCHO_VIA),
        "sal_local_C": pygame.Vector2(LARGO_RECTA, 0.0),
        "sal_local_D": pygame.Vector2(LARGO_RECTA, ANCHO_VIA),
        "ang_correccion": 0.0,   
        "aporte_angular": 0.0    
    },
    "RTD": {
        "superficie": surf_rtd_gt,
        "centro_local": pygame.Vector2(w_rtd / 2.0, h_rtd / 2.0),
        "ent_local_A": pygame.Vector2(ex_rtd - ANCHO_VIA / 2.0, ey_rtd),
        "ent_local_B": pygame.Vector2(ex_rtd + ANCHO_VIA / 2.0, ey_rtd),
        "sal_local_C": pygame.Vector2(sx_rtd, sy_rtd + ANCHO_VIA / 2.0),
        "sal_local_D": pygame.Vector2(sx_rtd, sy_rtd - ANCHO_VIA / 2.0),
        "ang_correccion": -90.0, 
        "aporte_angular": 90.0   
    },
    "RTI": {
        "superficie": surf_rti_gt,
        "centro_local": pygame.Vector2(w_rti / 2.0, h_rti / 2.0),
        "ent_local_A": pygame.Vector2(ex_rti - ANCHO_VIA / 2.0, ey_rti),
        "ent_local_B": pygame.Vector2(ex_rti + ANCHO_VIA / 2.0, ey_rti),
        "sal_local_C": pygame.Vector2(sx_rti, sy_rti - ANCHO_VIA / 2.0),
        "sal_local_D": pygame.Vector2(sx_rti, sy_rti + ANCHO_VIA / 2.0),
        "ang_correccion": -90.0, 
        "aporte_angular": -90.0  
    }
}

# =============================================================================
# ### procesar_y_conectar_pieza()
# =============================================================================
def procesar_y_conectar_pieza(codigo, eje_conexion_mundo, angulo_acumulado):
    '''
    Objetivo: Actúa como función de cálculo única para cualquier pieza. Recibe el punto de conexión global y el ángulo acumulado de la carrera, absorbe las discrepancias de diseño del molde y devuelve la superficie rotada lista para pintar junto con sus nuevas coordenadas y el ángulo de salida actualizado.
    '''
    if codigo not in CATALOGO_PIEZAS:
        print(f"Error: La pieza '{codigo}' no existe en el catálogo.")
        return None
        
    cfg = CATALOGO_PIEZAS[codigo]
    angulo_render = angulo_acumulado + cfg["ang_correccion"]
    
    surf_rotada = pygame.transform.rotate(cfg["superficie"], angulo_render)
    rect_pieza = surf_rotada.get_rect()
    
    eje_entrada_local = (cfg["ent_local_A"] + cfg["ent_local_B"]) / 2.0
    v_ent_rotado = rotar_punto_local(eje_entrada_local, cfg["centro_local"], angulo_render)
    centro_mundo = eje_conexion_mundo - v_ent_rotado
    rect_pieza.center = (int(centro_mundo.x), int(centro_mundo.y))
    
    mundo_sal_C = centro_mundo + rotar_punto_local(cfg["sal_local_C"], cfg["centro_local"], angulo_render)
    mundo_sal_D = centro_mundo + rotar_punto_local(cfg["sal_local_D"], cfg["centro_local"], angulo_render)
    
    nuevo_angulo = angulo_acumulado + cfg["aporte_angular"]
    return surf_rotada, rect_pieza, mundo_sal_C, mundo_sal_D, nuevo_angulo

# --- PROCESAMIENTO DINÁMICO DE LA PISTA ---
cadena_entrada = "R, RTD, R, RTI, R"  # Entrada parametrizada del usuario
despieze = [token.strip().upper() for token in cadena_entrada.split(",") if token.strip()]

punto_conexion_actual = pygame.Vector2(450, 550)
angulo_carrera_actual = ANGULO_INICIAL

piezas_calculadas = []

for tipo in despieze:
    resultado = procesar_y_conectar_pieza(tipo, punto_conexion_actual, angulo_carrera_actual)
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

# =========================================================================
# --- CÁLCULO DE CAJA CONTENEDORA Y MATRIZ DE VISUALIZACIÓN ---
# =========================================================================
todos_los_puntos = []
for p in piezas_calculadas:
    todos_los_puntos.extend([p["sal_C"], p["sal_D"]])

xs = [p.x for p in todos_los_puntos]
ys = [p.y for p in todos_los_puntos]
min_x, max_x = min(xs), max(xs)
min_y, max_y = min(ys), max(ys)

ancho_pista = max_x - min_x if (max_x - min_x) > 0 else 1.0
alto_pista = max_y - min_y if (max_y - min_y) > 0 else 1.0
centro_pista = pygame.Vector2((min_x + max_x) / 2.0, (min_y + max_y) / 2.0)

escala_x = (WIDTH * 0.90) / ancho_pista
escala_y = (HEIGHT * 0.90) / alto_pista
FACTOR_CAMARA = min(escala_x, escala_y)
centro_pantalla = pygame.Vector2(WIDTH / 2.0, HEIGHT / 2.0)

# --- EXPORTACIÓN AUTOMÁTICA A PNG INCREMENTAL ---
superficie_export = pygame.Surface((WIDTH, HEIGHT))
superficie_export.fill(COLOR_FONDO)

for idx, pieza in enumerate(piezas_calculadas):
    w_original, h_original = pieza["superficie"].get_size()
    surf_escalada = pygame.transform.scale(pieza["superficie"], (int(w_original * FACTOR_CAMARA), int(h_original * FACTOR_CAMARA)))
    rect_escalado = surf_escalada.get_rect()
    centro_pieza_mundo = pygame.Vector2(pieza["rect"].center)
    centro_pieza_camara = centro_pantalla + (centro_pieza_mundo - centro_pista) * FACTOR_CAMARA
    rect_escalado.center = (int(centro_pieza_camara.x), int(centro_pieza_camara.y))
    superficie_export.blit(surf_escalada, rect_escalado.topleft)
    
    p_C_camara = centro_pantalla + (pieza["sal_C"] - centro_pista) * FACTOR_CAMARA
    p_D_camara = centro_pantalla + (pieza["sal_D"] - centro_pista) * FACTOR_CAMARA
    pygame.draw.line(superficie_export, GRIS_LINEAS, p_C_camara, p_D_camara, GROSOR_DECORATIVO)
    
    if idx == 0 and len(despieze) > 0:
        cfg_primera = CATALOGO_PIEZAS[despieze[0]]
        angulo_r1 = ANGULO_INICIAL + cfg_primera["ang_correccion"]
        centro_m1 = pygame.Vector2(pieza["rect"].center)
        p_ent_A_mundo = centro_m1 + rotar_punto_local(cfg_primera["ent_local_A"], cfg_primera["centro_local"], angulo_r1)
        p_ent_B_mundo = centro_m1 + rotar_punto_local(cfg_primera["ent_local_B"], cfg_primera["centro_local"], angulo_r1)
        p_A_camara = centro_pantalla + (p_ent_A_mundo - centro_pista) * FACTOR_CAMARA
        p_B_camara = centro_pantalla + (p_ent_B_mundo - centro_pista) * FACTOR_CAMARA
        pygame.draw.line(superficie_export, GRIS_LINEAS, p_A_camara, p_B_camara, GROSOR_DECORATIVO)

nombre_script = "Arc17_Jauja_remejorado"
contador = 1
while os.path.exists(f"{nombre_script}_{contador}.png"):
    contador += 1
nombre_archivo_final = f"{nombre_script}_{contador}.png"
pygame.image.save(superficie_export, nombre_archivo_final)
print(f"[SISTEMA] Archivo exportado con éxito: {nombre_archivo_final}")

# --- BUCLE DE INTERFAZ GRÁFICA ---
paso_actual = 1
running = True

while running:
    screen.fill(COLOR_FONDO)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
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
            rect_vis.center = (int(centro_c.x), int(centro_c.y))
            screen.blit(surf_vis, rect_vis.topleft)
            
            p_C_camara = centro_pantalla + (pieza["sal_C"] - centro_pista) * FACTOR_CAMARA
            p_D_camara = centro_pantalla + (pieza["sal_D"] - centro_pista) * FACTOR_CAMARA
            
            pygame.draw.line(screen, GRIS_LINEAS, p_C_camara, p_D_camara, GROSOR_DECORATIVO)

            if idx == 0 and len(despieze) > 0:
                cfg_primera = CATALOGO_PIEZAS[despieze[0]]
                angulo_r1 = ANGULO_INICIAL + cfg_primera["ang_correccion"]
                centro_m1 = pygame.Vector2(pieza["rect"].center)
                p_ent_A_mundo = centro_m1 + rotar_punto_local(cfg_primera["ent_local_A"], cfg_primera["centro_local"], angulo_r1)
                p_ent_B_mundo = centro_m1 + rotar_punto_local(cfg_primera["ent_local_B"], cfg_primera["centro_local"], angulo_r1)
                p_A_camara = centro_pantalla + (p_ent_A_mundo - centro_pista) * FACTOR_CAMARA
                p_B_camara = centro_pantalla + (p_ent_B_mundo - centro_pista) * FACTOR_CAMARA
                pygame.draw.line(screen, GRIS_LINEAS, p_A_camara, p_B_camara, GROSOR_DECORATIVO)

            pygame.draw.circle(screen, ROSA, (int(p_C_camara.x), int(p_C_camara.y)), int(max(3, 5 * FACTOR_CAMARA)))
            pygame.draw.circle(screen, ROJO, (int(p_D_camara.x), int(p_D_camara.y)), int(max(3, 5 * FACTOR_CAMARA)))

    font = pygame.font.SysFont(None, 22)
    txt = font.render(f"Paso: {paso_actual}/{len(piezas_calculadas)} | String: '{cadena_entrada}' | Export: {nombre_archivo_final}", True, COLOR_LINEA)
    screen.blit(txt, (20, 20))
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
