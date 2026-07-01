# -*- coding: utf-8 -*-
"""
Created on Mon Jun 29 23:48:00 2026

@author: Matasiete
Proyecto McPy.


Versiones:


"""

# SVGmain2.py
#import math
import copy
import matplotlib.pyplot as plt
from shapely.affinity import translate, rotate
import SVGreader
import Biblioteca   # ← Para consultar forma y terrenos
import arquitecto

# Brújula de rumbos (por forma)
DESVIACION_BRUJULA = {
    "R": 0, "RC": 0,
    "CI90": -90, "CD90": 90,
    "CI45": -45, "CD45": 45,
    "SCD": 180, "SCI": 180,
    "RTD": 90, "RTI": -90,
}


def alinear_pieza_por_rumbo(pieza_fija, pieza_movil, rumbo_actual):
    hitbox = pieza_movil["hitbox"]
    entrada = pieza_movil["entrada"]
    salida = pieza_movil["salida"]
    id_actual = pieza_movil["id_pieza"]
    
    
    # Traslación
    tx = pieza_fija["salida"].x - entrada.x
    ty = pieza_fija["salida"].y - entrada.y
    hitbox_situada = translate(hitbox, xoff=tx, yoff=ty)
    entrada_situada = pieza_fija["salida"]
    salida_situada = translate(salida, xoff=tx, yoff=ty)

    # Ángulo de rotación base
    angulo_final_rotacion = rumbo_actual
        
    # Aplicar rotación
    if angulo_final_rotacion != 0:
        hitbox_final = rotate(hitbox_situada, angle=angulo_final_rotacion,
                              origin=(entrada_situada.x, entrada_situada.y))
        salida_final = rotate(salida_situada, angle=angulo_final_rotacion,
                              origin=(entrada_situada.x, entrada_situada.y))
    else:
        hitbox_final = hitbox_situada
        salida_final = salida_situada

    return {
        "id_pieza": id_actual,
        "hitbox": hitbox_final,
        "entrada": entrada_situada,
        "salida": salida_final,
        "colisiona": False
    }


def construir_y_dibujar_circuito(secuencia_claves, titulo="Circuito Flamme Rouge"):
    """Construye y dibuja un circuito a partir de una lista de claves reales de losetas."""
    if not secuencia_claves:
        print("❌ Secuencia vacía")
        return None
    
    # Cargar catálogo usando las formas reales
    catalogo = {}
    for clave in secuencia_claves:
        forma = Biblioteca.Losetas[clave][1]   # Ej: "R", "CD90", "SCD", etc.
        try:
            # Muchas losetas comparten el mismo SVG según su forma
            nombre_svg = forma if forma not in ["RC"] else forma
            catalogo[clave] = SVGreader.extraer_geometria_loseta_completa(f"{nombre_svg}.svg")
            catalogo[clave]["id_pieza"] = clave  # Guardamos la clave real
        except Exception as e:
            print(f"⚠️ Error cargando SVG para {clave} (forma {forma}): {e}")
    
    # Construcción del circuito
    circuito_colocado = []
    rumbo_acumulado = 0
    print (secuencia_claves)
    for i, clave in enumerate(secuencia_claves):
        if clave not in catalogo:
            continue
            
        pieza_base = copy.deepcopy(catalogo[clave])
        
        if i == 0:
            pieza_base["colisiona"] = False
            circuito_colocado.append(pieza_base)
            forma = Biblioteca.Losetas[clave][1]
            rumbo_acumulado += DESVIACION_BRUJULA.get(forma, 0)
        else:
            ultima_colocada = circuito_colocado[-1]
            pieza_alineada = alinear_pieza_por_rumbo(ultima_colocada, pieza_base, rumbo_acumulado)
           
            # Detección de colisión
            hitbox_auditoria = pieza_alineada["hitbox"].buffer(-0.59)
            colision_estructural = any(
                hitbox_auditoria.intersection(p["hitbox"]).area > 1.0 
                for p in circuito_colocado
            )
            
            '''
            # Detectada una colisión con el circuito vuelve para reiniciar
            print(colision_estructural)
            if colision_estructural:
                input() 
                return False
            #else:
            '''
            
            pieza_alineada["colisiona"] = colision_estructural
            circuito_colocado.append(pieza_alineada)
                
            forma = Biblioteca.Losetas[clave][1]
            rumbo_acumulado += DESVIACION_BRUJULA.get(forma, 0)
   
    # Renderizado
    fig, ax = plt.subplots(figsize=(14, 14))
    ax.set_facecolor('#f0f0f0')
   
    for pieza in circuito_colocado:
        x, y = pieza["hitbox"].exterior.xy
        color = "#d32f2f" if pieza["colisiona"] else "#44aa00"
        ax.fill(x, y, fc=color, ec="black", lw=1.8, alpha=0.75)
       
        # Etiqueta con el nombre real de la loseta
        centro = pieza["hitbox"].centroid
        ax.text(centro.x, centro.y, pieza["id_pieza"], 
                fontsize=10, ha='center', va='center', color='white', weight='bold')
       
        ax.plot(pieza["entrada"].x, pieza["entrada"].y, "go", markersize=6)
        ax.plot(pieza["salida"].x, pieza["salida"].y, "ro", markersize=6)
   
    ax.set_aspect('equal')
    ax.invert_yaxis()
    ax.grid(True, linestyle=':', alpha=0.5)
    plt.title(f"{titulo}\n{secuencia_claves}")
    plt.show()
   
    return circuito_colocado

'''
# Prueba directa
if __name__ == "__main__":
    # Ejemplo de secuencia con claves reales
    secuencia_prueba = ["a", "d", "1'", "9", "e", "h'", "x'", "z", "v", "m"]
    
    construir_y_dibujar_circuito(secuencia_prueba, "Circuito de Prueba")
'''
if __name__ == "__main__":
    
    #for intentos in range (300):
        # Crear una instancia del arquitecto
        builder = arquitecto.crear_arquitecto()   # o arquitecto.arquitecto()
        
        # Generar el circuito (máximo 2000 intentos por defecto)
        secuencia_prueba = builder.generar_circuito_valido()
        
        if secuencia_prueba:
            circuito_completo = construir_y_dibujar_circuito(secuencia_prueba, "Circuito de Prueba")    # -----> ya lo ha mandado a pantalla.
        else:
            print("No se pudo generar un circuito válido.")
            '''
        if circuito_completo:
            print(f"Circuito válido creado en {intentos} intentos")
        else:
            print(f"No se pudo generar un circuito válido tras {intentos} intentos")
            '''  

