# -*- coding: utf-8 -*-
"""
Marquesina Virtual (Flet) – PC + Android
Menú: Bienvenida | Consulta parada | Por línea
- Bienvenida: 1/2/3/0 = menú; 8/4/6 = scroll manual (paso fijo)
- SELECT_PARADA: ↵ vacío = alterna NAV/NUM; ↵ con texto = confirmar
- Autoscroll + paso fijo; misma dirección que el auto → sube nivel de velocidad
- Llegadas: refresco debounced cada 30 s
"""

import os
import sys
import time
import asyncio
import base64
from io import BytesIO
from pathlib import Path
from enum import Enum, auto

try:
    import nest_asyncio
    nest_asyncio.apply()
except Exception:
    pass

import flet as ft
from PIL import Image, ImageDraw, ImageFont

import list_query
import stop_query

# ---------------------------------------------------------------------------
# 1. CONFIGURACIÓN LED
# ---------------------------------------------------------------------------
CARACTERES_ANCHO = 22
ANCHO_FUENTE = 6
ALTO_FUENTE = 8
COLUMNAS_LED = CARACTERES_ANCHO * ANCHO_FUENTE
FILAS_POR_BLOQUE = ALTO_FUENTE
CANTIDAD_FILAS = 4
MARGEN_SUPERIOR = 1
FILAS_LED_TOTAL = (FILAS_POR_BLOQUE * CANTIDAD_FILAS) + MARGEN_SUPERIOR

TAMANO_LED = 4
ESPACIADO = 1
PIXEL_SIZE = TAMANO_LED + ESPACIADO

ANCHO_IMG = COLUMNAS_LED * PIXEL_SIZE
ALTO_IMG = FILAS_LED_TOTAL * PIXEL_SIZE

COLOR_ENCENDIDO = (255, 204, 0)
COLOR_APAGADO = (35, 35, 0)
COLOR_FONDO = (10, 10, 10)
COLOR_EMT = "#0033A0"

# ---------------------------------------------------------------------------
# 2. MODOS APP + TECLADO
# ---------------------------------------------------------------------------
class Modo(Enum):
    BIENVENIDA = auto()
    INPUT_PARADA = auto()
    LLEGADAS = auto()
    INPUT_LINEA = auto()
    SELECT_DIRECCION = auto()
    SELECT_PARADA = auto()


class ModoTeclado(Enum):
    NAV = auto()
    NUM = auto()


modo_actual = Modo.BIENVENIDA
modo_teclado = ModoTeclado.NAV

linea_actual = None
cabeceras_actual = None
direccion_actual = None
lista_paradas = []
matrices_paradas = []
matriz_titulo_parada = None

# Llegadas / refresco
ultima_parada = None
ultima_linea = None
REFRESCO_LLEGADAS_S = 30.0
ultimo_fetch_ts = 0.0
refresco_en_curso = False

# ---------------------------------------------------------------------------
# 3. SCROLL
# ---------------------------------------------------------------------------
PASO_V = 1.0
PASO_H = 8.0
VEL_V_BASE = 0.015
VEL_H_BASE = 0.6
NIVELES_V = [1.0, 1.75, 2.5, 3.5]
NIVELES_H = [1.0, 1.75, 2.5, 3.5]
nivel_v = 0
nivel_h = 0
PAUSA_AUTO_S = 1.2
auto_pausado_hasta = 0.0
AUTO_DIR_V = "down"
AUTO_DIR_H = "right"

offset_vertical = 0.0
offset_h = 0.0


def pausar_auto():
    global auto_pausado_hasta
    auto_pausado_hasta = time.time() + PAUSA_AUTO_S


def auto_activo() -> bool:
    return time.time() >= auto_pausado_hasta


def velocidad_v_actual() -> float:
    return VEL_V_BASE * NIVELES_V[min(nivel_v, len(NIVELES_V) - 1)]


def velocidad_h_actual() -> float:
    return VEL_H_BASE * NIVELES_H[min(nivel_h, len(NIVELES_H) - 1)]


def navegar_vertical(direccion: str):
    global offset_vertical, nivel_v
    if direccion == "down":
        offset_vertical += PASO_V
        if AUTO_DIR_V == "down":
            nivel_v = min(nivel_v + 1, len(NIVELES_V) - 1)
    elif direccion == "up":
        offset_vertical = max(0.0, offset_vertical - PASO_V)
        nivel_v = max(0, nivel_v - 1)
    pausar_auto()


def navegar_horizontal(direccion: str):
    global offset_h, nivel_h
    if direccion == "right":
        offset_h += PASO_H
        if AUTO_DIR_H == "right":
            nivel_h = min(nivel_h + 1, len(NIVELES_H) - 1)
    elif direccion == "left":
        offset_h = max(0.0, offset_h - PASO_H)
        nivel_h = max(0, nivel_h - 1)
    pausar_auto()


# ---------------------------------------------------------------------------
# 4. FUENTE
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent


def resolver_fuente() -> Path:
    nombre = "Mx437_Portfolio_6x8.ttf"
    for p in (BASE_DIR / "assets" / nombre, BASE_DIR / nombre):
        if p.is_file():
            return p
    return BASE_DIR / "assets" / nombre


RUTA_FUENTE = resolver_fuente()
_USE_PYGAME = False
_fuente_pygame = None
_fuente_pil = None

try:
    import pygame

    pygame.init()
    if RUTA_FUENTE.is_file():
        _fuente_pygame = pygame.font.Font(str(RUTA_FUENTE), FILAS_POR_BLOQUE)
        _USE_PYGAME = True
except Exception as e:
    print(f"pygame no disponible ({e}); Pillow.")

if not _USE_PYGAME:
    if RUTA_FUENTE.is_file():
        try:
            _fuente_pil = ImageFont.truetype(str(RUTA_FUENTE), FILAS_POR_BLOQUE)
        except Exception:
            _fuente_pil = ImageFont.load_default()
    else:
        _fuente_pil = ImageFont.load_default()


def generar_matriz_texto(texto: str) -> list:
    if _USE_PYGAME and _fuente_pygame is not None:
        texto_bytes = texto.encode("cp437", errors="ignore").decode("cp437")
        superficie = _fuente_pygame.render(
            texto_bytes, False, (255, 255, 255), (0, 0, 0)
        )
        ancho, alto = superficie.get_size()
        matriz = []
        for x in range(ancho):
            col = []
            for y in range(FILAS_POR_BLOQUE):
                if y < alto:
                    col.append(superficie.get_at((x, y))[0] > 128)
                else:
                    col.append(False)
            matriz.append(col)
        return matriz

    ancho_tmp = max(len(texto) * ANCHO_FUENTE + 8, COLUMNAS_LED)
    img = Image.new("L", (ancho_tmp, FILAS_POR_BLOQUE), 0)
    draw = ImageDraw.Draw(img)
    draw.text((0, 0), texto, fill=255, font=_fuente_pil)
    bbox = img.getbbox()
    if bbox:
        img = img.crop((bbox[0], 0, bbox[2], FILAS_POR_BLOQUE))
    ancho, alto = img.size
    matriz = []
    for x in range(ancho):
        col = []
        for y in range(FILAS_POR_BLOQUE):
            col.append(img.getpixel((x, y)) > 128 if y < alto else False)
        matriz.append(col)
    return matriz or [[False] * FILAS_POR_BLOQUE]


def pixel_de_matriz(mat, x_led, y_rel, off_h=0.0):
    if not mat:
        return False
    ancho = len(mat)
    if ancho > COLUMNAS_LED:
        return mat[(x_led + int(off_h)) % ancho][y_rel]
    if x_led < ancho:
        return mat[x_led][y_rel]
    return False


MENU_OPCIONES = [
    "1-Consulta parada",
    "2-Por linea",
    "3-Geolocalizacion (prox)",
    "0-Salir",
]
titulo_bienvenida = "Marquesina Virtual"
matriz_titulo = generar_matriz_texto(titulo_bienvenida)
matrices_opciones = [generar_matriz_texto(op) for op in MENU_OPCIONES]

matriz_f1 = generar_matriz_texto(" ")
matriz_f2 = generar_matriz_texto(" ")
matriz_f3 = generar_matriz_texto(" ")
matriz_f4 = generar_matriz_texto(" ")
offset_f1 = offset_f2 = offset_f3 = offset_f4 = 0.0
velocidad_f1 = velocidad_f2 = velocidad_f3 = velocidad_f4 = 0.0
matriz_titulo_parada = generar_matriz_texto(" ")


# ---------------------------------------------------------------------------
# 5. RENDER
# ---------------------------------------------------------------------------
def render_led_image() -> str:
    img = Image.new("RGB", (ANCHO_IMG, ALTO_IMG), COLOR_FONDO)
    draw = ImageDraw.Draw(img)

    def pintar(x_led, y_led, on):
        color = COLOR_ENCENDIDO if on else COLOR_APAGADO
        cx = x_led * PIXEL_SIZE + TAMANO_LED // 2
        cy = y_led * PIXEL_SIZE + TAMANO_LED // 2
        r = TAMANO_LED // 2
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)

    if modo_actual == Modo.BIENVENIDA:
        n = len(matrices_opciones)
        for x_led in range(COLUMNAS_LED):
            for y_led in range(FILAS_LED_TOTAL):
                if y_led < MARGEN_SUPERIOR:
                    on = False
                else:
                    ya = y_led - MARGEN_SUPERIOR
                    bloque = ya // FILAS_POR_BLOQUE
                    yr = ya % FILAS_POR_BLOQUE
                    if bloque == 0:
                        on = pixel_de_matriz(matriz_titulo, x_led, yr, offset_h)
                    else:
                        idx = (bloque - 1 + int(offset_vertical)) % n
                        on = pixel_de_matriz(
                            matrices_opciones[idx], x_led, yr, offset_h
                        )
                pintar(x_led, y_led, on)

    elif modo_actual == Modo.SELECT_PARADA:
        n = max(len(matrices_paradas), 1)
        for x_led in range(COLUMNAS_LED):
            for y_led in range(FILAS_LED_TOTAL):
                if y_led < MARGEN_SUPERIOR:
                    on = False
                else:
                    ya = y_led - MARGEN_SUPERIOR
                    bloque = ya // FILAS_POR_BLOQUE
                    yr = ya % FILAS_POR_BLOQUE
                    if bloque == 0:
                        on = pixel_de_matriz(
                            matriz_titulo_parada, x_led, yr, offset_h
                        )
                    else:
                        idx = (bloque - 1 + int(offset_vertical)) % n
                        on = pixel_de_matriz(
                            matrices_paradas[idx], x_led, yr, offset_h
                        )
                pintar(x_led, y_led, on)

    else:
        for x_led in range(COLUMNAS_LED):
            for y_led in range(FILAS_LED_TOTAL):
                if y_led < MARGEN_SUPERIOR:
                    on = False
                else:
                    ya = y_led - MARGEN_SUPERIOR
                    bloque = ya // FILAS_POR_BLOQUE
                    yr = ya % FILAS_POR_BLOQUE
                    if bloque == 0:
                        on = pixel_de_matriz(matriz_f1, x_led, yr, offset_f1)
                    elif bloque == 1:
                        on = pixel_de_matriz(matriz_f2, x_led, yr, offset_f2)
                    elif bloque == 2:
                        on = pixel_de_matriz(matriz_f3, x_led, yr, offset_f3)
                    else:
                        on = pixel_de_matriz(matriz_f4, x_led, yr, offset_f4)
                pintar(x_led, y_led, on)

    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


# ---------------------------------------------------------------------------
# 6. TECLADO
# ---------------------------------------------------------------------------
class NumericKeypad(ft.Column):
    def __init__(self, on_key=None, width=220):
        super().__init__()
        self.on_key = on_key
        self.spacing = 8
        self.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        self.width = width

        keys = [
            [("1", "1"), ("2/↑", "2"), ("3", "3")],
            [("4/←", "4"), ("5", "5"), ("6/→", "6")],
            [("7", "7"), ("8/↓", "8"), ("9", "9")],
            [("⌫", "⌫"), ("0", "0"), ("↵", "↵")],
        ]
        for row in keys:
            btn_row = ft.Row(spacing=8, alignment=ft.MainAxisAlignment.CENTER)
            for label, code in row:
                es_esp = code in ("⌫", "↵")
                btn = ft.Button(
                    content=label,
                    width=60,
                    height=55,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=8),
                        bgcolor=COLOR_EMT if es_esp else ft.Colors.BLUE_GREY_800,
                        color=ft.Colors.WHITE,
                    ),
                    on_click=lambda e, c=code: self._handle(c),
                )
                btn_row.controls.append(btn)
            self.controls.append(btn_row)

    def _handle(self, key: str):
        if self.on_key:
            self.on_key(key)


# ---------------------------------------------------------------------------
# 7. CIERRE
# ---------------------------------------------------------------------------
def salir_programa(page: ft.Page):
    print("Cerrando Marquesina Virtual...")
    try:
        page.window.destroy()
    except Exception:
        pass
    try:
        page.update()
    except Exception:
        pass
    time.sleep(0.25)
    try:
        sys.exit(0)
    except SystemExit:
        os._exit(0)


# ---------------------------------------------------------------------------
# 8. APP
# ---------------------------------------------------------------------------
def main(page: ft.Page):
    global modo_actual, modo_teclado, offset_vertical, offset_h
    global matriz_f1, matriz_f2, matriz_f3, matriz_f4
    global offset_f1, offset_f2, offset_f3, offset_f4
    global velocidad_f1, velocidad_f2, velocidad_f3, velocidad_f4
    global linea_actual, cabeceras_actual, direccion_actual
    global lista_paradas, matrices_paradas, matriz_titulo_parada
    global nivel_v, nivel_h
    global ultima_parada, ultima_linea, ultimo_fetch_ts, refresco_en_curso

    page.title = "Marquesina Virtual"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#0a0a0a"
    page.padding = 10

    try:
        if page.platform in (
            ft.PagePlatform.WINDOWS,
            ft.PagePlatform.MACOS,
            ft.PagePlatform.LINUX,
        ):
            page.window.width = 1100
            page.window.height = 520
    except Exception:
        pass

    led_image = ft.Image(
        src=f"data:image/png;base64,{render_led_image()}",
        width=ANCHO_IMG,
        height=ALTO_IMG,
        fit=ft.BoxFit.NONE,
        gapless_playback=True,
    )

    input_field = ft.TextField(
        label="Entrada",
        value="",
        width=220,
        text_align=ft.TextAlign.CENTER,
        border_color=COLOR_EMT,
        focused_border_color=COLOR_EMT,
        visible=False,
    )

    status_text = ft.Text("Menu principal", size=13, color=ft.Colors.GREY_400)

    def actualizar_status(msg=None):
        base = msg if msg is not None else (status_text.value or "")
        if " | NAV" in str(base) or " | NUM" in str(base):
            base = str(base).split(" | ")[0]
        if modo_actual == Modo.SELECT_PARADA:
            tag = "NAV" if modo_teclado == ModoTeclado.NAV else "NUM"
            status_text.value = f"{base} | {tag}"
        else:
            status_text.value = str(base)
        try:
            status_text.update()
        except Exception:
            pass

    def set_horizontal_texts(t1, t2, t3=" ", t4=" ", scroll=True):
        global matriz_f1, matriz_f2, matriz_f3, matriz_f4
        global offset_f1, offset_f2, offset_f3, offset_f4
        global velocidad_f1, velocidad_f2, velocidad_f3, velocidad_f4
        matriz_f1 = generar_matriz_texto(t1)
        matriz_f2 = generar_matriz_texto(t2)
        matriz_f3 = generar_matriz_texto(t3)
        matriz_f4 = generar_matriz_texto(t4)
        offset_f1 = offset_f2 = offset_f3 = offset_f4 = 0.0
        b = 0.7 if scroll else 0.5
        velocidad_f1 = b if len(matriz_f1) > COLUMNAS_LED else 0.0
        velocidad_f2 = 0.5 if len(matriz_f2) > COLUMNAS_LED else 0.0
        velocidad_f3 = (1.0 if scroll else 0.5) if len(matriz_f3) > COLUMNAS_LED else 0.0
        velocidad_f4 = (1.0 if scroll else 0.5) if len(matriz_f4) > COLUMNAS_LED else 0.0

    def registrar_llegadas(parada, linea, textos):
        """Aplica textos al display y reinicia debounce de refresco."""
        global ultima_parada, ultima_linea, ultimo_fetch_ts, lista_paradas
        ultima_parada = str(parada)
        ultima_linea = str(linea) if linea else "all"
        ultimo_fetch_ts = time.monotonic()
        set_horizontal_texts(textos[0], textos[1], textos[2], textos[3])

    def cambiar_modo(nuevo_modo: Modo):
        global modo_actual, modo_teclado, offset_h, nivel_v, nivel_h
        modo_actual = nuevo_modo
        offset_h = 0.0
        input_field.value = ""
        input_field.visible = nuevo_modo in (
            Modo.INPUT_PARADA,
            Modo.INPUT_LINEA,
            Modo.SELECT_PARADA,
        )
        try:
            input_field.update()
        except Exception:
            pass

        if nuevo_modo == Modo.BIENVENIDA:
            modo_teclado = ModoTeclado.NUM
            nivel_v = nivel_h = 0
            actualizar_status("Menu principal – 1/2/3/0 elige | 8/4/6 scroll")
        elif nuevo_modo == Modo.INPUT_PARADA:
            modo_teclado = ModoTeclado.NUM
            actualizar_status("Numero de parada + Intro")
            set_horizontal_texts(
                "Introduzca numero de parada ", "y pulse Intro ", scroll=False
            )
        elif nuevo_modo == Modo.INPUT_LINEA:
            modo_teclado = ModoTeclado.NUM
            actualizar_status("Numero de linea + Intro")
            set_horizontal_texts(
                "Introduzca numero de linea ", "y pulse Intro ", scroll=False
            )
        elif nuevo_modo == Modo.SELECT_DIRECCION:
            modo_teclado = ModoTeclado.NUM
            actualizar_status("1 o 2 = sentido   ⌫ = volver")
        elif nuevo_modo == Modo.SELECT_PARADA:
            modo_teclado = ModoTeclado.NAV
            nivel_v = nivel_h = 0
            actualizar_status("Lista paradas – ↵ NAV/NUM")
        elif nuevo_modo == Modo.LLEGADAS:
            modo_teclado = ModoTeclado.NUM
            actualizar_status(
                f"Parada {ultima_parada or ''} – refresco {int(REFRESCO_LLEGADAS_S)}s"
            )

    def on_key_press(key: str):
        global modo_actual, modo_teclado
        global matriz_f1, matriz_f2, matriz_f3, matriz_f4
        global offset_f1, offset_f2, offset_f3, offset_f4
        global velocidad_f1, velocidad_f2, velocidad_f3, velocidad_f4
        global linea_actual, cabeceras_actual, direccion_actual
        global lista_paradas, matrices_paradas, matriz_titulo_parada
        global offset_vertical, offset_h

        # ----- BIENVENIDA -----
        if modo_actual == Modo.BIENVENIDA:
            if key in ("⌫", "0"):
                salir_programa(page)
                return
            if key == "1":
                cambiar_modo(Modo.INPUT_PARADA)
                return
            if key == "2":
                cambiar_modo(Modo.INPUT_LINEA)
                return
            if key == "3":
                actualizar_status("Geolocalizacion – proximamente")
                return
            if key == "8":
                navegar_vertical("down")
                return
            if key == "4":
                navegar_horizontal("left")
                return
            if key == "6":
                navegar_horizontal("right")
                return
            return

        # ----- SELECT_PARADA -----
        if modo_actual == Modo.SELECT_PARADA:
            if key == "⌫":
                if input_field.value:
                    input_field.value = input_field.value[:-1]
                    input_field.update()
                else:
                    cambiar_modo(Modo.SELECT_DIRECCION)
                return

            if key == "↵":
                if input_field.value.strip():
                    parada = input_field.value.strip()
                    actualizar_status(f"Consultando parada {parada}...")
                    try:
                        textos = stop_query.busca_info(
                            stop=parada, line=linea_actual or "all"
                        )
                        if not textos:
                            actualizar_status("Error al obtener llegadas")
                            return
                        registrar_llegadas(parada, linea_actual or "all", textos)
                        cambiar_modo(Modo.LLEGADAS)
                        actualizar_status(
                            f"Parada {parada} / L{linea_actual or 'all'}"
                        )
                    except Exception as e:
                        actualizar_status(f"Error: {e}")
                    return
                # Alternar NAV ↔ NUM
                if modo_teclado == ModoTeclado.NAV:
                    modo_teclado = ModoTeclado.NUM
                    actualizar_status("Escribe nº parada")
                else:
                    modo_teclado = ModoTeclado.NAV
                    actualizar_status("Lista paradas – 2/8 scroll")
                return

            if modo_teclado == ModoTeclado.NAV and key in ("2", "4", "6", "8"):
                if key == "2":
                    navegar_vertical("up")
                elif key == "8":
                    navegar_vertical("down")
                elif key == "4":
                    navegar_horizontal("left")
                elif key == "6":
                    navegar_horizontal("right")
                actualizar_status(f"Lista – vel V x{NIVELES_V[nivel_v]:.2g}")
                return

            if key.isdigit():
                if modo_teclado == ModoTeclado.NAV and key in ("2", "4", "6", "8"):
                    return
                modo_teclado = ModoTeclado.NUM
                input_field.value += key
                input_field.update()
                actualizar_status("Escribe nº parada")
            return

        # ----- INPUT_PARADA -----
        if modo_actual == Modo.INPUT_PARADA:
            if key == "⌫":
                if input_field.value:
                    input_field.value = input_field.value[:-1]
                else:
                    cambiar_modo(Modo.BIENVENIDA)
                input_field.update()
                return
            if key == "↵":
                parada = input_field.value.strip()
                if not parada:
                    actualizar_status("Introduce un numero de parada")
                    return
                actualizar_status(f"Consultando parada {parada}...")
                try:
                    textos = stop_query.busca_info(stop=parada, line="all")
                    if not textos:
                        actualizar_status("Error al obtener datos")
                        return
                    lista_paradas = []
                    registrar_llegadas(parada, "all", textos)
                    cambiar_modo(Modo.LLEGADAS)
                    actualizar_status(f"Parada {parada} – ⌫ volver")
                except Exception as e:
                    actualizar_status(f"Error: {e}")
                return
            if key.isdigit():
                input_field.value += key
                input_field.update()
            return

        # ----- INPUT_LINEA -----
        if modo_actual == Modo.INPUT_LINEA:
            if key == "⌫":
                if input_field.value:
                    input_field.value = input_field.value[:-1]
                else:
                    cambiar_modo(Modo.BIENVENIDA)
                input_field.update()
                return
            if key == "↵":
                linea = input_field.value.strip()
                if not linea:
                    actualizar_status("Introduce un numero de linea")
                    return
                actualizar_status(f"Consultando linea {linea}...")
                cabeceras = list_query.obtener_cabeceras_linea(linea)
                if not cabeceras:
                    actualizar_status("Linea no encontrada o error API")
                    return
                linea_actual = cabeceras.get("label") or linea
                cabeceras_actual = cabeceras
                set_horizontal_texts(
                    f"Linea {linea_actual} ",
                    f"1: {cabeceras['nameA']} -> {cabeceras['nameB']} ",
                    f"2: {cabeceras['nameB']} -> {cabeceras['nameA']} ",
                    "Elige 1 o 2 ",
                    scroll=True,
                )
                cambiar_modo(Modo.SELECT_DIRECCION)
                return
            if key.isdigit() or key.isalpha():
                input_field.value += key.upper()
                input_field.update()
            return

        # ----- SELECT_DIRECCION -----
        if modo_actual == Modo.SELECT_DIRECCION:
            if key == "⌫":
                cambiar_modo(Modo.INPUT_LINEA)
                return
            if key in ("1", "2"):
                direccion_actual = int(key)
                actualizar_status("Cargando paradas...")
                paradas = list_query.obtener_paradas_linea(
                    linea_actual, direction=direccion_actual
                )
                if not paradas:
                    actualizar_status("No se obtuvieron paradas")
                    return
                lista_paradas = paradas
                matrices_paradas = []
                for p in paradas:
                    matrices_paradas.append(
                        generar_matriz_texto(f"-Parada: {p['stop']}:")
                    )
                    matrices_paradas.append(
                        generar_matriz_texto(f" {p['name']}")
                    )
                if direccion_actual == 1:
                    sentido = (
                        f"{cabeceras_actual['nameA']}->"
                        f"{cabeceras_actual['nameB']}"
                    )
                else:
                    sentido = (
                        f"{cabeceras_actual['nameB']}->"
                        f"{cabeceras_actual['nameA']}"
                    )
                matriz_titulo_parada = generar_matriz_texto(
                    f"L{linea_actual} {sentido} "
                )
                offset_vertical = 0.0
                offset_h = 0.0
                cambiar_modo(Modo.SELECT_PARADA)
                actualizar_status(f"{len(paradas)} paradas – ↵ NAV/NUM")
            return

        # ----- LLEGADAS -----
        if modo_actual == Modo.LLEGADAS:
            if key == "⌫":
                if lista_paradas:
                    offset_vertical = 0.0
                    offset_h = 0.0
                    cambiar_modo(Modo.SELECT_PARADA)
                else:
                    cambiar_modo(Modo.BIENVENIDA)
            return

    keypad = NumericKeypad(on_key=on_key_press)

    display_container = ft.Container(
        content=led_image,
        bgcolor="#050505",
        padding=8,
        border_radius=8,
        border=ft.Border.all(2, COLOR_EMT),
    )

    right_panel = ft.Column(
        [
            ft.Text(
                "Teclado de control",
                size=16,
                weight=ft.FontWeight.BOLD,
                color=COLOR_EMT,
            ),
            input_field,
            keypad,
            status_text,
            ft.Text(
                "Bienvenida: 1/2/3/0 menu | 8/4/6 scroll\n"
                "Lista: ↵ vacio=NAV/NUM | ↵ con texto=OK\n"
                "Llegadas: auto-refresco 30s (debounce)",
                size=11,
                color=ft.Colors.GREY_500,
            ),
        ],
        spacing=10,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        scroll=ft.ScrollMode.AUTO,
    )

    page.add(
        ft.Row(
            [
                display_container,
                ft.VerticalDivider(width=16, color=ft.Colors.TRANSPARENT),
                right_panel,
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            wrap=True,
        )
    )

    cambiar_modo(Modo.BIENVENIDA)

    async def animation_loop():
        global offset_vertical, offset_h
        global offset_f1, offset_f2, offset_f3, offset_f4

        while True:
            if modo_actual in (Modo.BIENVENIDA, Modo.SELECT_PARADA):
                if auto_activo():
                    offset_vertical += velocidad_v_actual()
                    offset_h += velocidad_h_actual()
            else:
                offset_f1 += velocidad_f1
                offset_f2 += velocidad_f2
                offset_f3 += velocidad_f3
                offset_f4 += velocidad_f4

            led_image.src = f"data:image/png;base64,{render_led_image()}"
            try:
                led_image.update()
            except Exception:
                pass
            await asyncio.sleep(1 / 30)

    async def refresco_llegadas_loop():
        global ultimo_fetch_ts, refresco_en_curso

        while True:
            await asyncio.sleep(0.5)

            if modo_actual != Modo.LLEGADAS:
                continue
            if not ultima_parada:
                continue
            if refresco_en_curso:
                continue
            if time.monotonic() - ultimo_fetch_ts < REFRESCO_LLEGADAS_S:
                continue

            refresco_en_curso = True
            try:
                try:
                    textos = await asyncio.to_thread(
                        stop_query.busca_info,
                        ultima_parada,
                        ultima_linea or "all",
                    )
                except AttributeError:
                    # Python sin to_thread o entorno limitado
                    textos = stop_query.busca_info(
                        stop=ultima_parada, line=ultima_linea or "all"
                    )

                if modo_actual != Modo.LLEGADAS:
                    continue
                if not textos:
                    ultimo_fetch_ts = (
                        time.monotonic() - REFRESCO_LLEGADAS_S + 5.0
                    )
                    continue

                set_horizontal_texts(
                    textos[0], textos[1], textos[2], textos[3]
                )
                ultimo_fetch_ts = time.monotonic()
                try:
                    status_text.value = (
                        f"Parada {ultima_parada} – actualizado"
                    )
                    status_text.update()
                except Exception:
                    pass
            except Exception as e:
                print(f"Refresco llegadas: {e}")
                ultimo_fetch_ts = time.monotonic() - REFRESCO_LLEGADAS_S + 5.0
            finally:
                refresco_en_curso = False

    page.run_task(animation_loop)
    page.run_task(refresco_llegadas_loop)


def _es_spyder() -> bool:
    return any(k.startswith("SPYDER") for k in os.environ)


if __name__ == "__main__":
    if _es_spyder() or os.environ.get("MCPY_WEB") == "1":
        ft.run(main, view=ft.AppView.WEB_BROWSER)
    else:
        ft.run(main)
