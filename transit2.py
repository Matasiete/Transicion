# -*- coding: utf-8 -*-
"""
Marquesina Virtual MvM v1.3.2 (Flet) – Windows + Android

Versión 1.3.2:
- Geolocator en page.services (NO overlay) — evita Unknown control
- Flujo Ubicación con coords GPS reales en APK
- Preferencias en ruta escribible
- Info y Ayuda no preguntan guardar
"""

import os
import sys
import time
import json
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
import location_query

# --- Geolocator (paquete opcional; en APK debe ir en pyproject + flutter deps) ---
HAS_GEO_PKG = False
Geolocator = None
GeolocatorConfiguration = None
GeolocatorPositionAccuracy = None
_geo_import_err = None
try:
    import flet_geolocator as ftg
    Geolocator = getattr(ftg, "Geolocator", None)
    GeolocatorConfiguration = getattr(ftg, "GeolocatorConfiguration", None)
    GeolocatorPositionAccuracy = getattr(ftg, "GeolocatorPositionAccuracy", None)
    HAS_GEO_PKG = Geolocator is not None
    if not HAS_GEO_PKG:
        _geo_import_err = "Geolocator class missing in flet_geolocator"
except Exception as e1:
    _geo_import_err = repr(e1)

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
MARGEN_TACTIL = 0.12
DOBLE_TOQUE_S = 0.45

TECLADO_COLS, TECLADO_FILAS = 3, 4
TECLADO_SPACING, TECLADO_PADDING = 6, 6
BTN_MIN, BTN_MAX = 36, 52
TECLADO_MAX_FRAC, TECLADO_MAX_PX = 0.30, 220

BASE_DIR = Path(__file__).resolve().parent


def _prefs_candidates() -> list:
    """Rutas posibles de prefs (Android necesita almacenamiento de la app)."""
    out = []
    for key in ("FLET_APP_STORAGE_DATA", "FLET_APP_STORAGE", "HOME"):
        v = os.environ.get(key)
        if v:
            out.append(Path(v) / "marquesina_prefs.json")
            out.append(Path(v) / ".marquesina_virtual" / "prefs.json")
    out.append(BASE_DIR / "prefs.json")
    out.append(Path.home() / ".marquesina_virtual" / "prefs.json")
    # únicos
    seen = set()
    uniq = []
    for p in out:
        s = str(p)
        if s not in seen:
            seen.add(s)
            uniq.append(p)
    return uniq


prefs = {
    "parada": "",
    "linea": "",
    "sentido": 0,
    "lon": None,
    "lat": None,
    "radius": 200,
}
_prefs_path_used = None


def cargar_prefs():
    global prefs, _prefs_path_used
    for p in _prefs_candidates():
        try:
            if p.is_file():
                data = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    for k in prefs:
                        if k in data:
                            prefs[k] = data[k]
                    _prefs_path_used = p
                    print("Preferencias cargadas desde:", p)
                    return
        except Exception as e:
            print("Prefs load try", p, e)


def guardar_prefs() -> bool:
    global _prefs_path_used
    payload = json.dumps(prefs, ensure_ascii=False, indent=2)
    errors = []
    # Preferir la ruta que ya funcionó al cargar
    ordered = []
    if _prefs_path_used is not None:
        ordered.append(_prefs_path_used)
    ordered.extend(_prefs_candidates())
    seen = set()
    for p in ordered:
        s = str(p)
        if s in seen:
            continue
        seen.add(s)
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(payload, encoding="utf-8")
            _prefs_path_used = p
            print("Preferencias guardadas en:", p)
            return True
        except Exception as e:
            errors.append(f"{p}: {e}")
    print("Prefs save FAILED:", errors)
    return False


cargar_prefs()

# ---------------------------------------------------------------------------
# 2. MODOS
# ---------------------------------------------------------------------------
class Modo(Enum):
    BIENVENIDA = auto()
    INPUT_PARADA = auto()
    LLEGADAS = auto()
    INPUT_LINEA = auto()
    SELECT_DIRECCION = auto()
    SELECT_PARADA = auto()
    INFO = auto()
    AYUDA = auto()
    GEO_CHOICE = auto()
    GEO_LON = auto()
    GEO_LAT = auto()
    GEO_RADIUS = auto()
    GEO_LISTA = auto()
    CONFIRM_SAVE = auto()


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
REFRESCO_LLEGADAS_S = 15.0
ultimo_fetch_ts = 0.0
refresco_en_curso = False

geo_lon = None
geo_lat = None
geo_radius = None
lista_geo = []
matrices_geo = []
matriz_titulo_geo = None
# Testigo: última posición obtenida por GPS (no confiar solo en prefs)
gps_lon = None
gps_lat = None
gps_ok = False

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
scroll_pausado = False
scroll_vel_mult_v = 1.0
ultimo_toque_nav_ts = 0.0

offset_vertical = 0.0
offset_h = 0.0
offset_f1 = offset_f2 = offset_f3 = offset_f4 = 0.0
velocidad_f1 = velocidad_f2 = velocidad_f3 = velocidad_f4 = 0.0


def pausar_auto():
    global auto_pausado_hasta
    auto_pausado_hasta = time.time() + PAUSA_AUTO_S


def auto_activo() -> bool:
    if scroll_pausado:
        return False
    return time.time() >= auto_pausado_hasta


def velocidad_v_actual() -> float:
    return VEL_V_BASE * NIVELES_V[min(nivel_v, len(NIVELES_V) - 1)] * scroll_vel_mult_v


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


def manejar_toque_navegacion():
    global scroll_pausado, scroll_vel_mult_v, ultimo_toque_nav_ts
    ahora = time.time()
    doble = (ahora - ultimo_toque_nav_ts) <= DOBLE_TOQUE_S
    ultimo_toque_nav_ts = ahora
    if doble:
        scroll_pausado = False
        scroll_vel_mult_v = 2.0
        return "x2"
    if scroll_pausado or scroll_vel_mult_v != 1.0:
        scroll_pausado = False
        scroll_vel_mult_v = 1.0
        return "normal"
    scroll_pausado = True
    return "pausa"


async def _maybe_await(val):
    if asyncio.iscoroutine(val):
        return await val
    return val


# ---------------------------------------------------------------------------
# 3. FUENTE / TEXTO
# ---------------------------------------------------------------------------
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
                col.append(superficie.get_at((x, y))[0] > 128 if y < alto else False)
            matriz.append(col)
        return matriz
    ancho_tmp = max(len(texto) * ANCHO_FUENTE + 8, COLUMNAS_LED)
    img = Image.new("L", (ancho_tmp, FILAS_POR_BLOQUE), 0)
    draw = ImageDraw.Draw(img)
    draw.text((0, 0), texto, fill=255, font=_fuente_pil)
    bbox = img.getbbox()
    if bbox:
        img = img.crop((bbox[0], 0, max(bbox[2], bbox[0] + 1), FILAS_POR_BLOQUE))
    ancho, alto = img.size
    matriz = []
    for x in range(ancho):
        col = []
        for y in range(FILAS_POR_BLOQUE):
            col.append(img.getpixel((x, y)) > 128 if y < alto else False)
        matriz.append(col)
    return matriz or [[False] * FILAS_POR_BLOQUE]


def matriz_con_ciclo(texto: str) -> list:
    t = (texto or " ").rstrip()
    mat = generar_matriz_texto(t)
    if len(mat) > COLUMNAS_LED:
        mat_p = generar_matriz_texto(t + ".")
        sep = [[False] * FILAS_POR_BLOQUE for _ in range(ANCHO_FUENTE)]
        mat = mat_p + sep + sep
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


def leer_texto_asset(nombre: str, fallback: str) -> str:
    for p in (BASE_DIR / "assets" / nombre, BASE_DIR / nombre):
        try:
            if p.is_file():
                return p.read_text(encoding="utf-8").strip()
        except Exception as e:
            print(f"No se pudo leer {p}: {e}")
    return fallback


def leer_info_mvm() -> str:
    return leer_texto_asset(
        "info_mvm.txt",
        "MvM (v1.3.2). Marquesina virtual Madrid. Por David de Haro. API EMT-Madrid.",
    )


def leer_ayuda_mvm() -> str:
    return leer_texto_asset(
        "ayuda_mvm.txt",
        "MvM v1.3.2. 1-Paradas. 2-Lineas. 3-Ubicacion. 4-Info. 5-Ayuda. 0-Salir. "
        "Toque: pausa scroll; doble: x2 vertical. Preferencias al salir de consulta.",
    )


MENU_TITULO = "Marquesina Virtual MvM"
# Textos cortos para LED (sin acentos si la fuente no los tiene; sí en docs)
MENU_LINEAS = [
    "1-Paradas  2-Lineas",
    "3-Ubicacion  4-Info",
    "5-Ayuda  0-Salida",
]
matriz_titulo = generar_matriz_texto(MENU_TITULO)
matrices_opciones = [generar_matriz_texto(op) for op in MENU_LINEAS]

matriz_f1 = generar_matriz_texto(" ")
matriz_f2 = generar_matriz_texto(" ")
matriz_f3 = generar_matriz_texto(" ")
matriz_f4 = generar_matriz_texto(" ")
matriz_titulo_parada = generar_matriz_texto(" ")
matriz_titulo_geo = generar_matriz_texto(" ")
matrices_geo = []


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

    elif modo_actual in (Modo.SELECT_PARADA, Modo.GEO_LISTA):
        mats = matrices_paradas if modo_actual == Modo.SELECT_PARADA else matrices_geo
        titulo_m = (
            matriz_titulo_parada
            if modo_actual == Modo.SELECT_PARADA
            else matriz_titulo_geo
        )
        n = max(len(mats), 1)
        for x_led in range(COLUMNAS_LED):
            for y_led in range(FILAS_LED_TOTAL):
                if y_led < MARGEN_SUPERIOR:
                    on = False
                else:
                    ya = y_led - MARGEN_SUPERIOR
                    bloque = ya // FILAS_POR_BLOQUE
                    yr = ya % FILAS_POR_BLOQUE
                    if bloque == 0:
                        on = pixel_de_matriz(titulo_m, x_led, yr, offset_h)
                    else:
                        idx = (bloque - 1 + int(offset_vertical)) % n
                        on = pixel_de_matriz(mats[idx], x_led, yr, offset_h)
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
                            label, size=fs, text_align=ft.TextAlign.CENTER,
                            no_wrap=True, color=ft.Colors.WHITE,
                        ),
                        width=btn_size, height=btn_size,
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
    os._exit(0)


def _parse_float(s: str):
    s = (s or "").strip().replace(",", ".")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


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
    global geo_lon, geo_lat, geo_radius, lista_geo, matrices_geo, matriz_titulo_geo
    global scroll_pausado, scroll_vel_mult_v
    global gps_lon, gps_lat, gps_ok

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
            page.window.height = 560
    except Exception:
        pass

    print(f"HAS_GEO_PKG={HAS_GEO_PKG} err={_geo_import_err} android={es_android}")
    print("Prefs env:", {k: os.environ.get(k) for k in (
        "FLET_APP_STORAGE_DATA", "FLET_APP_STORAGE", "HOME"
    )})

    # -----------------------------------------------------------------------
    # Geolocator → page.services (Service, no control visual / no overlay)
    # -----------------------------------------------------------------------
    gl = None
    geo_usable = False
    if HAS_GEO_PKG and Geolocator is not None:
        try:
            kwargs = {}
            if GeolocatorConfiguration is not None and GeolocatorPositionAccuracy is not None:
                acc = (
                    getattr(GeolocatorPositionAccuracy, "HIGH", None)
                    or getattr(GeolocatorPositionAccuracy, "BEST", None)
                    or getattr(GeolocatorPositionAccuracy, "MEDIUM", None)
                    or getattr(GeolocatorPositionAccuracy, "LOW", None)
                )
                if acc is not None:
                    try:
                        kwargs["configuration"] = GeolocatorConfiguration(accuracy=acc)
                    except Exception as ce:
                        print("GeolocatorConfiguration:", ce)
            gl_candidate = Geolocator(
                on_error=lambda e: print("Geo error:", getattr(e, "data", e)),
                **kwargs,
            )
            # API 0.86+: Service → page.services (overlay provoca Unknown control)
            if hasattr(page, "services"):
                page.services.append(gl_candidate)
            else:
                page.overlay.append(gl_candidate)  # fallback muy antiguo
            gl = gl_candidate
            geo_usable = True
            print("Geolocator registrado en page.services")
        except Exception as e:
            print("Geolocator init FAIL:", e)
            gl = None
            geo_usable = False

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
    status_text = ft.Text("", size=11, color=ft.Colors.GREY_400, visible=not es_android)

    btn_volver_dir = ft.Button(
        content=ft.Text("Volver", size=12, no_wrap=True, color=ft.Colors.WHITE),
        height=48, width=72, visible=False,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.BLUE_GREY_700,
            shape=ft.RoundedRectangleBorder(radius=6), padding=4,
        ),
    )
    btn_izq = ft.Button(
        content=ft.Text("Volver", size=13, no_wrap=True, color=ft.Colors.WHITE),
        expand=True, height=48,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.BLUE_GREY_800,
            shape=ft.RoundedRectangleBorder(radius=6), padding=4,
        ),
    )
    btn_der = ft.Button(
        content=ft.Text("OK", size=13, no_wrap=True, color=ft.Colors.WHITE),
        expand=True, height=48,
        style=ft.ButtonStyle(
            bgcolor=COLOR_EMT,
            shape=ft.RoundedRectangleBorder(radius=6), padding=4,
        ),
    )
    gap_box = ft.Container(height=GAP_MIN_PX)
    touch_stack = ft.Stack([led_image], width=ANCHO_IMG, height=ALTO_IMG)
    barra_botones = ft.Row(
        [btn_volver_dir, btn_izq, btn_der],
        spacing=6, alignment=ft.MainAxisAlignment.CENTER,
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
        if modo_actual in (
            Modo.INPUT_PARADA, Modo.INPUT_LINEA,
            Modo.GEO_LON, Modo.GEO_LAT, Modo.GEO_RADIUS,
        ):
            return True
        if modo_actual == Modo.SELECT_PARADA and modo_teclado == ModoTeclado.NUM:
            return True
        return False

    def sync_input_visibility():
        need = necesita_entrada()
        input_field.visible = need
        if need:
            input_field.width = min(float(page.width or 400) - 24, 420)
        try:
            input_field.update()
        except Exception:
            pass

    def actualizar_captions():
        en_dir = modo_actual == Modo.SELECT_DIRECCION
        # Tres botones en GEO_CHOICE: Volver visible
        btn_volver_dir.visible = es_android and modo_actual in (
            Modo.SELECT_DIRECCION, Modo.GEO_CHOICE,
        )
        try:
            btn_volver_dir.update()
        except Exception:
            pass

        if not es_android:
            sync_input_visibility()
            return

        if modo_actual == Modo.BIENVENIDA:
            set_captions("Salir", "Pulsa 0-5")
        elif modo_actual == Modo.CONFIRM_SAVE:
            set_captions("No, solo volver", "Guardar")
        elif modo_actual == Modo.GEO_CHOICE:
            set_captions("Manual", "Usar estas")
        elif modo_actual in (
            Modo.INPUT_PARADA, Modo.INPUT_LINEA,
            Modo.GEO_LON, Modo.GEO_LAT, Modo.GEO_RADIUS,
        ):
            if input_field.value:
                labels = {
                    Modo.INPUT_PARADA: ("Borrar", "Buscar parada"),
                    Modo.INPUT_LINEA: ("Borrar", "Buscar línea"),
                    Modo.GEO_LON: ("Borrar", "Confirmar lon"),
                    Modo.GEO_LAT: ("Borrar", "Confirmar lat"),
                    Modo.GEO_RADIUS: ("Borrar", "Buscar cerca"),
                }
                set_captions(*labels[modo_actual])
            else:
                set_captions("Volver", "Toca el campo")
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
                set_captions("Volver", "Toca el campo")
        elif modo_actual == Modo.LLEGADAS:
            set_captions("Volver", "Actualizar")
        elif modo_actual in (Modo.INFO, Modo.AYUDA):
            set_captions("Volver", "Menú")
        elif modo_actual == Modo.GEO_LISTA:
            set_captions("Volver", "Actualizar")
        sync_input_visibility()

    async def abrir_teclado_async():
        input_field.visible = True
        input_field.width = min(float(page.width or 320) - 24, 420)
        try:
            input_field.update()
            page.update()
        except Exception:
            pass
        await asyncio.sleep(0.12)
        try:
            input_field.focus()
            page.update()
        except Exception as ex:
            print("focus:", ex)

    def abrir_teclado():
        page.run_task(abrir_teclado_async)

    def ocultar_teclado_campo():
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
        global scroll_pausado, scroll_vel_mult_v
        matriz_f1 = matriz_con_ciclo(t1)
        matriz_f2 = matriz_con_ciclo(t2)
        matriz_f3 = matriz_con_ciclo(t3)
        matriz_f4 = matriz_con_ciclo(t4)
        offset_f1 = offset_f2 = offset_f3 = offset_f4 = 0.0
        scroll_pausado = False
        scroll_vel_mult_v = 1.0
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
            left=left, top=top,
            width=max(width, 6), height=max(height, 6),
            bgcolor="#01FFFFFF",
            on_click=click,
        )

    def on_nav_tap(e=None):
        r = manejar_toque_navegacion()
        if not es_android:
            try:
                status_text.value = f"Scroll: {r}"
                status_text.update()
            except Exception:
                pass

    def led_row_y(row_index: float) -> float:
        return (row_index / FILAS_LED_TOTAL) * disp_h[0]

    def reconstruir_capas_tactiles():
        w, h = max(disp_w[0], 1), max(disp_h[0], 1)
        capas = [led_image]

        if modo_actual == Modo.BIENVENIDA:
            for bi, (k_left, k_right) in enumerate(
                (("1", "2"), ("3", "4"), ("5", "0")), start=1
            ):
                row0 = MARGEN_SUPERIOR + bi * FILAS_POR_BLOQUE + 2
                top = led_row_y(row0)
                height = led_row_y(row0 + 3) - top
                capas.append(
                    zona(lambda e, k=k_left: manejar_tecla(k), 0, top, w * 0.5, height)
                )
                capas.append(
                    zona(
                        lambda e, k=k_right: manejar_tecla(k),
                        w * 0.5, top, w * 0.5, height,
                    )
                )
        else:
            mx, my = MARGEN_TACTIL * w, MARGEN_TACTIL * h
            my_b = MARGEN_TACTIL * 0.85 * h
            if modo_actual == Modo.SELECT_DIRECCION:
                capas += [
                    zona(lambda e: navegar_horizontal("left"), 0, 0, mx, h),
                    zona(lambda e: navegar_horizontal("right"), w - mx, 0, mx, h),
                    zona(on_nav_tap, mx, my, w - 2 * mx, h - my - my_b),
                ]
            elif (
                (modo_actual == Modo.SELECT_PARADA and modo_teclado == ModoTeclado.NAV)
                or modo_actual == Modo.GEO_LISTA
            ):
                capas += [
                    zona(lambda e: navegar_vertical("up"), mx, 0, w - 2 * mx, my),
                    zona(lambda e: navegar_vertical("down"), mx, h - my_b, w - 2 * mx, my_b),
                    zona(lambda e: navegar_horizontal("left"), 0, my, mx, h - my - my_b),
                    zona(lambda e: navegar_horizontal("right"), w - mx, my, mx, h - my - my_b),
                    zona(on_nav_tap, mx, my, w - 2 * mx, h - my - my_b),
                ]
            elif modo_actual in (
                Modo.INPUT_PARADA, Modo.INPUT_LINEA,
                Modo.GEO_LON, Modo.GEO_LAT, Modo.GEO_RADIUS,
            ):
                capas += [
                    zona(lambda e: abrir_teclado(), mx, my, w - 2 * mx, h - my - my_b)
                ]
            elif modo_actual == Modo.GEO_CHOICE:
                capas += [
                    zona(lambda e: manejar_tecla("1"), 0, h * 0.30, w * 0.5, h * 0.35),
                    zona(lambda e: manejar_tecla("2"), w * 0.5, h * 0.30, w * 0.5, h * 0.35),
                ]
            elif modo_actual in (Modo.INFO, Modo.AYUDA, Modo.LLEGADAS):
                capas += [
                    zona(lambda e: navegar_horizontal("left"), 0, 0, mx, h),
                    zona(lambda e: navegar_horizontal("right"), w - mx, 0, mx, h),
                    zona(on_nav_tap, mx, 0, w - 2 * mx, h),
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
        set_horizontal_texts(leer_info_mvm(), " ", " ", " ", scroll=True)
        cambiar_modo(Modo.INFO)

    def mostrar_ayuda():
        set_horizontal_texts(leer_ayuda_mvm(), " ", " ", " ", scroll=True)
        cambiar_modo(Modo.AYUDA)

    async def intentar_gps_async():
        """Obtiene coords del dispositivo. Actualiza gps_lon/lat/gps_ok."""
        global gps_lon, gps_lat, gps_ok
        gps_ok = False
        gps_lon = gps_lat = None
        if gl is None or not geo_usable:
            print("GPS: sin control usable")
            return False
        set_horizontal_texts("Obteniendo GPS ", "Espere... ", " ", " ", scroll=False)
        try:
            page.update()
        except Exception:
            pass
        try:
            if hasattr(gl, "is_location_service_enabled"):
                enabled = await _maybe_await(gl.is_location_service_enabled())
                print("GPS service:", enabled)
                if enabled is False:
                    return False

            status = None
            for meth in ("get_permission_status", "get_permission_status_async"):
                if hasattr(gl, meth):
                    try:
                        status = await _maybe_await(getattr(gl, meth)())
                    except Exception as e:
                        print("get_permission:", e)
                        return False
                    break
            print("GPS status:", status)
            st = str(status).lower() if status is not None else ""

            if "denied" in st or status is None or st in ("", "none"):
                if "forever" not in st:
                    for meth in ("request_permission", "request_permission_async"):
                        if hasattr(gl, meth):
                            try:
                                status = await _maybe_await(getattr(gl, meth)())
                            except Exception as e:
                                print("request_permission:", e)
                                return False
                            break
                    st = str(status).lower() if status is not None else ""
            if "denied" in st:
                return False

            pos = None
            for meth in (
                "get_current_position", "get_current_position_async",
                "get_last_known_position", "get_last_known_position_async",
            ):
                if hasattr(gl, meth):
                    try:
                        pos = await _maybe_await(getattr(gl, meth)())
                        if pos is not None:
                            break
                    except Exception as e:
                        print(meth, e)
                        continue
            if pos is None:
                return False
            lon = getattr(pos, "longitude", None)
            lat = getattr(pos, "latitude", None)
            if lon is None and isinstance(pos, dict):
                lon, lat = pos.get("longitude"), pos.get("latitude")
            if lon is None or lat is None:
                return False
            gps_lon, gps_lat = float(lon), float(lat)
            gps_ok = True
            print(f"GPS OK {gps_lon}, {gps_lat}")
            return True
        except Exception as e:
            print("GPS exception:", e)
            return False

    def mostrar_geo_choice():
        """Pantalla testigo: coords obtenidas o mensaje, 1=usar / 2=manual + Volver."""
        global geo_lon, geo_lat
        if gps_ok and gps_lon is not None:
            set_horizontal_texts(
                f"GPS Lon:{gps_lon:.5f} ",
                f"Lat:{gps_lat:.5f} ",
                "1-Usar estas  2-Manual ",
                "Volver=menu ",
                scroll=False,
            )
        elif prefs.get("lon") is not None and prefs.get("lat") is not None:
            set_horizontal_texts(
                f"Pref Lon:{float(prefs['lon']):.5f} ",
                f"Lat:{float(prefs['lat']):.5f} ",
                "1-Usar pref  2-Manual ",
                "Volver=menu ",
                scroll=False,
            )
        else:
            set_horizontal_texts(
                "Sin coords GPS ",
                "1-Reintentar GPS ",
                "2-Entrada manual ",
                "Volver=menu ",
                scroll=False,
            )
        cambiar_modo(Modo.GEO_CHOICE)

    def ir_a_radio_tras_coords():
        r = prefs.get("radius") or 200
        set_horizontal_texts(
            f"Lon: {geo_lon:.5f} ",
            f"Lat: {geo_lat:.5f} ",
            f"Radio m (def {r}) ",
            "Confirme o edite ",
            scroll=False,
        )
        input_field.value = str(int(r))
        cambiar_modo(Modo.GEO_RADIUS)

    def iniciar_geo():
        global geo_lon, geo_lat, geo_radius, lista_geo, gps_ok, gps_lon, gps_lat
        geo_lon = geo_lat = geo_radius = None
        lista_geo = []
        gps_ok = False
        gps_lon = gps_lat = None

        async def _flujo():
            # Siempre intentar GPS primero (testigo en display vía GEO_CHOICE)
            if gl is not None and geo_usable:
                await intentar_gps_async()
            else:
                print("GPS no usable en este build; menú sin GPS")
            mostrar_geo_choice()

        page.run_task(_flujo)

    def lanzar_busqueda_geo():
        global lista_geo, matrices_geo, matriz_titulo_geo, offset_vertical, offset_h
        set_horizontal_texts(
            "Buscando paradas ", f"en {geo_radius} m... ", " ", " ", scroll=False
        )
        try:
            page.update()
        except Exception:
            pass
        paradas = location_query.buscar_paradas_cercanas(
            geo_lon, geo_lat, int(geo_radius),
            con_llegadas=True, max_paradas_llegadas=6,
        )
        lista_geo = paradas
        if not paradas:
            set_horizontal_texts(
                "Sin paradas en el radio ", "Pruebe mas metros ", " ", " ", scroll=False
            )
            cambiar_modo(Modo.GEO_RADIUS)
            return
        matrices_geo = []
        for p in paradas:
            for ln in location_query.formatear_parada_para_display(p):
                matrices_geo.append(matriz_con_ciclo(ln))
            matrices_geo.append(generar_matriz_texto(" "))
        matriz_titulo_geo = matriz_con_ciclo(
            f"Cerca {geo_radius}m · {len(paradas)} paradas "
        )
        offset_vertical = 0.0
        offset_h = 0.0
        cambiar_modo(Modo.GEO_LISTA)

    def tiene_datos_usuario_para_guardar() -> bool:
        return bool(
            ultima_parada
            or linea_actual
            or (geo_lon is not None and geo_lat is not None)
            or lista_paradas
            or lista_geo
        )

    def pedir_guardar_y_menu():
        if not tiene_datos_usuario_para_guardar():
            cambiar_modo(Modo.BIENVENIDA)
            return
        set_horizontal_texts(
            "Guardar preferencias? ",
            "Parada/linea/ubicacion ",
            "Der=Guardar ",
            "Izq=Solo volver ",
            scroll=False,
        )
        cambiar_modo(Modo.CONFIRM_SAVE)

    def aplicar_guardado_desde_contexto():
        global prefs
        if ultima_parada:
            prefs["parada"] = str(ultima_parada)
        if linea_actual:
            prefs["linea"] = str(linea_actual)
        if direccion_actual:
            prefs["sentido"] = int(direccion_actual)
        if geo_lon is not None and geo_lat is not None:
            prefs["lon"] = float(geo_lon)
            prefs["lat"] = float(geo_lat)
        if geo_radius:
            prefs["radius"] = int(geo_radius)
        ok = guardar_prefs()
        print("Guardado OK" if ok else "Guardado FALLÓ")

    def volver_atras():
        if modo_actual == Modo.BIENVENIDA:
            salir_programa(page)
        elif modo_actual == Modo.CONFIRM_SAVE:
            cambiar_modo(Modo.BIENVENIDA)
        elif modo_actual in (Modo.INFO, Modo.AYUDA):
            # Nunca preguntar guardar
            cambiar_modo(Modo.BIENVENIDA)
        elif modo_actual == Modo.GEO_CHOICE:
            cambiar_modo(Modo.BIENVENIDA)
        elif modo_actual in (Modo.INPUT_PARADA, Modo.INPUT_LINEA):
            pedir_guardar_y_menu()
        elif modo_actual == Modo.LLEGADAS:
            if lista_paradas:
                cambiar_modo(Modo.SELECT_PARADA)
            elif lista_geo:
                cambiar_modo(Modo.GEO_LISTA)
            else:
                pedir_guardar_y_menu()
        elif modo_actual == Modo.SELECT_PARADA:
            cambiar_modo(Modo.SELECT_DIRECCION)
        elif modo_actual == Modo.SELECT_DIRECCION:
            cambiar_modo(Modo.INPUT_LINEA)
        elif modo_actual == Modo.GEO_LISTA:
            cambiar_modo(Modo.GEO_RADIUS)
        elif modo_actual == Modo.GEO_RADIUS:
            mostrar_geo_choice()
        elif modo_actual == Modo.GEO_LAT:
            cambiar_modo(Modo.GEO_LON)
        elif modo_actual == Modo.GEO_LON:
            mostrar_geo_choice()
        else:
            cambiar_modo(Modo.BIENVENIDA)

    def cambiar_modo(nuevo: Modo):
        global modo_actual, modo_teclado, offset_h, nivel_v, nivel_h
        global scroll_pausado, scroll_vel_mult_v
        modo_actual = nuevo
        offset_h = 0.0
        scroll_pausado = False
        scroll_vel_mult_v = 1.0

        if nuevo == Modo.BIENVENIDA:
            modo_teclado = ModoTeclado.NUM
            nivel_v = nivel_h = 0
            input_field.value = ""
            ocultar_teclado_campo()
        elif nuevo == Modo.INPUT_PARADA:
            modo_teclado = ModoTeclado.NUM
            pref = (prefs.get("parada") or "").strip()
            set_horizontal_texts(
                "Introduzca parada ",
                f"(pref: {pref}) " if pref else "y confirme ",
                scroll=False,
            )
            input_field.value = pref
            abrir_teclado()
        elif nuevo == Modo.INPUT_LINEA:
            modo_teclado = ModoTeclado.NUM
            pref = (prefs.get("linea") or "").strip()
            set_horizontal_texts(
                "Introduzca linea ",
                f"(pref: {pref}) " if pref else "ej. SE1 ",
                scroll=False,
            )
            input_field.value = pref
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
        elif nuevo in (Modo.INFO, Modo.AYUDA, Modo.GEO_CHOICE, Modo.CONFIRM_SAVE):
            modo_teclado = ModoTeclado.NUM
            ocultar_teclado_campo()
        elif nuevo in (Modo.GEO_LON, Modo.GEO_LAT, Modo.GEO_RADIUS):
            modo_teclado = ModoTeclado.NUM
            abrir_teclado()
        elif nuevo == Modo.GEO_LISTA:
            modo_teclado = ModoTeclado.NAV
            nivel_v = nivel_h = 0
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
        global geo_lon, geo_lat, geo_radius

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
                iniciar_geo()
                return
            if key == "4":
                mostrar_info()
                return
            if key == "5":
                mostrar_ayuda()
                return
            return

        if modo_actual == Modo.CONFIRM_SAVE:
            if key in ("↵", "1"):
                aplicar_guardado_desde_contexto()
                set_horizontal_texts("Preferencias guardadas ", " ", " ", " ", scroll=False)
                cambiar_modo(Modo.BIENVENIDA)
            else:
                cambiar_modo(Modo.BIENVENIDA)
            return

        if modo_actual == Modo.GEO_CHOICE:
            if key == "⌫":
                cambiar_modo(Modo.BIENVENIDA)
                return
            if key in ("↵", "1"):
                # Usar GPS o preferidas, o reintentar
                if gps_ok and gps_lon is not None:
                    geo_lon, geo_lat = gps_lon, gps_lat
                    ir_a_radio_tras_coords()
                    return
                if prefs.get("lon") is not None and prefs.get("lat") is not None:
                    geo_lon = float(prefs["lon"])
                    geo_lat = float(prefs["lat"])
                    ir_a_radio_tras_coords()
                    return

                async def _retry():
                    ok = await intentar_gps_async()
                    mostrar_geo_choice()
                    if ok:
                        # actualizar textos ya hechos en mostrar
                        pass
                page.run_task(_retry)
                return
            if key == "2":
                if prefs.get("lon") is not None:
                    input_field.value = str(prefs["lon"])
                else:
                    input_field.value = ""
                set_horizontal_texts(
                    "Longitud (manual) ", "(Madrid ~ -3.7) ", " ", " ", scroll=False
                )
                cambiar_modo(Modo.GEO_LON)
                return
            return

        if modo_actual in (Modo.INFO, Modo.AYUDA):
            if key in ("⌫", "↵", "0"):
                cambiar_modo(Modo.BIENVENIDA)
            elif key in ("4", "6"):
                navegar_horizontal("left" if key == "4" else "right")
            elif key == "8":
                on_nav_tap()
            return

        if modo_actual == Modo.GEO_LON:
            if key == "⌫":
                if input_field.value:
                    input_field.value = input_field.value[:-1]
                    input_field.update()
                    actualizar_captions()
                else:
                    volver_atras()
                return
            if key == "↵":
                v = _parse_float(input_field.value)
                if v is None or not (-10 < v < 5):
                    set_horizontal_texts(
                        "Longitud no valida ", "Ej. -3.756 ", " ", " ", scroll=False
                    )
                    return
                geo_lon = v
                input_field.value = (
                    str(prefs["lat"]) if prefs.get("lat") is not None else ""
                )
                set_horizontal_texts(
                    f"Lon: {geo_lon:.5f} ",
                    "Introduzca latitud ",
                    "(Madrid ~ 40.40) ",
                    " ",
                    scroll=False,
                )
                cambiar_modo(Modo.GEO_LAT)
                return
            if len(key) == 1 and (key.isdigit() or key in ".-"):
                input_field.value = (input_field.value or "") + key
                input_field.update()
                actualizar_captions()
            return

        if modo_actual == Modo.GEO_LAT:
            if key == "⌫":
                if input_field.value:
                    input_field.value = input_field.value[:-1]
                    input_field.update()
                    actualizar_captions()
                else:
                    volver_atras()
                return
            if key == "↵":
                v = _parse_float(input_field.value)
                if v is None or not (35 < v < 45):
                    set_horizontal_texts(
                        "Latitud no valida ", "Ej. 40.398 ", " ", " ", scroll=False
                    )
                    return
                geo_lat = v
                ir_a_radio_tras_coords()
                return
            if len(key) == 1 and (key.isdigit() or key in ".-"):
                input_field.value = (input_field.value or "") + key
                input_field.update()
                actualizar_captions()
            return

        if modo_actual == Modo.GEO_RADIUS:
            if key == "⌫":
                if input_field.value:
                    input_field.value = input_field.value[:-1]
                    input_field.update()
                    actualizar_captions()
                else:
                    volver_atras()
                return
            if key == "↵":
                v = _parse_float(input_field.value)
                if v is None or v < 20 or v > 5000:
                    set_horizontal_texts(
                        "Radio no valido ", "Entre 20 y 5000 m ", " ", " ", scroll=False
                    )
                    return
                geo_radius = int(v)
                lanzar_busqueda_geo()
                return
            if len(key) == 1 and key.isdigit():
                input_field.value = (input_field.value or "") + key
                input_field.update()
                actualizar_captions()
            return

        if modo_actual == Modo.GEO_LISTA:
            if key == "⌫":
                volver_atras()
                return
            if key == "↵":
                lanzar_busqueda_geo()
                return
            if key in ("2", "8", "4", "6"):
                {
                    "2": lambda: navegar_vertical("up"),
                    "8": lambda: navegar_vertical("down"),
                    "4": lambda: navegar_horizontal("left"),
                    "6": lambda: navegar_horizontal("right"),
                }[key]()
            return

        if modo_actual == Modo.SELECT_PARADA:
            if key == "⌫":
                if input_field.value:
                    input_field.value = input_field.value[:-1]
                    input_field.update()
                    actualizar_captions()
                else:
                    volver_atras()
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
                    volver_atras()
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
                    volver_atras()
                return
            if key == "↵":
                linea = (input_field.value or "").strip()
                if not linea:
                    abrir_teclado()
                    return
                cabeceras = list_query.obtener_cabeceras_linea(linea)
                if not cabeceras:
                    set_horizontal_texts("Linea no encontrada ", " ", scroll=False)
                    return
                linea_actual = cabeceras.get("label") or linea
                cabeceras_actual = cabeceras
                sentido_pref = prefs.get("sentido") or 0
                set_horizontal_texts(
                    f"Linea {linea_actual} ",
                    f"1: {cabeceras['nameA']} -> {cabeceras['nameB']} ",
                    f"2: {cabeceras['nameB']} -> {cabeceras['nameA']} ",
                    f"Elija sentido "
                    + (f"(pref {sentido_pref}) " if sentido_pref else ""),
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
                volver_atras()
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
                    matrices_paradas.append(matriz_con_ciclo(f"-Parada: {p['stop']}:"))
                    matrices_paradas.append(matriz_con_ciclo(f" {p['name']}"))
                if direccion_actual == 1:
                    sentido = f"{cabeceras_actual['nameA']}->{cabeceras_actual['nameB']}"
                else:
                    sentido = f"{cabeceras_actual['nameB']}->{cabeceras_actual['nameA']}"
                matriz_titulo_parada = matriz_con_ciclo(f"L{linea_actual} {sentido} ")
                offset_vertical = 0.0
                offset_h = 0.0
                cambiar_modo(Modo.SELECT_PARADA)
            return

        if modo_actual == Modo.LLEGADAS:
            if key == "⌫":
                volver_atras()
            elif key == "↵" and ultima_parada:
                textos = stop_query.busca_info(
                    stop=ultima_parada, line=ultima_linea or "all"
                )
                if textos:
                    registrar_llegadas(ultima_parada, ultima_linea or "all", textos)
            elif key == "8":
                on_nav_tap()
            return

    def on_btn_izq(e):
        if modo_actual == Modo.SELECT_DIRECCION:
            manejar_tecla("1")
        elif modo_actual == Modo.BIENVENIDA:
            manejar_tecla("0")
        elif modo_actual == Modo.CONFIRM_SAVE:
            manejar_tecla("⌫")
        elif modo_actual == Modo.GEO_CHOICE:
            manejar_tecla("2")
        else:
            manejar_tecla("⌫")

    def on_btn_der(e):
        if modo_actual == Modo.SELECT_DIRECCION:
            manejar_tecla("2")
            return
        if modo_actual == Modo.CONFIRM_SAVE:
            manejar_tecla("↵")
            return
        if modo_actual == Modo.GEO_CHOICE:
            manejar_tecla("1")
            return
        if modo_actual in (
            Modo.INPUT_PARADA, Modo.INPUT_LINEA,
            Modo.GEO_LON, Modo.GEO_LAT, Modo.GEO_RADIUS,
        ):
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
        if modo_actual == Modo.GEO_LISTA:
            manejar_tecla("↵")
            return
        if modo_actual in (Modo.INFO, Modo.AYUDA):
            manejar_tecla("⌫")
            return
        manejar_tecla("↵")

    btn_izq.on_click = on_btn_izq
    btn_der.on_click = on_btn_der
    btn_volver_dir.on_click = lambda e: manejar_tecla("⌫")
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
        page.add(
            ft.Column(
                [input_field, display_container, gap_box, barra_botones],
                spacing=4, expand=True,
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )
    else:
        keypad = NumericKeypad(on_key=manejar_tecla, btn_size=44)
        page.add(
            ft.Row(
                [
                    display_container,
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(
                                    "Control", size=12,
                                    weight=ft.FontWeight.BOLD, color=COLOR_EMT,
                                ),
                                input_field, keypad, status_text,
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
                spacing=8, expand=True,
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
                max_tw - 2 * TECLADO_PADDING - (TECLADO_COLS - 1) * TECLADO_SPACING
            ) / TECLADO_COLS
            btn_hh = (
                H - 80 - 2 * TECLADO_PADDING - (TECLADO_FILAS - 1) * TECLADO_SPACING
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
            reconstruir_capas_tactiles()
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



def _es_spyder() -> bool:
    return any(k.startswith("SPYDER") for k in os.environ)


if __name__ == "__main__":
    if _es_spyder() or os.environ.get("MCPY_WEB") == "1":
        ft.run(main, view=ft.AppView.WEB_BROWSER)
    else:
        ft.run(main)
