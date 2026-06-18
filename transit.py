# -*- coding: utf-8 -*-
"""
Created on Thu Jun 18 12:56:33 2026

@author: Matasiete

Created on Tue Jun 17 15:24:59 2026

Arcs021 provisional
"""

import pygame
import sys
import math
import os

# 1. IMPORTACIÓN PRIMERO
import config
from config import *
'''
NEW!!!
'''
from presentacion import inicializar_pantalla, ejecutar_bucle_principal


# --- CONFIGURACIÓN DE LA INTERFAZ ---
pygame.init()

# Forzamos la lectura explícita desde el espacio de nombres de config para blindar Spyder
ANCHO_PANTALLA = config.WIDTH
ALTO_PANTALLA = config.HEIGHT

pantalla_objetivo = pygame.display.set_mode((ANCHO_PANTALLA, ALTO_PANTALLA))
pygame.display.set_caption("Arc17_Jauja_remejorado: Motor de Escalado y Exportación")
clock = pygame.time.Clock()

# --- CONSTANTES DE DISEÑO INTERNAS ---
ANCHO_VIA = 6 * ESCALA  
GROSOR_LINEA = 2         
GROSOR_DECORATIVO = 1    
GROSOR_AMARILLO = 3      
ANGULO_INICIAL = 0         



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
def dibujar_rotonda(mano, escala, tam_surf, gris, amarillo):
    '''
    Objetivo: Generar dinámicamente un molde procedural para una rotonda (RTD/RTI) en un lienzo virtual sobredimensionado. Dibuja arcos concéntricos e hilos rectos según la quiralidad ("I" o "D"), calcula el trazado divisorio de casillas radiales y recorta la superficie con precisión mediante un subsurface para optimizar los puntos de anclaje.
    Parametros:
    P1: mano, string -> Quiralidad de la pieza; "I" para mano izquierda (RTI), "D" para mano derecha (RTD).
    P2: escala, int -> Factor multiplicador de píxeles para el diseño relativo de la loseta.
    P3: tam_surf, int -> Dimensión en píxeles del lienzo virtual cuadrado seguro (1200).
    P4: gris, tuple -> Valor RGB correspondiente a las líneas divisorias y bordes estándar (GRIS_LINEAS).
    P5: amarillo, tuple -> Valor RGB correspondiente al hilo continuo de seguridad derecho (AMARILLO_DERECHO).
    Returns:
    surf_cortada, pygame.Surface -> Superficie recortada que contiene la geometría exacta de la rotonda sin transparencias muertas.
    datos_enganche, dict -> Coordenadas locales de entrada (X, Y) y salida (X, Y) calculadas de forma estanca desde el marco recortado.
    LLama a: math.sqrt(), math.asin(), math.degrees(), math.radians(), math.cos(), math.sin(), pygame.Surface(), pygame.draw.lines(), pygame.draw.line(), pygame.draw.circle(), pygame.Surface.subsurface(), pygame.Surface.copy()
    LLamada por: Bloque de inicialización de moldes al arrancar el script (líneas 152 y 153 para surf_rtd_gt y surf_rti_gt).
    '''    
    
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
    # Arco interior (decorativo, grosor 1)
    pygame.draw.lines(surf_canvas, color_int, False, puntos_int, GROSOR_DECORATIVO)

    g_ini_ext = 0.0 + grado_desvio if mano == "I" else -90.0 + grado_desvio
    g_fin_ext = 270.0 - grado_desvio if mano == "I" else 180.0 - grado_desvio
    puntos_ext = []
    for i in range(int((g_fin_ext - g_ini_ext) * 100) + 1):
        rad = math.radians(g_ini_ext + (i / 100.0))
        puntos_ext.append((cx + r_ext * math.cos(rad), cy - r_ext * math.sin(rad)))
        
    # Arco exterior de la rotonda (amarillo grueso si es D, sino gris estándar)
    pygame.draw.lines(surf_canvas, color_ext, False, puntos_ext,
                      GROSOR_AMARILLO if mano == "D" else GROSOR_LINEA)

    x_junta_rotonda_out = cx - math.sqrt(r_ext**2 - desfase_c**2) * s
    xc_C = x_junta_rotonda_out + l_brazo_corto * (-s)

    # 1. Tramos de Entrada (Verticales): Entrada Abierta
    pygame.draw.line(surf_canvas, color_ext, (x_ext_in, y_base_in), (x_ext_in, y_junta_entrada),
                     GROSOR_AMARILLO if mano == "D" else GROSOR_LINEA)
    pygame.draw.line(surf_canvas, color_int, (x_int_in, y_base_in), (x_int_in, y_junta_entrada),
                     GROSOR_DECORATIVO)  # interior siempre decorativo
    # ❌ ENTRADA ABIERTA: Hemos borrado la línea que unía (x_ext_in, y_base_in) con (x_int_in, y_base_in)

    # 2. Tramos de Salida (Horizontales): Salida Cerrada
    pygame.draw.line(surf_canvas, color_ext, (x_junta_rotonda_out, y_ext_out), (xc_C, y_ext_out),
                     GROSOR_AMARILLO if mano == "I" else GROSOR_LINEA)
    pygame.draw.line(surf_canvas, color_int, (x_junta_rotonda_out, y_int_out), (xc_C, y_int_out),
                     GROSOR_DECORATIVO)  # interior siempre decorativo
    
    # 🟢 SALIDA CERRADA: Sellamos el extremo de salida con 1 píxel fino
    pygame.draw.line(surf_canvas, gris, (xc_C, y_ext_out), (xc_C, y_int_out), GROSOR_DECORATIVO)

    # Subdivisiones internas (travesaños) - todas decorativas
    paso_entrada = l_brazo_largo / 4.0
    for i in range(1, 4):
        pygame.draw.line(surf_canvas, gris, (x_ext_in, y_base_in - i * paso_entrada),
                         (x_int_in, y_base_in - i * paso_entrada), GROSOR_DECORATIVO)
    # Eje central vertical
    pygame.draw.line(surf_canvas, gris, (cx, y_base_in), (cx, y_junta_entrada), GROSOR_DECORATIVO)

    # Líneas radiales (subdivisiones internas)
    for i in range(8):
        ang_rad = math.radians(i * 45.0)
        pygame.draw.line(surf_canvas, gris,
                         (cx + (2.0 * escala) * math.cos(ang_rad), cy - (2.0 * escala) * math.sin(ang_rad)),
                         (cx + r_ext * math.cos(ang_rad), cy - r_ext * math.sin(ang_rad)),
                         GROSOR_DECORATIVO)
    # Línea horizontal de subdivisión
    pygame.draw.line(surf_canvas, gris, (x_junta_rotonda_out, cy), (xc_C, cy), GROSOR_DECORATIVO)
    # Círculo central
    pygame.draw.circle(surf_canvas, gris, (int(cx), int(cy)), int(2.0 * escala), GROSOR_DECORATIVO)

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
surf_rtd_gt, enganche_rtd = dibujar_rotonda("D", ESCALA, tam_seguro, GRIS_LINEAS, AMARILLO_DERECHO)
surf_rti_gt, enganche_rti = dibujar_rotonda("I", ESCALA, tam_seguro, GRIS_LINEAS, AMARILLO_DERECHO)

# --- EXTRACCIÓN SEGURA DE VECTORES DE ANCLAJE ---
w_rtd, h_rtd = surf_rtd_gt.get_width(), surf_rtd_gt.get_height()
w_rti, h_rti = surf_rti_gt.get_width(), surf_rti_gt.get_height()

ex_rtd, ey_rtd, sx_rtd, sy_rtd = enganche_rtd["entrada_x"], enganche_rtd["entrada_y"], enganche_rtd["salida_x"], enganche_rtd["salida_y"]
ex_rti, ey_rti, sx_rti, sy_rti = enganche_rti["entrada_x"], enganche_rti["entrada_y"], enganche_rti["salida_x"], enganche_rti["salida_y"]




# ////////////////////////////////////////////////////////////

def dibujar_sharp_corners(mano, escala, grosor_linea, tam_surf, gris, amarillo):
    surf_local = pygame.Surface((tam_surf, tam_surf), pygame.SRCALPHA)
    
    if mano == "I":
        s = -1
        color_ext = gris
        color_int = amarillo
    else:
        s = 1
        color_ext = amarillo
        color_int = gris

    x_X = tam_surf // 2
    y_X = tam_surf // 2 + 150
    calzada = 6.0 * escala
    techo_total = 18.0 * escala
    alto_der = 10.5 * escala
    alto_izq = 6.0 * escala
    ancho_hueco = 6.0 * escala
    prof_hueco = 2.0 * escala 

    x_der_ext = x_X + (calzada / 2.0) * s
    x_der_int = x_X - (calzada / 2.0) * s
    y_base_der = y_X
    y_techo = y_X - alto_der
    x_izq_ext = x_der_ext - techo_total * s
    x_izq_int = x_izq_ext + calzada * s
    y_base_izq = y_techo + alto_izq
    x_hueco_der = x_der_int
    y_hueco_fondo = y_techo + (alto_der - prof_hueco) - calzada

    # Trazado Perimetral Base
    pygame.draw.line(surf_local, color_ext, (x_der_ext, y_base_der), (x_der_ext, y_techo), grosor_linea)
    pygame.draw.line(surf_local, color_ext, (x_der_ext, y_techo), (x_izq_ext, y_techo), grosor_linea)
    pygame.draw.line(surf_local, color_ext, (x_izq_ext, y_techo), (x_izq_ext, y_base_izq), grosor_linea)

    pygame.draw.line(surf_local, color_int, (x_der_int, y_base_der), (x_der_int, y_hueco_fondo + prof_hueco), grosor_linea)
    pygame.draw.line(surf_local, color_int, (x_der_int, y_hueco_fondo + prof_hueco), (x_hueco_der - ancho_hueco * s, y_hueco_fondo + prof_hueco), grosor_linea)
    pygame.draw.line(surf_local, color_int, (x_izq_int, y_base_izq), (x_izq_int, y_hueco_fondo + prof_hueco), grosor_linea)
 
    # Casillas interiores lateral estrecho
    pygame.draw.line(surf_local, gris, (x_hueco_der - ancho_hueco * s, y_hueco_fondo + prof_hueco), (x_hueco_der - ancho_hueco * s, y_techo), grosor_linea)
    pygame.draw.line(surf_local, gris, (x_hueco_der, y_hueco_fondo + prof_hueco), (x_hueco_der, y_techo), grosor_linea)

    # Tapas de extremos
    pygame.draw.line(surf_local, gris, (x_izq_ext, y_base_izq), (x_izq_int, y_base_izq), grosor_linea) 
    pygame.draw.line(surf_local, gris, (x_der_ext, y_base_der), (x_der_int, y_base_der), grosor_linea) 

    # Estructura Interna
    y_division_entrada = y_base_der - (alto_der - (y_hueco_fondo - y_techo)) / 2.0
    x_eje_salida = x_izq_ext + (calzada / 2.0) * s
    top_int_izq = (y_hueco_fondo + prof_hueco) - 10
    
    # Casillero horizontal lado largo
    pygame.draw.line(surf_local, gris, (x_der_ext, y_division_entrada), (x_der_int, y_division_entrada), grosor_linea)
    # Casillero vertical lado largo
    pygame.draw.line(surf_local, gris, (x_X, y_base_der), (x_X, y_hueco_fondo + prof_hueco - (y_base_der - y_hueco_fondo + prof_hueco + 8)/5), grosor_linea)
    # Casillero vertical lado corto
    pygame.draw.line(surf_local, gris, (x_eje_salida, y_base_izq), (x_eje_salida, top_int_izq), grosor_linea)

    # Diagonales
    pygame.draw.line(surf_local, gris, (x_der_int, y_hueco_fondo + prof_hueco), (x_der_ext, y_techo), grosor_linea)
    pygame.draw.line(surf_local, gris, (x_izq_ext, y_hueco_fondo), (x_izq_int, y_hueco_fondo + prof_hueco), grosor_linea)
    
    return surf_local

# ////////////////////////////////////////////////////////////





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
    "RC": {
        "ancho": 9.6 * ESCALA,
        "alto": 6 * ESCALA,
        "angulo_giro": 0.0,
        "ang_correccion": 0.0,
        "aporte_angular": 0.0,
        "centro_local": pygame.Vector2(4.8 * ESCALA, 3 * ESCALA),
        # Entrada en el lateral izquierdo unificado
        "ent_local_A": pygame.Vector2(0.0, 0.0),
        "ent_local_B": pygame.Vector2(0.0, 6 * ESCALA),
        # Salida recta pura exactamente a 9.6 unidades de distancia física
        "sal_local_C": pygame.Vector2(9.6 * ESCALA, 0.0),
        "sal_local_D": pygame.Vector2(9.6 * ESCALA, 6 * ESCALA),
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
    },
    "SCD": {
        "ancho": 800,
        "alto": 800,
        "angulo_giro": 180.0,
        # CORRECCIÓN: Resta los 90 grados de desviación del molde vertical para alinearlo al eje horizontal Este
        "ang_correccion": -90.0,
        "aporte_angular": 180.0,
        "centro_local": pygame.Vector2(400.0, 400.0),
        "ent_local_A": pygame.Vector2(400.0 - (6.0 * ESCALA) / 2.0, 400.0 + 150.0),
        "ent_local_B": pygame.Vector2(400.0 + (6.0 * ESCALA) / 2.0, 400.0 + 150.0),
        "sal_local_C": pygame.Vector2(400.0 + (6.0 * ESCALA / 2.0) * 1 - 18.0 * ESCALA + 6.0 * ESCALA, 400.0 + 150.0 - 10.5 * ESCALA + 6.0 * ESCALA),
        "sal_local_D": pygame.Vector2(400.0 + (6.0 * ESCALA / 2.0) * 1 - 18.0 * ESCALA, 400.0 + 150.0 - 10.5 * ESCALA + 6.0 * ESCALA),
    },
    "SCI": {
        "ancho": 800,
        "alto": 800,
        "angulo_giro": 180.0,
        # CORRECCIÓN: Ajusta los 90 grados de desviación del molde vertical para alinearlo al eje horizontal Este
        "ang_correccion": -90.0,
        "aporte_angular": 180.0,
        "centro_local": pygame.Vector2(400.0, 400.0),
        "ent_local_A": pygame.Vector2(400.0 - (6.0 * ESCALA) / 2.0, 400.0 + 150.0),
        "ent_local_B": pygame.Vector2(400.0 + (6.0 * ESCALA) / 2.0, 400.0 + 150.0),
        "sal_local_C": pygame.Vector2(400.0 + (6.0 * ESCALA / 2.0) * (-1) - 18.0 * ESCALA * (-1), 400.0 + 150.0 - 10.5 * ESCALA + 6.0 * ESCALA),
        "sal_local_D": pygame.Vector2(400.0 + (6.0 * ESCALA / 2.0) * (-1) - 18.0 * ESCALA * (-1) + 6.0 * ESCALA * (-1), 400.0 + 150.0 - 10.5 * ESCALA + 6.0 * ESCALA),
    },


# ////////////////////////////////////////////////////////////

# ////////////////////////////////////////////////////////////
# --- ANTES (LÍNEAS QUE NO CAMBIAN) ---
#         "ang_correccion": -90.0,
#         "aporte_angular": -90.0
#     },
# ////////////////////////////////////////////////////////////

    "CD90": {
        "ancho": 8 * ESCALA,
        "alto": 8 * ESCALA,
        "angulo_giro": -90,
        "ang_correccion": 0.0,
        "aporte_angular": -90.0,
        "centro_local": pygame.Vector2(4 * ESCALA, 4 * ESCALA),
        "ent_local_A": pygame.Vector2(0.0, 0.0),
        "ent_local_B": pygame.Vector2(0.0, 6 * ESCALA),
        "sal_local_C": pygame.Vector2(8 * ESCALA, 8 * ESCALA),
        "sal_local_D": pygame.Vector2(2 * ESCALA, 8 * ESCALA),
    },
    "CI90": {
        "ancho": 8 * ESCALA,
        "alto": 8 * ESCALA,
        "angulo_giro": 90,
        "ang_correccion": 0.0,
        "aporte_angular": 90.0,
        "centro_local": pygame.Vector2(4 * ESCALA, 4 * ESCALA),
        # CORRECCIÓN DE QUIRALIDAD: Entrada en el flanco inferior izquierdo del lienzo
        "ent_local_A": pygame.Vector2(0.0, 2 * ESCALA),
        "ent_local_B": pygame.Vector2(0.0, 8 * ESCALA),
        # Salida pura orientada al norte: C es exterior (8), D es interior amarillo (2) en y=0
        "sal_local_C": pygame.Vector2(8 * ESCALA, 0.0),
        "sal_local_D": pygame.Vector2(2 * ESCALA, 0.0),
    },
    "CD45": {
        "ancho": 12 * ESCALA,
        "alto": 12 * ESCALA,
        "angulo_giro": -45,
        "ang_correccion": 0.0,
        "aporte_angular": -45.0,
        "centro_local": pygame.Vector2(6 * ESCALA, 6 * ESCALA),
        "ent_local_A": pygame.Vector2(0.0, 0.0),
        "ent_local_B": pygame.Vector2(0.0, 6 * ESCALA),
        "sal_local_C": pygame.Vector2(12 * ESCALA * 0.70710678, 12 * ESCALA * (1.0 - 0.70710678)),
        "sal_local_D": pygame.Vector2(6 * ESCALA * 0.70710678, (12.0 - 6.0 * 0.70710678) * ESCALA),
    },
    "CI45": {
        "ancho": 12 * ESCALA,
        "alto": 12 * ESCALA,
        "angulo_giro": 45,
        "ang_correccion": 0.0,
        "aporte_angular": 45.0,
        "centro_local": pygame.Vector2(6 * ESCALA, 6 * ESCALA),
        # CORRECCIÓN DE QUIRALIDAD: Entrada alineada en la banda inferior de la calzada de 12
        "ent_local_A": pygame.Vector2(0.0, 6 * ESCALA),
        "ent_local_B": pygame.Vector2(0.0, 12 * ESCALA),
        # Salida proyectada de forma estricta desde el centro inferior (0, 12 * ESCALA) hacia arriba
        "sal_local_C": pygame.Vector2(12 * ESCALA * 0.70710678, 12 * ESCALA * 0.70710678),
        "sal_local_D": pygame.Vector2(6 * ESCALA * 0.70710678, 6 * ESCALA * 0.70710678),
    },

# ////////////////////////////////////////////////////////////
# --- DESPUÉS (LÍNEAS QUE NO CAMBIAN) ---
# }
# 
# # =============================================================================
# ////////////////////////////////////////////////////////////

}

# =============================================================================
# ### procesar_y_conectar_pieza()
# =============================================================================
def procesar_y_conectar_pieza(codigo, eje_conexion_mundo, angulo_acumulado):
    '''
    Objetivo: Actúa como función de cálculo única para cualquier pieza. Recibe el punto de conexión global y el ángulo acumulado de la carrera, absorbe las discrepancies de diseño del molde y devuelve la superficie rotada lista para pintar junto con sus nuevas coordenadas y el ángulo de salida actualizado.
    Parametros:
    P1: codigo, string -> Código nominal de la pieza ("R", "RTD").
    P2: eje_conexion_mundo, pygame.Vector2 -> Punto medio de la salida de la pieza anterior en el mundo.
    P3: angulo_acumulado (float) -> Dirección actual de la carrera en grados.
    Returns:
    surf_rotada, pygame.Surface -> Imagen de la pieza girada correctamente.
    rect_pieza, pygame.Rect -> Rectángulo posicionado en el espacio del mundo.
    mundo_sal_C, pygame.Vector2 -> Posición global de la salida izquierda (Gris).
    mundo_sal_D, pygame.Vector2 -> Posición global de la salida derecha (Amarilla).
    nuevo_angulo, float -> Ángulo de dirección de la carrera actualizado para la siguiente loseta.
    LLama a: rotar_punto_local(), pygame.transform.rotate()
    LLamada por: Bloque de procesamiento de la pista (Main) en el bucle iterativo de la receta de tramos.
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
cadena_entrada = "R, SCD, R, CD90, RC, CD90, SCI, RTD, R"  # Entrada parametrizada del usuario
despieze = [token.strip().upper() for token in cadena_entrada.split(",") if token.strip()]

punto_conexion_actual = pygame.Vector2(450, 550)
angulo_carrera_actual = ANGULO_INICIAL

# ////////////////////////////////////////////////////////////

    # --- FABRICACIÓN GRÁFICA DE SUPERFICIE PARA RECTA CORTA (RC) REAL (9.6 U) ---
cfg_rc = CATALOGO_PIEZAS["RC"]
surf_rc_local = pygame.Surface((int(cfg_rc["ancho"]), int(cfg_rc["alto"])), pygame.SRCALPHA)

l_corta = 9.6 * ESCALA
ancho_via_local = 6 * ESCALA

# Líneas perimetrales (Regla de Oro: derecha es Amarilla)
pygame.draw.line(surf_rc_local, GRIS_LINEAS, (0, 0), (l_corta, 0), GROSOR_LINEA)
pygame.draw.line(surf_rc_local, AMARILLO_DERECHO, (0, ancho_via_local), (l_corta, ancho_via_local), GROSOR_LINEA + 1)

# Bocas de cierre de la loseta de cartón
pygame.draw.line(surf_rc_local, GRIS_LINEAS, (0, 0), (0, ancho_via_local), GROSOR_LINEA)
pygame.draw.line(surf_rc_local, GRIS_LINEAS, (l_corta, 0), (l_corta, ancho_via_local), GROSOR_LINEA)

# Línea central divisoria de carriles
pygame.draw.line(surf_rc_local, GRIS_LINEAS, (0, ancho_via_local // 2), (l_corta, ancho_via_local // 2), GROSOR_LINEA)

# 2 travesaños internos para formar exactamente las 3 casillas reales de carrera (3.2 unidades cada una)
ancho_casilla_rc = l_corta / 3.0
for i in range(1, 3):
    x_t = i * ancho_casilla_rc
    pygame.draw.line(surf_rc_local, GRIS_LINEAS, (x_t, 0), (x_t, ancho_via_local), GROSOR_LINEA)

# Guardar la superficie e inyectar el promedio de enganche en el motor
CATALOGO_PIEZAS["RC"]["superficie"] = surf_rc_local
CATALOGO_PIEZAS["RC"]["promedio_entrada_local"] = (cfg_rc["ent_local_A"] + cfg_rc["ent_local_B"]) / 2.0

# ////////////////////////////////////////////////////////////

# --- INVOCACIÓN GRÁFICA DIRECTA DE TU FUNCIÓN NATIVA PARA CALLEJONES (SCD / SCI) ---
for mano_cod in ["SCD", "SCI"]:
    cfg_sc = CATALOGO_PIEZAS[mano_cod]
    letra_mano = "D" if mano_cod == "SCD" else "I"
    
    # CORRECCIÓN: Se sustituye TAM_SURF por el valor literal 800 píxeles exigido por el lienzo
    surf_fabricada = dibujar_sharp_corners(letra_mano, ESCALA, GROSOR_LINEA, 800, GRIS_LINEAS, AMARILLO_DERECHO)
    
    # Inyectar la superficie y calcular el promedio de entrada exigido por el motor rígido
    CATALOGO_PIEZAS[mano_cod]["superficie"] = surf_fabricada
    CATALOGO_PIEZAS[mano_cod]["promedio_entrada_local"] = (cfg_sc["ent_local_A"] + cfg_sc["ent_local_B"]) / 2.0

# ////////////////////////////////////////////////////////////

piezas_calculadas = []

# ////////////////////////////////////////////////////////////
# --- ANTES (LÍNEAS QUE NO CAMBIAN) ---
#         cfg["promedio_entrada_local"] = (v_ent_A + v_ent_B) / 2.0
# 
# piezas_calculadas = []
# ////////////////////////////////////////////////////////////

# --- BLOQUE 2: FABRICACIÓN GRÁFICA DE SUPERFICIES PARA CURVAS ESTÁNDAR ---
for codigo in ["CD90", "CI90", "CD45", "CI45"]:
    cfg = CATALOGO_PIEZAS[codigo]
    ancho_local = int(cfg["ancho"])
    alto_local = int(cfg["alto"])
    
    # Crear la superficie local transparente
    surf_local = pygame.Surface((ancho_local, alto_local), pygame.SRCALPHA)
    
    es_90 = '90' in codigo
    es_izq = 'I' in codigo
    r_int = 2 * ESCALA if es_90 else 6 * ESCALA
    r_ext = 8 * ESCALA if es_90 else 12 * ESCALA
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

    # Dibujo de líneas perimetrales (Regla de Oro: Derecha en la marcha siempre Amarilla)
    if len(puntos_ext) >= 2:
        pygame.draw.lines(surf_local, AMARILLO_DERECHO if es_izq else GRIS_LINEAS, False, puntos_ext, GROSOR_LINEA + 1 if es_izq else GROSOR_LINEA)
        pygame.draw.lines(surf_local, GRIS_LINEAS if es_izq else AMARILLO_DERECHO, False, puntos_int, GROSOR_LINEA if es_izq else GROSOR_LINEA + 1)

    # Bocas de entrada y salida (Líneas de cierre estancas)
    pygame.draw.line(surf_local, GRIS_LINEAS, puntos_ext[0], puntos_int[0], GROSOR_LINEA)
    pygame.draw.line(surf_local, GRIS_LINEAS, puntos_ext[-1], puntos_int[-1], GROSOR_LINEA)

    # Línea central transmedia en curva
    r_med = (r_int + r_ext) / 2.0
    puntos_centro = []
    for grado in range(int(ang_i), int(ang_f) + 1):
        rad = math.radians(grado)
        puntos_centro.append((cx_arco + r_med * math.cos(rad), cy_arco - r_med * math.sin(rad)))
    if len(puntos_centro) >= 2:
        pygame.draw.lines(surf_local, GRIS_LINEAS, False, puntos_centro, GROSOR_LINEA)

    # Travesaño intermedio angular para dividir las casillas
    grado_medio = ang_i + (angulo_giro / 2.0)
    rad_m = math.radians(grado_medio)
    pygame.draw.line(surf_local, GRIS_LINEAS, 
                     (cx_arco + r_int * math.cos(rad_m), cy_arco - r_int * math.sin(rad_m)), 
                     (cx_arco + r_ext * math.cos(rad_m), cy_arco - r_ext * math.sin(rad_m)), GROSOR_LINEA)

    # Asignar la superficie fabricada y calcular el promedio requerido
    CATALOGO_PIEZAS[codigo]["superficie"] = surf_local
    CATALOGO_PIEZAS[codigo]["promedio_entrada_local"] = (cfg["ent_local_A"] + cfg["ent_local_B"]) / 2.0

# ////////////////////////////////////////////////////////////
# --- DESPUÉS (LÍNEAS QUE NO CAMBIAN) ---
# for tipo in despieze:
#     resultado = procesar_y_conectar_pieza(tipo, punto_conexion_actual, angulo_carrera_actual)
# ////////////////////////////////////////////////////////////


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
    margen_loseta = 15.0 * ESCALA 
    
    min_x = min(puntos_x) - margen_loseta
    max_x = max(puntos_x) + margen_loseta
    min_y = min(puntos_y) - margen_loseta
    max_y = max(puntos_y) + margen_loseta

    ancho_pista = max_x - min_x if (max_x - min_x) > 0 else 1.0
    alto_pista = max_y - min_y if (max_y - min_y) > 0 else 1.0
    
    # Imponer el 5% de margen lateral mínimo por cada lado (90% de pantalla útil total)
    escala_x = (WIDTH * 0.90) / ancho_pista
    escala_y = (HEIGHT * 0.90) / alto_pista
    FACTOR_CAMARA = min(escala_x, escala_y)
    
    centro_pista = pygame.Vector2((min_x + max_x) / 2.0, (min_y + max_y) / 2.0)
    centro_pantalla = pygame.Vector2(WIDTH / 2.0, HEIGHT / 2.0)

# ////////////////////////////////////////////////////////////

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



# # ==========================================
# # --- LOGICA DE VISUALIZACIÓN DINÁMICA DE LA CARRERA ---
# ////////////////////////////////////////////////////////////

# --- BUCLE DE INTERFAZ GRÁFICA INTERACTIVA CON AUTOCIERRE ---
paso_actual = 1
running = True
tiempo_ultima_actividad = pygame.time.get_ticks()

'''
while running:
    tiempo_inactivo = (pygame.time.get_ticks() - tiempo_ultima_actividad) / 1000.0
    if tiempo_inactivo >= 60.0:
        print("=== APAGADO AUTOMÁTICO: Ventana cerrada por inactividad tras 1 minuto ===")
        running = False
        break
'''    

def mi_funcion_de_renderizado(pantalla_objetivo):
    """
    Aquí dentro pones EXCLUSIVAMENTE las líneas que antes estaban en tu bucle while
    y que se encargaban de dibujar el circuito. Asegúrate de sustituir 'pantalla_objetivo' por 'pantalla_objetivo'.
    """
    pantalla_objetivo.fill(COLOR_FONDO)
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
            rect_vis.center = (int(centro_c.x), int(centro_c.y))
            pantalla_objetivo.blit(surf_vis, rect_vis.topleft)
            
            p_C_camara = centro_pantalla + (pieza["sal_C"] - centro_pista) * FACTOR_CAMARA
            p_D_camara = centro_pantalla + (pieza["sal_D"] - centro_pista) * FACTOR_CAMARA
            pygame.draw.line(pantalla_objetivo, GRIS_LINEAS, p_C_camara, p_D_camara, GROSOR_DECORATIVO)

            if idx == 0 and len(despieze) > 0:
                cfg_primera = CATALOGO_PIEZAS[despieze[0]]
                angulo_r1 = ANGULO_INICIAL + cfg_primera["ang_correccion"]
                centro_m1 = pygame.Vector2(pieza["rect"].center)
                p_ent_A_mundo = centro_m1 + rotar_punto_local(cfg_primera["ent_local_A"], cfg_primera["centro_local"], angulo_r1)
                p_ent_B_mundo = centro_m1 + rotar_punto_local(cfg_primera["ent_local_B"], cfg_primera["centro_local"], angulo_r1)
                pygame.draw.line(pantalla_objetivo, GRIS_LINEAS, centro_pantalla + (p_ent_A_mundo - centro_pista) * FACTOR_CAMARA, centro_pantalla + (p_ent_B_mundo - centro_pista) * FACTOR_CAMARA, GROSOR_DECORATIVO)

            pygame.draw.circle(pantalla_objetivo, ROSA, (int(p_C_camara.x), int(p_C_camara.y)), int(max(3, 5 * FACTOR_CAMARA)))
            pygame.draw.circle(pantalla_objetivo, ROJO, (int(p_D_camara.x), int(p_D_camara.y)), int(max(3, 5 * FACTOR_CAMARA)))
    

    # --- TEXTO INFORMATIVO DE PRESENTACIÓN ---
    font = pygame.font.SysFont(None, 22)
    txt_info = f"Paso: {paso_actual}/{len(piezas_calculadas)} | String: '{cadena_entrada}' | Archivo: {nombre_archivo_final}"
    txt = font.render(txt_info, True, COLOR_LINEA)
    pantalla_objetivo.blit(txt, (20, 20))
    
    pygame.display.flip()
    clock.tick(60)

# Cierre limpio del hilo tras salir del bucle while running
pygame.quit()
sys.exit()


if __name__ == "__main__":
    # Inicializamos la pantalla con el nuevo módulo
    pantalla = inicializar_pantalla()

    # Arrancamos el loop pasándole nuestra función de dibujo
    ejecutar_bucle_principal(pantalla, mi_funcion_de_renderizado)
