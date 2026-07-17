# -*- coding: utf-8 -*-
"""
Created on Thu Jun 18 18.54 2026

@author: Matasiete
Proyecto McPy.


Versiones: V28
    

Eventos: 
    Post:   Refactorizacion de McPyGen
            
"""
# regeometria.py

from shapely.affinity import translate, rotate
import math
import pygame


def rotar_punto_local(punto_local, centro_local, angulo_grados):
    """
    Rota un punto alrededor de un centro local.
    """
    angulo_rad = math.radians(-angulo_grados)

    rx = punto_local.x - centro_local.x
    ry = punto_local.y - centro_local.y

    nx = rx * math.cos(angulo_rad) - ry * math.sin(angulo_rad)
    ny = rx * math.sin(angulo_rad) + ry * math.cos(angulo_rad)

    return pygame.Vector2(nx, ny)


def procesar_y_conectar_pieza(
        codigo,
        eje_conexion_mundo,
        angulo_acumulado,
        catalogo_piezas):
    """
    Procesa una pieza del catálogo y devuelve:

    superficie_rotada
    rect_posicionado
    salida_C
    salida_D
    nuevo_angulo
    """

    if codigo not in catalogo_piezas:
        print(f"Error: La pieza '{codigo}' no existe en el catálogo.")
        return None

    cfg = catalogo_piezas[codigo]

    angulo_render = angulo_acumulado + cfg["ang_correccion"]

    surf_rotada = pygame.transform.rotate(
        cfg["superficie"],
        angulo_render
    )

    rect_pieza = surf_rotada.get_rect()

    eje_entrada_local = (
        cfg["ent_local_A"] +
        cfg["ent_local_B"]
    ) / 2.0

    v_ent_rotado = rotar_punto_local(
        eje_entrada_local,
        cfg["centro_local"],
        angulo_render
    )

    centro_mundo = eje_conexion_mundo - v_ent_rotado

    rect_pieza.center = (
        int(round(centro_mundo.x)),
        int(round(centro_mundo.y))
    )

    mundo_sal_C = (
        centro_mundo +
        rotar_punto_local(
            cfg["sal_local_C"],
            cfg["centro_local"],
            angulo_render
        )
    )

    mundo_sal_D = (
        centro_mundo +
        rotar_punto_local(
            cfg["sal_local_D"],
            cfg["centro_local"],
            angulo_render
        )
    )

    nuevo_angulo = (
        angulo_acumulado +
        cfg["aporte_angular"]
    )

    return (
        surf_rotada,
        rect_pieza,
        mundo_sal_C,
        mundo_sal_D,
        nuevo_angulo
    )

def alinear_pieza(pieza_fija, pieza_movil, rumbo_actual):
    """
    Alinea una pieza móvil respecto a una fija.
    - Traslada la pieza móvil para que su punto de entrada coincida con la salida de la fija.
    - Luego aplica una rotación alrededor de la entrada según el ángulo rumbo_actual.
    Retorna un diccionario con:
        'hitbox': Polygon trasladado y rotado
        'entrada': Point (coincide con la salida de la pieza fija)
        'salida': Point trasladado y rotado
    """
    hitbox = pieza_movil["hitbox"]
    entrada = pieza_movil["entrada"]
    salida = pieza_movil["salida"]

    tx = pieza_fija["salida"].x - entrada.x
    ty = pieza_fija["salida"].y - entrada.y

    hitbox_situada = translate(hitbox, xoff=tx, yoff=ty)
    entrada_situada = pieza_fija["salida"]  # Punto Shapely
    salida_situada = translate(salida, xoff=tx, yoff=ty)

    if rumbo_actual != 0:
        hitbox_final = rotate(hitbox_situada, angle=rumbo_actual,
                              origin=(entrada_situada.x, entrada_situada.y))
        salida_final = rotate(salida_situada, angle=rumbo_actual,
                              origin=(entrada_situada.x, entrada_situada.y))
    else:
        hitbox_final = hitbox_situada
        salida_final = salida_situada

    return {
        "hitbox": hitbox_final,
        "entrada": entrada_situada,
        "salida": salida_final
    }

