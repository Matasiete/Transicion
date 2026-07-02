# -*- coding: utf-8 -*-
"""
Created on Mon Jun 29 23:23:50 2026

@author: Matasiete
Proyecto McPy.


Versiones:


"""

import random
import copy
from shapely.affinity import translate, rotate
import Biblioteca  # Importamos la biblioteca real de losetas
import SVGreader   # Importamos para extraer la geometría teórica antes de validar

# Brújula de rumbos (por forma) extraída de SVGmain
DESVIACION_BRUJULA = {
    "R": 0, "RC": 0,
    "CI90": -90, "CD90": 90,
    "CI45": -45, "CD45": 45,
    "SCD": 180, "SCI": 180,
    "RTD": 90, "RTI": -90,
}

class arquitecto:
    def __init__(self):
        self.losetas = Biblioteca.Losetas
        self.piezas_usadas = set()   # Piezas físicas ya usadas (incluye primos)
        self.catalogo_geometria = {} # Caché para las formas base cargadas de SVGreader
        
    def _obtener_pieza_y_primo(self, clave):
        """Devuelve la clave y su versión prima (cara opuesta)"""
        if clave.endswith("'"):
            primo = clave[:-1]
        else:
            primo = clave + "'"
        return clave, primo if primo in self.losetas else None

    def _puede_usar_pieza(self, clave):
        """Verifica si la loseta y su primo están disponibles"""
        clave, primo = self._obtener_pieza_y_primo(clave)
        return clave not in self.piezas_usadas and (primo is None or primo not in self.piezas_usadas)

    def _marcar_pieza_usada(self, clave):
        """Marca la loseta y su primo como usadas"""
        clave, primo = self._obtener_pieza_y_primo(clave)
        self.piezas_usadas.add(clave)
        if primo:
            self.piezas_usadas.add(primo)

    def _desmarcar_pieza_usada(self, clave):
        """Libera la loseta y su primo al hacer backtracking"""
        clave, primo = self._obtener_pieza_y_primo(clave)
        if clave in self.piezas_usadas:
            self.piezas_usadas.remove(clave)
        if primo and primo in self.piezas_usadas:
            self.piezas_usadas.remove(primo)

    def _cargar_geometria_base(self, clave):
        """Carga y almacena en caché la estructura espacial limpia de la pieza."""
        forma = self.losetas[clave][1]
        if forma not in self.catalogo_geometria:
            try:
                nombre_svg = forma  # El SVG se llama igual que la forma
                geo = SVGreader.extraer_geometria_loseta_completa(f"{nombre_svg}.svg")
                self.catalogo_geometria[forma] = geo
            except Exception as e:
                print(f"⚠️ Error cargando geometría base para forma {forma}: {e}")
                return None
        return copy.deepcopy(self.catalogo_geometria[forma])

    def _alinear_pieza_en_espacio(self, pieza_fija, pieza_movil, rumbo_actual):
        """Calcula la posición de la pieza móvil acoplada a la pieza fija usando su rumbo."""
        hitbox = pieza_movil["hitbox"]
        entrada = pieza_movil["entrada"]
        salida = pieza_movil["salida"]
        
        # Traslación al extremo de salida de la loseta anterior
        tx = pieza_fija["salida"].x - entrada.x
        ty = pieza_fija["salida"].y - entrada.y
        
        hitbox_situada = translate(hitbox, xoff=tx, yoff=ty)
        entrada_situada = pieza_fija["salida"]
        salida_situada = translate(salida, xoff=tx, yoff=ty)

        # Aplicar la rotación acumulada del rumbo
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

    def _backtrack_construccion(self, circuito_claves, circuito_geometrias, rumbo_acumulado, longitud_objetivo):
        """Algoritmo de backtracking recursivo paso a paso."""
        paso_actual = len(circuito_claves)

        # Caso Base: Circuito completado con la longitud deseada (falta solo la meta)
        if paso_actual == longitud_objetivo - 1:
            posibles_meta = [k for k in self.losetas.keys() 
                             if 'm' in self.losetas[k][2] and self._puede_usar_pieza(k)]
            random.shuffle(posibles_meta)
            
            for meta in posibles_meta:
                pieza_base = self._cargar_geometria_base(meta)
                if not pieza_base:
                    continue
                
                ultima_colocada = circuito_geometrias[-1]
                pieza_alineada = self._alinear_pieza_en_espacio(ultima_colocada, pieza_base, rumbo_acumulado)
                
                # Validar colisión de la meta con margen de seguridad (-0.59)
                hitbox_auditoria = pieza_alineada["hitbox"].buffer(-0.59)
                colisiona = any(hitbox_auditoria.intersection(p["hitbox"]).area > 1.0 for p in circuito_geometrias)
                
                if not colisiona:
                    circuito_claves.append(meta)
                    circuito_geometrias.append(pieza_alineada)
                    self._marcar_pieza_usada(meta)
                    return True
            return False

        # Determinar restricciones del tronco central
        es_segunda_posicion = (paso_actual == 1)
        
        if es_segunda_posicion and random.random() < 0.45:
            candidatos = [k for k in self.losetas.keys() if 'd' in self.losetas[k][2] and self._puede_usar_pieza(k)]
        else:
            candidatos = [k for k in self.losetas.keys() 
                          if 'm' not in self.losetas[k][2] and 'i' not in self.losetas[k][2] 
                          and self._puede_usar_pieza(k)]
            
        random.shuffle(candidatos)

        # Probar candidatos de forma aleatoria estructurada
        for pieza_cand in candidatos:
            pieza_base = self._cargar_geometria_base(pieza_cand)
            if not pieza_base:
                continue
                
            ultima_colocada = circuito_geometrias[-1]
            pieza_alineada = self._alinear_pieza_en_espacio(ultima_colocada, pieza_base, rumbo_acumulado)
            
            # Comprobación estricta de colisiones antes de comprometer la pieza
            hitbox_auditoria = pieza_alineada["hitbox"].buffer(-0.59)
            colisiona = any(hitbox_auditoria.intersection(p["hitbox"]).area > 1.0 for p in circuito_geometrias)
            
            if not colisiona:
                # La pieza es geométricamente válida. Avanzamos.
                circuito_claves.append(pieza_cand)
                circuito_geometrias.append(pieza_alineada)
                self._marcar_pieza_usada(pieza_cand)
                
                forma = self.losetas[pieza_cand][1]
                nuevo_rumbo = rumbo_acumulado + DESVIACION_BRUJULA.get(forma, 0)
                
                # Intentar rellenar el siguiente eslabón del circuito (Recursión)
                if self._backtrack_construccion(circuito_claves, circuito_geometrias, nuevo_rumbo, longitud_objetivo):
                    return True
                    
                # Si los pasos futuros fallan, retrocedemos (Deshacer)
                self._desmarcar_pieza_usada(pieza_cand)
                circuito_geometrias.pop()
                circuito_claves.pop()
                
        return False  # Ninguna pieza funcionó en esta rama, forzar backtracking arriba

    def generar_circuito_valido(self, max_intentos=50):
        """Inicia el proceso de backtracking matemático puro."""
        for intento in range(max_intentos):
            self.piezas_usadas.clear()
            
            dados = sum(random.randint(1, 2) for _ in range(3))
            longitud_objetivo = 14 + dados
            
            # 1. Colocar Loseta de Inicio (salida)
            posibles_inicios = [k for k in self.losetas.keys() 
                                if 'i' in self.losetas[k][2] and self._puede_usar_pieza(k)]
            if not posibles_inicios:
                continue
            inicio = random.choice(posibles_inicios)
            
            pieza_base = self._cargar_geometria_base(inicio)
            if not pieza_base:
                continue
                
            # Inicializar las listas de control del árbol de decisiones
            circuito_claves = [inicio]
            circuito_geometrias = [{
                "hitbox": pieza_base["hitbox"],
                "entrada": pieza_base["entrada"],
                "salida": pieza_base["salida"]
            }]
            self._marcar_pieza_usada(inicio)
            
            forma = self.losetas[inicio][1]
            rumbo_inicial = DESVIACION_BRUJULA.get(forma, 0)
            
            # Lanzar el motor recursivo
            if self._backtrack_construccion(circuito_claves, circuito_geometrias, rumbo_inicial, longitud_objetivo):
                print(f"✅ Circuito geométrico perfecto generado ({len(circuito_claves)} losetas) en intento {intento+1}")
                return circuito_claves
                
        print("❌ El algoritmo no encontró una solución geométrica válida libre de colisiones.")
        return None

# Factory
def crear_arquitecto():
    return arquitecto()
