# -*- coding: utf-8 -*-
"""
Marquesina Virtual MvM v1.0 (Flet) – PC + Android
- Windows: display + teclado numérico
- Android: display casi a todo el ancho; teclado sistema; zonas táctiles;
  barra inferior multifunción (en SELECT_DIRECCION: Volver estrecho + 1 + 2)
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
# 1. LED
# ---------------------------------------------------------------------------
CARACTERES_ANCHO = 22
ANCHO_FUENTE = 6
ALTO_FUENTE = 8
COLUMNAS_LED = CARACTERES_ANCHO * ANCHO_FUENTE
FILAS_POR_BLOQUE = ALTO_FUENTE
CANTIDAD_FILAS = 4
MARGEN_SUPERIOR = 1
FILAS_LED_TOTAL = (FILAS_POR_BLOQUE * CANTIDAD_FILAS) + MARGEN_SUPERIOR

TAMANO_LED = 6
ESPACIADO = 2
PIXEL_SIZE = TAMANO_LED + ESPACIADO
ANCHO_IMG = COLUMNAS_LED * PIXEL_SIZE
ALTO_IMG = FILAS_LED_TOTAL * PIXEL_SIZE
RATIO_DISPLAY = ANCHO_IMG / max(ALTO_IMG, 1)

COLOR_ENCENDIDO = (255, 204, 0)
COLOR_APAGADO = (35, 35, 0)
COLOR_FONDO = (10, 10, 10)
COLOR_EMT = "#0033A0"

BARRA_MIN_PX = 48
GAP_MIN_PX = 4
MARGEN_TACTIL = 0.15

TECLADO_COLS, TECLADO_FILAS = 3, 4
TECLADO_SPACING, TECLADO_PADDING = 6, 6
BTN_MIN, BTN_MAX = 36, 52
TECLADO_MAX_FRAC, TECLADO_MAX_PX = 0.30, 220

# ---------------------------------------------------------------------------
# 2. MODOS / ESTADO
# ---------------------------------------------------------------------------
class Modo(Enum):
    BIENVENIDA = auto()
    INPUT_PARADA = auto()
    LLEGADAS = auto()
    INPUT_LINEA = auto()
    SELECT_DIRECCION = auto()
    SELECT_PARADA = auto()
    INFO = auto()


class ModoTeclado(Enum):
    NAV = auto()
    NUM = auto()


modo_actual = Modo.BIENVENIDA
modo_teclado = ModoTeclado.NAV
es_android = False

linea_actual = None
cabeceras_actual = None
direccion_actual = None
lista_paradas = []
matrices_paradas = []
matriz_titulo_parada = None

ultima_parada = None
ultima_linea = None
REFRESCO_LLEGADAS_S = 15.0  # corrección 4
ultimo_fetch_ts = 0.0
refresco_en_curso = False

# Scroll: corr. 5 (H ×2) y 6 (V ×3)
PASO_V = 3.0
PASO_H = 16.0
VEL_V_BASE = 0.045
VEL_H_BASE = 1.2
NIVELES_V = [1.0, 1.75, 2.5, 3.5]
NIVELES_H = [1.0, 1.75, 2.5, 3.5]
nivel_v = nivel_h = 0
PAUSA_AUTO_S = 1.2
auto_pausado_hasta = 0.0
AUTO_DIR_V, AUTO_DIR_H = "down", "right"

offset_vertical = 0.0
offset_h = 0.0
offset_f1 = offset_f2 = offset_f3 = offset_f4 = 0.0
velocidad_f1 = velocidad_f2 = velocidad_f3 = velocidad_f4 = 0.0


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
    else:
        offset_vertical = max(0.0, offset_vertical - PASO_V)
        nivel_v = max(0, nivel_v - 1)
    pausar_auto()


def navegar_horizontal(direccion: str):
    global offset_h, offset_f1, offset_f2, offset_f3, offset_f4, nivel_h
    paso = PASO_H
    if direccion == "right":
        offset_h += paso
        offset_f1 += paso
        offset_f2 += paso
        offset_f3 += paso
        offset_f4 += paso
        if AUTO_DIR_H == "right":
            nivel_h = min(nivel_h + 1, len(NIVELES_H) - 1)
    else:
        offset_h = max(0.0, offset_h - paso)
        offset_f1 = max(0.0, offset_f1 - paso)
        offset_f2 = max(0.0, offset_f2 - paso)
        offset_f3 = max(0.0, offset_f3 - paso)
        offset_f4 = max(0.0, offset_f4 - paso)
        nivel_h = max(0, nivel_h - 1)
    pausar_auto()


# ---------------------------------------------------------------------------
# 3. FUENTE / TEXTO
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
                col.append(
                    superficie.get_at((x, y))[0] > 128 if y < alto else False
                )
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


def matriz_con_ciclo(texto: str) -> list:
    """
    Si el texto no cabe y se ciclará, añade '. ' al final para separar vueltas.
    """
    t = (texto or " ").rstrip()
    mat = generar_matriz_texto(t)
    if len(mat) > COLUMNAS_LED:
        if not t.endswith(". "):
            if t.endswith("."):
                t = t + " "
            else:
                t = t + ". "
            mat = generar_matriz_texto(t)
    return mat


def pixel_de_matriz(mat, x_led, y_rel, off_h=0.0):
    if not mat:
        return False
    ancho = len(mat)
    if ancho > COLUMNAS_LED:
        return mat[(x_led + int(off_h)) % ancho][y_rel]
    if x_led < ancho:
        return mat[x_led][y_rel]
    return False


def leer_info_mvm() -> str:
    candidatos = [
        BASE_DIR / "assets" / "info_mvm.txt",
        BASE_DIR / "info_mvm.txt",
    ]
    for p in candidatos:
        try:
            if p.is_file():
                return p.read_text(encoding="utf-8").strip()
        except Exception as e:
            print(f"No se pudo leer {p}: {e}")
    return (
        "MvM (v1.0). Marquesina virtual Madrid. Por David de Haro. "
        "Empleando la API de EMT-Madrid."
    )


# Textos de menú con acentuación correcta
MENU_TITULO = "Marquesina Virtual MvM"
MENU_LINEAS = [
    "1-Paradas  2-Líneas",
    "3-Ubicación  4-Info",
    "0-Salida",
]
matriz_titulo = generar_matriz_texto(MENU_TITULO)
matrices_opciones = [generar_matriz_texto(op) for op in MENU_LINEAS]

matriz_f1 = generar_matriz_texto(" ")
matriz_f2 = generar_matriz_texto(" ")
matriz_f3 = generar_matriz_texto(" ")
matriz_f4 = generar_matriz_texto(" ")
matriz_titulo_parada = generar_matriz_texto(" ")


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
        lineas = [matriz_titulo] + matrices_opciones
        for x_led in range(COLUMNAS_LED):
            for y_led in range(FILAS_LED_TOTAL):
                if y_led < MARGEN_SUPERIOR:
                    on = False
                else:
                    ya = y_led - MARGEN_SUPERIOR
                    bloque = ya // FILAS_POR_BLOQUE
                    yr = ya % FILAS_POR_BLOQUE
                    on = (
                        pixel_de_matriz(lineas[bloque], x_led, yr, 0.0)
                        if bloque < len(lineas)
                        else False
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
        mats = [matriz_f1, matriz_f2, matriz_f3, matriz_f4]
        offs = [offset_f1, offset_f2, offset_f3, offset_f4]
        for x_led in range(COLUMNAS_LED):
            for y_led in range(FILAS_LED_TOTAL):
                if y_led < MARGEN_SUPERIOR:
                    on = False
                else:
                    ya = y_led - MARGEN_SUPERIOR
                    bloque = min(ya // FILAS_POR_BLOQUE, 3)
                    yr = ya % FILAS_POR_BLOQUE
                    on = pixel_de_matriz(mats[bloque], x_led, yr, offs[bloque])
                pintar(x_led, y_led, on)

    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


# ---------------------------------------------------------------------------
# 4. TECLADO WINDOWS
# ---------------------------------------------------------------------------
class NumericKeypad(ft.Column):
    def __init__(self, on_key=None, btn_size: int = 44):
        super().__init__()
        self.on_key = on_key
        self.btn_size = btn_size
        self.spacing = TECLADO_SPACING
        self.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        self.tight = True
        self._build(btn_size)

    def _build(self, btn_size: int):
        self.controls.clear()
        self.btn_size = btn_size
        fs = 14 if btn_size >= 48 else 12
        keys = [
            [("1", "1"), ("2/↑", "2"), ("3", "3")],
            [("4/←", "4"), ("5", "5"), ("6/→", "6")],
            [("7", "7"), ("8/↓", "8"), ("9", "9")],
            [("⌫", "⌫"), ("0", "0"), ("↵", "↵")],
        ]
        for row in keys:
            btn_row = ft.Row(
                spacing=TECLADO_SPACING,
                alignment=ft.MainAxisAlignment.CENTER,
                tight=True,
            )
            for label, code in row:
                es = code in ("⌫", "↵")
                btn_row.controls.append(
                    ft.Button(
                        content=ft.Text(
                            label,
                            size=fs,
                            text_align=ft.TextAlign.CENTER,
                            no_wrap=True,
                            color=ft.Colors.WHITE,
                        ),
                        width=btn_size,
                        height=btn_size,
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=8),
                            bgcolor=COLOR_EMT if es else ft.Colors.BLUE_GREY_800,
                            padding=0,
                        ),
                        on_click=lambda e, c=code: self._handle(c),
                    )
                )
            self.controls.append(btn_row)

    def resize(self, btn_size: int):
        btn_size = int(max(BTN_MIN, min(BTN_MAX, btn_size)))
        if btn_size != self.btn_size:
            self._build(btn_size)

    def _handle(self, key: str):
        if self.on_key:
            self.on_key(key)

    def ancho_total(self) -> float:
        return (
            TECLADO_COLS * self.btn_size
            + (TECLADO_COLS - 1) * TECLADO_SPACING
            + 2 * TECLADO_PADDING
        )


def salir_programa(page: ft.Page):
    """Cierre completo (sin dejar la app en segundo plano)."""
    print("Cerrando Marquesina Virtual MvM...")
    try:
        page.window.destroy()
    except Exception:
        pass
    try:
        page.update()
    except Exception:
        pass
    time.sleep(0.15)
    # Forzar fin del proceso (Android / desktop)
    os._exit(0)


# ---------------------------------------------------------------------------
# 5. APP
# ---------------------------------------------------------------------------
def main(page: ft.Page):
    global modo_actual, modo_teclado, es_android
    global offset_vertical, offset_h
    global matriz_f1, matriz_f2, matriz_f3, matriz_f4
    global offset_f1, offset_f2, offset_f3, offset_f4
    global velocidad_f1, velocidad_f2, velocidad_f3, velocidad_f4
    global linea_actual, cabeceras_actual, direccion_actual
    global lista_paradas, matrices_paradas, matriz_titulo_parada
    global nivel_v, nivel_h
    global ultima_parada, ultima_linea, ultimo_fetch_ts, refresco_en_curso

    try:
        es_android = page.platform == ft.PagePlatform.ANDROID
    except Exception:
        es_android = False

    page.title = "Marquesina Virtual MvM"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#0a0a0a"
    page.padding = 4 if es_android else 8

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
        fit=ft.BoxFit.CONTAIN,
        gapless_playback=True,
    )
    disp_w = [float(ANCHO_IMG)]
    disp_h = [float(ALTO_IMG)]

    input_field = ft.TextField(
        value="",
        label="Entrada",
        width=280,
        height=48,
        text_size=18,
        text_align=ft.TextAlign.CENTER,
        border_color=COLOR_EMT,
        focused_border_color=COLOR_EMT,
        keyboard_type=ft.KeyboardType.TEXT,
        visible=False,
        autofocus=False,
    )

    status_text = ft.Text(
        "", size=11, color=ft.Colors.GREY_400, visible=not es_android
    )

    # Botones base (Android)
    btn_volver_dir = ft.Button(
        content=ft.Text("Volver", size=12, no_wrap=True, color=ft.Colors.WHITE),
        height=48,
        width=72,
        visible=False,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.BLUE_GREY_700,
            shape=ft.RoundedRectangleBorder(radius=6),
            padding=4,
        ),
    )
    btn_izq = ft.Button(
        content=ft.Text("Volver", size=13, no_wrap=True, color=ft.Colors.WHITE),
        expand=True,
        height=48,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.BLUE_GREY_800,
            shape=ft.RoundedRectangleBorder(radius=6),
            padding=4,
        ),
    )
    btn_der = ft.Button(
        content=ft.Text("OK", size=13, no_wrap=True, color=ft.Colors.WHITE),
        expand=True,
        height=48,
        style=ft.ButtonStyle(
            bgcolor=COLOR_EMT,
            shape=ft.RoundedRectangleBorder(radius=6),
            padding=4,
        ),
    )
    gap_box = ft.Container(height=GAP_MIN_PX)
    touch_stack = ft.Stack([led_image], width=ANCHO_IMG, height=ALTO_IMG)

    barra_botones = ft.Row(
        [btn_volver_dir, btn_izq, btn_der],
        spacing=6,
        alignment=ft.MainAxisAlignment.CENTER,
    )

    def set_captions(izq: str, der: str):
        btn_izq.content = ft.Text(izq, size=12, no_wrap=True, color=ft.Colors.WHITE)
        btn_der.content = ft.Text(der, size=12, no_wrap=True, color=ft.Colors.WHITE)
        try:
            btn_izq.update()
            btn_der.update()
        except Exception:
            pass

    def _trunc(s: str, n: int = 16) -> str:
        s = (s or "").strip()
        return s if len(s) <= n else s[: n - 1] + "…"

    def necesita_entrada() -> bool:
        if modo_actual in (Modo.INPUT_PARADA, Modo.INPUT_LINEA):
            return True
        if modo_actual == Modo.SELECT_PARADA and modo_teclado == ModoTeclado.NUM:
            return True
        return False

    def actualizar_captions():
        if not es_android:
            return
        # Volver estrecho solo en SELECT_DIRECCION
        en_dir = modo_actual == Modo.SELECT_DIRECCION
        btn_volver_dir.visible = en_dir
        try:
            btn_volver_dir.update()
        except Exception:
            pass

        if modo_actual == Modo.BIENVENIDA:
            set_captions("Salir", "Pulsa 1-4 en pantalla")
        elif modo_actual == Modo.INPUT_PARADA:
            if input_field.value:
                set_captions("Borrar", "Buscar parada")
            else:
                set_captions("Volver", "Teclado parada")
        elif modo_actual == Modo.INPUT_LINEA:
            if input_field.value:
                set_captions("Borrar", "Buscar línea")
            else:
                set_captions("Volver", "Teclado línea")
        elif modo_actual == Modo.SELECT_DIRECCION:
            a = _trunc((cabeceras_actual or {}).get("nameA", "1"))
            b = _trunc((cabeceras_actual or {}).get("nameB", "2"))
            set_captions(f"1→{a}", f"2→{b}")
        elif modo_actual == Modo.SELECT_PARADA:
            if modo_teclado == ModoTeclado.NAV:
                set_captions("Volver", "Escribir nº")
            elif input_field.value:
                set_captions("Borrar", "Ver llegadas")
            else:
                set_captions("Volver", "Teclado / NAV")
        elif modo_actual == Modo.LLEGADAS:
            set_captions("Volver", "Actualizar")
        elif modo_actual == Modo.INFO:
            set_captions("Volver", "Info MvM")

    async def abrir_teclado_async():
        if not es_android:
            return
        input_field.visible = True
        input_field.width = min(float(page.width or 320) - 24, 400)
        try:
            input_field.update()
            page.update()
        except Exception:
            pass
        await asyncio.sleep(0.15)
        try:
            input_field.focus()
            page.update()
        except Exception as ex:
            print("focus teclado:", ex)

    def abrir_teclado():
        if es_android:
            page.run_task(abrir_teclado_async)

    def ocultar_teclado_campo():
        if not es_android:
            return
        if not necesita_entrada():
            input_field.visible = False
            try:
                input_field.update()
            except Exception:
                pass

    def set_horizontal_texts(t1, t2, t3=" ", t4=" ", scroll=True):
        global matriz_f1, matriz_f2, matriz_f3, matriz_f4
        global offset_f1, offset_f2, offset_f3, offset_f4
        global velocidad_f1, velocidad_f2, velocidad_f3, velocidad_f4
        # matriz_con_ciclo: separador ". " si habrá bucle horizontal
        matriz_f1 = matriz_con_ciclo(t1)
        matriz_f2 = matriz_con_ciclo(t2)
        matriz_f3 = matriz_con_ciclo(t3)
        matriz_f4 = matriz_con_ciclo(t4)
        offset_f1 = offset_f2 = offset_f3 = offset_f4 = 0.0
        # Velocidades base ×2 respecto a diseño original de filas H
        b = 1.4 if scroll else 1.0
        velocidad_f1 = b if len(matriz_f1) > COLUMNAS_LED else 0.0
        velocidad_f2 = 1.0 if len(matriz_f2) > COLUMNAS_LED else 0.0
        velocidad_f3 = (2.0 if scroll else 1.0) if len(matriz_f3) > COLUMNAS_LED else 0.0
        velocidad_f4 = (2.0 if scroll else 1.0) if len(matriz_f4) > COLUMNAS_LED else 0.0

    def registrar_llegadas(parada, linea, textos):
        global ultima_parada, ultima_linea, ultimo_fetch_ts
        ultima_parada = str(parada)
        ultima_linea = str(linea) if linea else "all"
        ultimo_fetch_ts = time.monotonic()
        set_horizontal_texts(textos[0], textos[1], textos[2], textos[3])

    def zona(click, left, top, width, height):
        return ft.Container(
            left=left,
            top=top,
            width=max(width, 8),
            height=max(height, 8),
            bgcolor="#01FFFFFF",
            on_click=click,
        )

    def reconstruir_capas_tactiles():
        if not es_android:
            touch_stack.controls = [led_image]
            try:
                touch_stack.update()
            except Exception:
                pass
            return

        w, h = max(disp_w[0], 1), max(disp_h[0], 1)
        capas = [led_image]
        mx, my = MARGEN_TACTIL * w, MARGEN_TACTIL * h
        my_b = MARGEN_TACTIL * 0.85 * h

        if modo_actual == Modo.BIENVENIDA:
            # Celdas amplias: 1|2, 3|4, 0 a ancho completo (corr. 7–8)
            iw, ih = w - 2 * mx, h - my - my_b
            x0, y0 = mx, my
            capas += [
                zona(lambda e: manejar_tecla("1"), x0, y0 + 0.18 * ih, 0.48 * iw, 0.24 * ih),
                zona(lambda e: manejar_tecla("2"), x0 + 0.52 * iw, y0 + 0.18 * ih, 0.48 * iw, 0.24 * ih),
                zona(lambda e: manejar_tecla("3"), x0, y0 + 0.44 * ih, 0.48 * iw, 0.24 * ih),
                zona(lambda e: manejar_tecla("4"), x0 + 0.52 * iw, y0 + 0.44 * ih, 0.48 * iw, 0.24 * ih),
                zona(lambda e: manejar_tecla("0"), x0, y0 + 0.70 * ih, iw, 0.26 * ih),
            ]

        elif modo_actual == Modo.SELECT_DIRECCION:
            capas += [
                zona(lambda e: navegar_horizontal("left"), 0, 0, mx, h),
                zona(lambda e: navegar_horizontal("right"), w - mx, 0, mx, h),
            ]

        elif modo_actual == Modo.SELECT_PARADA and modo_teclado == ModoTeclado.NAV:
            capas += [
                zona(lambda e: navegar_vertical("up"), mx, 0, w - 2 * mx, my),
                zona(lambda e: navegar_vertical("down"), mx, h - my_b, w - 2 * mx, my_b),
                zona(lambda e: navegar_horizontal("left"), 0, my, mx, h - my - my_b),
                zona(lambda e: navegar_horizontal("right"), w - mx, my, mx, h - my - my_b),
                zona(lambda e: ir_a_num_parada(), mx, my, w - 2 * mx, h - my - my_b),
            ]

        elif modo_actual in (Modo.INPUT_PARADA, Modo.INPUT_LINEA):
            capas += [
                zona(lambda e: abrir_teclado(), mx, my, w - 2 * mx, h - my - my_b),
            ]

        elif modo_actual == Modo.INFO:
            capas += [
                zona(lambda e: navegar_horizontal("left"), 0, 0, mx, h),
                zona(lambda e: navegar_horizontal("right"), w - mx, 0, mx, h),
            ]

        touch_stack.controls = capas
        touch_stack.width = w
        touch_stack.height = h
        try:
            touch_stack.update()
        except Exception:
            pass

    def ir_a_num_parada():
        global modo_teclado
        modo_teclado = ModoTeclado.NUM
        actualizar_captions()
        reconstruir_capas_tactiles()
        abrir_teclado()

    def mostrar_info():
        texto = leer_info_mvm()
        set_horizontal_texts(texto, " ", " ", " ", scroll=True)
        cambiar_modo(Modo.INFO)

    def cambiar_modo(nuevo: Modo):
        global modo_actual, modo_teclado, offset_h, nivel_v, nivel_h
        modo_actual = nuevo
        offset_h = 0.0
        if nuevo not in (Modo.INPUT_PARADA, Modo.INPUT_LINEA, Modo.SELECT_PARADA):
            input_field.value = ""
        try:
            input_field.update()
        except Exception:
            pass

        if nuevo == Modo.BIENVENIDA:
            modo_teclado = ModoTeclado.NUM
            nivel_v = nivel_h = 0
            ocultar_teclado_campo()
        elif nuevo == Modo.INPUT_PARADA:
            modo_teclado = ModoTeclado.NUM
            set_horizontal_texts(
                "Introduzca parada ", "y confirme ", scroll=False
            )
            abrir_teclado()
        elif nuevo == Modo.INPUT_LINEA:
            modo_teclado = ModoTeclado.NUM
            set_horizontal_texts(
                "Introduzca línea (ej. SE1) ", "y confirme ", scroll=False
            )
            abrir_teclado()
        elif nuevo == Modo.SELECT_DIRECCION:
            modo_teclado = ModoTeclado.NUM
            ocultar_teclado_campo()
        elif nuevo == Modo.SELECT_PARADA:
            modo_teclado = ModoTeclado.NAV
            nivel_v = nivel_h = 0
            ocultar_teclado_campo()
        elif nuevo == Modo.LLEGADAS:
            modo_teclado = ModoTeclado.NUM
            ocultar_teclado_campo()
        elif nuevo == Modo.INFO:
            modo_teclado = ModoTeclado.NUM
            ocultar_teclado_campo()

        actualizar_captions()
        reconstruir_capas_tactiles()
        if page.width and page.height:
            aplicar_layout(float(page.width), float(page.height))

    def manejar_tecla(key: str):
        global modo_actual, modo_teclado
        global linea_actual, cabeceras_actual, direccion_actual
        global lista_paradas, matrices_paradas, matriz_titulo_parada
        global offset_vertical, offset_h

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
                set_horizontal_texts(
                    "Ubicación ", "Próximamente ", scroll=False
                )
                return
            if key == "4":
                mostrar_info()
                return
            if not es_android:
                if key == "8":
                    navegar_vertical("down")
                elif key == "4":
                    navegar_horizontal("left")
                elif key == "6":
                    navegar_horizontal("right")
            return

        if modo_actual == Modo.INFO:
            if key in ("⌫", "↵", "0"):
                cambiar_modo(Modo.BIENVENIDA)
            return

        if modo_actual == Modo.SELECT_PARADA:
            if key == "⌫":
                if input_field.value:
                    input_field.value = input_field.value[:-1]
                    input_field.update()
                    actualizar_captions()
                else:
                    cambiar_modo(Modo.SELECT_DIRECCION)
                return
            if key == "↵":
                if (input_field.value or "").strip():
                    parada = input_field.value.strip()
                    textos = stop_query.busca_info(
                        stop=parada, line=linea_actual or "all"
                    )
                    if textos:
                        registrar_llegadas(parada, linea_actual or "all", textos)
                        cambiar_modo(Modo.LLEGADAS)
                    return
                if modo_teclado == ModoTeclado.NAV:
                    ir_a_num_parada()
                else:
                    modo_teclado = ModoTeclado.NAV
                    ocultar_teclado_campo()
                    actualizar_captions()
                    reconstruir_capas_tactiles()
                return
            if modo_teclado == ModoTeclado.NAV and key in ("2", "4", "6", "8"):
                {
                    "2": lambda: navegar_vertical("up"),
                    "8": lambda: navegar_vertical("down"),
                    "4": lambda: navegar_horizontal("left"),
                    "6": lambda: navegar_horizontal("right"),
                }[key]()
                return
            if len(key) == 1 and (key.isdigit() or key.isalpha()):
                if modo_teclado == ModoTeclado.NAV and key in ("2", "4", "6", "8"):
                    return
                modo_teclado = ModoTeclado.NUM
                input_field.value = (input_field.value or "") + key.upper()
                input_field.visible = True
                input_field.update()
                actualizar_captions()
                reconstruir_capas_tactiles()
            return

        if modo_actual == Modo.INPUT_PARADA:
            if key == "⌫":
                if input_field.value:
                    input_field.value = input_field.value[:-1]
                    input_field.update()
                    actualizar_captions()
                else:
                    cambiar_modo(Modo.BIENVENIDA)
                return
            if key == "↵":
                parada = (input_field.value or "").strip()
                if not parada:
                    abrir_teclado()
                    return
                textos = stop_query.busca_info(stop=parada, line="all")
                if textos:
                    lista_paradas = []
                    registrar_llegadas(parada, "all", textos)
                    cambiar_modo(Modo.LLEGADAS)
                return
            if len(key) == 1 and key.isdigit():
                input_field.value = (input_field.value or "") + key
                input_field.update()
                actualizar_captions()
            return

        if modo_actual == Modo.INPUT_LINEA:
            if key == "⌫":
                if input_field.value:
                    input_field.value = input_field.value[:-1]
                    input_field.update()
                    actualizar_captions()
                else:
                    cambiar_modo(Modo.BIENVENIDA)
                return
            if key == "↵":
                linea = (input_field.value or "").strip()
                if not linea:
                    abrir_teclado()
                    return
                cabeceras = list_query.obtener_cabeceras_linea(linea)
                if not cabeceras:
                    set_horizontal_texts("Línea no encontrada ", " ", scroll=False)
                    return
                linea_actual = cabeceras.get("label") or linea
                cabeceras_actual = cabeceras
                set_horizontal_texts(
                    f"Línea {linea_actual} ",
                    f"1: {cabeceras['nameA']} -> {cabeceras['nameB']} ",
                    f"2: {cabeceras['nameB']} -> {cabeceras['nameA']} ",
                    "Elija sentido ",
                    scroll=True,
                )
                cambiar_modo(Modo.SELECT_DIRECCION)
                return
            if len(key) == 1 and (key.isdigit() or key.isalpha()):
                input_field.value = (input_field.value or "") + key.upper()
                input_field.update()
                actualizar_captions()
            return

        if modo_actual == Modo.SELECT_DIRECCION:
            if key == "⌫":
                cambiar_modo(Modo.INPUT_LINEA)
                return
            if key in ("1", "2"):
                direccion_actual = int(key)
                paradas = list_query.obtener_paradas_linea(
                    linea_actual, direction=direccion_actual
                )
                if not paradas:
                    set_horizontal_texts("Sin paradas ", " ", scroll=False)
                    return
                lista_paradas = paradas
                matrices_paradas = []
                for p in paradas:
                    matrices_paradas.append(
                        matriz_con_ciclo(f"-Parada: {p['stop']}:")
                    )
                    matrices_paradas.append(
                        matriz_con_ciclo(f" {p['name']}")
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
                matriz_titulo_parada = matriz_con_ciclo(
                    f"L{linea_actual} {sentido} "
                )
                offset_vertical = 0.0
                offset_h = 0.0
                cambiar_modo(Modo.SELECT_PARADA)
            return

        if modo_actual == Modo.LLEGADAS:
            if key == "⌫":
                if lista_paradas:
                    offset_vertical = 0.0
                    offset_h = 0.0
                    cambiar_modo(Modo.SELECT_PARADA)
                else:
                    cambiar_modo(Modo.BIENVENIDA)
            elif key == "↵" and ultima_parada:
                textos = stop_query.busca_info(
                    stop=ultima_parada, line=ultima_linea or "all"
                )
                if textos:
                    registrar_llegadas(
                        ultima_parada, ultima_linea or "all", textos
                    )
            return

    def on_btn_izq(e):
        if modo_actual == Modo.SELECT_DIRECCION:
            manejar_tecla("1")
        elif modo_actual == Modo.BIENVENIDA:
            manejar_tecla("0")  # Salir
        else:
            manejar_tecla("⌫")

    def on_btn_der(e):
        if modo_actual == Modo.SELECT_DIRECCION:
            manejar_tecla("2")
            return
        if modo_actual in (Modo.INPUT_PARADA, Modo.INPUT_LINEA):
            if (input_field.value or "").strip():
                manejar_tecla("↵")
            else:
                abrir_teclado()
            return
        if modo_actual == Modo.SELECT_PARADA:
            if modo_teclado == ModoTeclado.NAV:
                ir_a_num_parada()
            elif (input_field.value or "").strip():
                manejar_tecla("↵")
            else:
                abrir_teclado()
            return
        if modo_actual == Modo.INFO:
            manejar_tecla("⌫")
            return
        manejar_tecla("↵")

    def on_btn_volver_dir(e):
        manejar_tecla("⌫")

    btn_izq.on_click = on_btn_izq
    btn_der.on_click = on_btn_der
    btn_volver_dir.on_click = on_btn_volver_dir

    input_field.on_submit = lambda e: manejar_tecla("↵")
    input_field.on_change = lambda e: actualizar_captions()

    display_container = ft.Container(
        content=touch_stack,
        bgcolor="#050505",
        padding=2,
        border_radius=8,
        border=ft.Border.all(2, COLOR_EMT),
        alignment=ft.Alignment.CENTER,
    )

    keypad = None
    if es_android:
        # Corrección 1: Entrada ENCIMA del display
        page.add(
            ft.Column(
                [
                    input_field,
                    display_container,
                    gap_box,
                    barra_botones,
                ],
                spacing=4,
                expand=True,
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )
    else:
        keypad = NumericKeypad(on_key=manejar_tecla, btn_size=44)
        input_field.visible = False
        page.add(
            ft.Row(
                [
                    display_container,
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(
                                    "Control",
                                    size=12,
                                    weight=ft.FontWeight.BOLD,
                                    color=COLOR_EMT,
                                ),
                                input_field,
                                keypad,
                                status_text,
                            ],
                            spacing=4,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            tight=True,
                        ),
                        padding=TECLADO_PADDING,
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
                expand=True,
            )
        )

    def aplicar_layout(page_w: float, page_h: float):
        if page_w <= 0 or page_h <= 0:
            return
        pad = 8
        W = max(page_w - pad, 200)
        H = max(page_h - pad, 120)

        if es_android:
            bar_h = max(BARRA_MIN_PX, H * 0.12)
            gap_h = max(GAP_MIN_PX, H * 0.01)
            input_h = 52 if (necesita_entrada() or input_field.visible) else 0
            h_rest = max(H - bar_h - gap_h - input_h, 80)

            w_disp = W
            h_disp = w_disp / RATIO_DISPLAY
            if h_disp > h_rest:
                h_disp = h_rest
                w_disp = h_disp * RATIO_DISPLAY

            led_image.width = w_disp
            led_image.height = h_disp
            touch_stack.width = w_disp
            touch_stack.height = h_disp
            display_container.width = w_disp + 4
            display_container.height = h_disp + 4
            disp_w[0], disp_h[0] = w_disp, h_disp

            gap_box.height = gap_h
            btn_izq.height = bar_h
            btn_der.height = bar_h
            btn_volver_dir.height = bar_h
            if input_field.visible:
                input_field.width = min(W - 16, 420)

            reconstruir_capas_tactiles()
        else:
            max_tw = min(W * TECLADO_MAX_FRAC, TECLADO_MAX_PX)
            btn_a = (
                max_tw
                - 2 * TECLADO_PADDING
                - (TECLADO_COLS - 1) * TECLADO_SPACING
            ) / TECLADO_COLS
            btn_hh = (
                H
                - 56
                - 2 * TECLADO_PADDING
                - (TECLADO_FILAS - 1) * TECLADO_SPACING
            ) / TECLADO_FILAS
            btn = int(max(BTN_MIN, min(BTN_MAX, btn_a, btn_hh)))
            if keypad:
                keypad.resize(btn)
                tw = keypad.ancho_total()
            else:
                tw = 180
            w_max = max(W - tw - 8, 120)
            h_max = H
            if w_max / h_max > RATIO_DISPLAY:
                h_disp = h_max
                w_disp = min(h_disp * RATIO_DISPLAY, w_max)
                h_disp = w_disp / RATIO_DISPLAY
            else:
                w_disp = w_max
                h_disp = min(w_disp / RATIO_DISPLAY, h_max)
                w_disp = h_disp * RATIO_DISPLAY
            led_image.width = w_disp
            led_image.height = h_disp
            touch_stack.width = w_disp
            touch_stack.height = h_disp
            display_container.width = w_disp + 10
            display_container.height = h_disp + 10
            disp_w[0], disp_h[0] = w_disp, h_disp

        try:
            page.update()
        except Exception:
            pass

    def on_resized(e):
        w = getattr(e, "width", None) or page.width
        h = getattr(e, "height", None) or page.height
        if w and h:
            aplicar_layout(float(w), float(h))

    try:
        page.on_resized = on_resized
    except Exception:
        pass

    cambiar_modo(Modo.BIENVENIDA)
    aplicar_layout(float(page.width or 900), float(page.height or 400))

    async def layout_bootstrap():
        for d in (0.2, 0.5, 1.0):
            await asyncio.sleep(d)
            if page.width and page.height:
                aplicar_layout(float(page.width), float(page.height))

    async def watchdog_orientacion():
        prev = (page.width, page.height)
        while True:
            await asyncio.sleep(0.5)
            cur = (page.width, page.height)
            if cur != prev and cur[0] and cur[1]:
                aplicar_layout(float(cur[0]), float(cur[1]))
                prev = cur

    async def animation_loop():
        global offset_vertical, offset_h
        global offset_f1, offset_f2, offset_f3, offset_f4
        while True:
            if modo_actual == Modo.SELECT_PARADA and auto_activo():
                offset_vertical += velocidad_v_actual()
                offset_h += velocidad_h_actual()
            elif modo_actual not in (Modo.BIENVENIDA, Modo.SELECT_PARADA):
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
            if modo_actual != Modo.LLEGADAS or not ultima_parada or refresco_en_curso:
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
                    textos = stop_query.busca_info(
                        stop=ultima_parada, line=ultima_linea or "all"
                    )
                if modo_actual == Modo.LLEGADAS and textos:
                    set_horizontal_texts(
                        textos[0], textos[1], textos[2], textos[3]
                    )
                    ultimo_fetch_ts = time.monotonic()
                else:
                    ultimo_fetch_ts = time.monotonic() - REFRESCO_LLEGADAS_S + 5.0
            except Exception as ex:
                print("Refresco:", ex)
                ultimo_fetch_ts = time.monotonic() - REFRESCO_LLEGADAS_S + 5.0
            finally:
                refresco_en_curso = False

    page.run_task(layout_bootstrap)
    page.run_task(watchdog_orientacion)
    page.run_task(animation_loop)
    page.run_task(refresco_llegadas_loop)


def _es_spyder() -> bool:
    return any(k.startswith("SPYDER") for k in os.environ)


if __name__ == "__main__":
    if _es_spyder() or os.environ.get("MCPY_WEB") == "1":
        ft.run(main, view=ft.AppView.WEB_BROWSER)
    else:
        ft.run(main)
