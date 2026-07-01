# -*- coding: utf-8 -*-
"""
Created on Mon Jun 29 23:23:50 2026

@author: Matasiete
Proyecto McPy.


Versiones:


"""

# arquitecto.py
# arquitecto.py
import random
import copy
import Biblioteca  # Importamos la biblioteca real de losetas

class arquitecto:
    def __init__(self):
        self.losetas = Biblioteca.Losetas
        self.piezas_usadas = set()   # Piezas físicas ya usadas (incluye primos)
        
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

    def generar_circuito_valido(self, max_intentos=2):
        """Genera una secuencia válida de claves de losetas según las reglas."""
        for intento in range(max_intentos):
            self.piezas_usadas.clear()
            circuito = []
            
            # Longitud del circuito: 14 + 3d2 → 17 a 20 losetas
            dados = sum(random.randint(1, 2) for _ in range(3))
            longitud = 14 + dados
            
            # 1. Loseta de Inicio (salida)
            posibles_inicios = [k for k in self.losetas.keys() 
                              if 'i' in self.losetas[k][2] 
                              and self._puede_usar_pieza(k)]
            if not posibles_inicios:
                continue
            inicio = random.choice(posibles_inicios)
            circuito.append(inicio)
            self._marcar_pieza_usada(inicio)
            
            # 2. Demarraje en segunda posición (opcional pero con probabilidad)
            if random.random() < 0.45:   # ~45% de probabilidades de tener demarraje
                posibles_d = [k for k in self.losetas.keys() 
                            if 'd' in self.losetas[k][2] 
                            and self._puede_usar_pieza(k)]
                if posibles_d:
                    demarraje = random.choice(posibles_d)
                    circuito.append(demarraje)
                    self._marcar_pieza_usada(demarraje)
            
            # 3. Rellenar el resto del circuito
            exito = True
            for _ in range(len(circuito), longitud - 1):
                posibles = [k for k in self.losetas.keys() 
                            if not 'm' in self.losetas[k][2]
                            and self._puede_usar_pieza(k)]
                if not posibles:
                    exito = False
                    break
                siguiente = random.choice(posibles)
                circuito.append(siguiente)
                self._marcar_pieza_usada(siguiente)
            
            if not exito:
                continue
                
            # 4. Loseta de Meta al final
            posibles_meta = [k for k in self.losetas.keys() 
                           if 'm' in self.losetas[k][2] 
                           and self._puede_usar_pieza(k)]
            if not posibles_meta:
                continue
            meta = random.choice(posibles_meta)
            circuito.append(meta)
            self._marcar_pieza_usada(meta)
            
            print(f"✅ Circuito válido generado ({len(circuito)} losetas) en intento {intento+1}")
            return circuito
            
        print("❌ No se encontró un circuito válido después de muchos intentos.")
        return None


# Factory
def crear_arquitecto():
    return arquitecto()
