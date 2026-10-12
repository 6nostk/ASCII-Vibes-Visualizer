"""Interfaz oscura y minimalista en modo inmediato (sin dependencias extra, solo pygame)."""
from __future__ import annotations
import pygame

BG = (7, 9, 13)
PANEL = (11, 14, 20)
CONTROL = (15, 20, 27)
CONTROL_HOVER = (22, 30, 38)
POPUP = (10, 14, 19)
LINE = (34, 58, 66)
TEXT = (160, 245, 225)
DIM = (82, 128, 122)
ACCENT = (0, 235, 190)
ACCENT_D = (0, 92, 80)
WARN = (255, 180, 70)
ERR = (255, 95, 95)

THEMES = {
    "Verde": ((0, 235, 190), (0, 92, 80), (160, 245, 225), (82, 128, 122), (34, 58, 66)),
    "Cian": ((0, 190, 255), (0, 70, 105), (175, 230, 250), (80, 135, 155), (34, 62, 78)),
    "Magenta": ((245, 70, 205), (105, 25, 85), (250, 190, 235), (150, 90, 135), (76, 38, 68)),
    "Ámbar": ((255, 180, 55), (110, 67, 10), (255, 225, 165), (155, 120, 75), (76, 59, 37)),
    "Azul": ((95, 125, 255), (42, 50, 115), (190, 200, 255), (115, 125, 175), (50, 55, 94)),
    "Rojo": ((255, 65, 85), (112, 25, 38), (255, 195, 200), (165, 105, 115), (82, 42, 50)),
    "Violeta": ((175, 100, 255), (75, 40, 125), (225, 200, 255), (145, 120, 175), (65, 48, 90)),
    "Rosa": ((255, 105, 185), (120, 40, 82), (255, 210, 235), (175, 120, 150), (88, 48, 70)),
    "Turquesa": ((50, 230, 210), (20, 100, 95), (190, 255, 245), (100, 165, 155), (42, 78, 76)),
    "Naranja": ((255, 125, 45), (125, 55, 20), (255, 215, 175), (175, 125, 90), (88, 56, 38)),
    "Matrix": ((80, 255, 95), (25, 105, 35), (195, 255, 200), (105, 165, 110), (43, 82, 48)),
}
THEME_SURFACES = {
    "Verde": ((11, 14, 20), (15, 20, 27), (22, 30, 38), (10, 14, 19)),
    "Cian": ((8, 14, 21), (12, 22, 31), (17, 37, 49), (8, 15, 22)),
    "Magenta": ((19, 10, 18), (28, 15, 27), (45, 22, 42), (17, 9, 17)),
    "Ámbar": ((20, 15, 8), (30, 22, 12), (48, 35, 17), (18, 13, 7)),
    "Azul": ((10, 12, 23), (16, 19, 34), (26, 31, 55), (9, 10, 20)),
    "Rojo": ((22, 10, 14), (34, 15, 21), (53, 23, 31), (19, 9, 13)),
    "Violeta": ((17, 10, 25), (25, 15, 37), (39, 23, 56), (15, 9, 23)),
    "Rosa": ((23, 10, 18), (36, 15, 28), (55, 23, 43), (20, 9, 16)),
    "Turquesa": ((8, 19, 20), (13, 29, 30), (21, 46, 47), (8, 17, 18)),
    "Naranja": ((23, 14, 8), (36, 21, 12), (55, 32, 17), (20, 12, 7)),
    "Matrix": ((8, 18, 9), (13, 28, 15), (21, 45, 24), (8, 16, 8)),
}

TRANSLATIONS = {
    "ASCII-VIBES-VISUALIZER": "ASCII-VIBES-VISUALIZER",
    "retro-futurista · reactivo al sonido": "retro-futuristic · audio reactive",
    "EFECTO VISUAL": "VISUAL EFFECT",
    "AUTO · alternar efectos": "AUTO · cycle effects",
    "Duración de cada escena (s)": "Scene duration (s)",
    "Cambia el efecto cada 20–100 segundos al azar": "Changes visual randomly every 20–100 seconds",
    "NOMBRE DEL DJ (Enter para terminar)": "DJ NAME (press Enter to finish)",
    "Escribe tu nombre y elige la visual DJ ASCII": "Enter a name and choose the ASCII DJ visual",
    "PALETA DE COLORES": "COLOR PALETTE",
    "COLORES AUTO: ON": "AUTO COLORS: ON",
    "COLORES AUTO: OFF": "AUTO COLORS: OFF",
    "MONOCROMO": "MONOCHROME",
    "ALAMBRE": "WIREFRAME",
    "SOMBREADO": "SHADED",
    "DISPOSITIVO DE AUDIO": "AUDIO DEVICE",
    "ACTUALIZAR DISPOSITIVOS": "REFRESH DEVICES",
    "Intensidad de reacción al sonido": "Audio reaction intensity",
    "Sensibilidad del audio": "Audio sensitivity",
    "Velocidad de animación": "Animation speed",
    "Brillo": "Brightness",
    "Densidad de caracteres": "Character density",
    "NIVELES": "LEVELS",
    "MEDIDORES EN PANTALLA": "ON-SCREEN METERS",
    "PANTALLA COMPLETA": "FULLSCREEN",
    "PAUSA": "PAUSED",
    "REANUDADO": "RESUMED",
    "AUTO: ON": "AUTO: ON",
    "AUTO: OFF": "AUTO: OFF",
    "Monocromo: ON": "Monochrome: ON",
    "Monocromo: OFF": "Monochrome: OFF",
    "Estilo: ALAMBRE": "Style: WIREFRAME",
    "Estilo: SOMBREADO": "Style: SHADED",
    "IDIOMA": "LANGUAGE",
    "TEMA DE INTERFAZ": "INTERFACE THEME",
    "DETENER AUDIO": "STOP AUDIO",
    "INICIAR AUDIO": "START AUDIO",
    "REANUDAR": "RESUME",
    "PAUSAR": "PAUSE",
    "Audio detenido.": "Audio stopped.",
    "Actualizando dispositivos…": "Refreshing devices…",
    "Dispositivo ocupado: otra aplicación lo usa en modo exclusivo.": "Audio device is busy: another app has exclusive access.",
    "Dispositivo desconectado o en error. Reintentando…": "Audio device disconnected or failed. Retrying…",
    "Capturando: señal de demostración sintética.": "Capturing: synthetic demo signal.",
    "El dispositivo no admite la configuración de audio solicitada.": "The device does not support the requested audio settings.",
    "No hay librería de captura: pip install PyAudioWPatch (o soundcard en Python 3.14)": "No audio capture library: pip install PyAudioWPatch (or soundcard on Python 3.14)",
    "AZAR INTENSIDAD: ON": "RANDOM INTENSITY: ON",
    "AZAR INTENSIDAD: OFF": "RANDOM INTENSITY: OFF",
    "AZAR SENSIBILIDAD: ON": "RANDOM SENSITIVITY: ON",
    "AZAR SENSIBILIDAD: OFF": "RANDOM SENSITIVITY: OFF",
    "AZAR VELOCIDAD: ON": "RANDOM SPEED: ON",
    "AZAR VELOCIDAD: OFF": "RANDOM SPEED: OFF",
    "AZAR BRILLO: ON": "RANDOM BRIGHTNESS: ON",
    "AZAR BRILLO: OFF": "RANDOM BRIGHTNESS: OFF",
    "AZAR DENSIDAD: ON": "RANDOM DENSITY: ON",
    "AZAR DENSIDAD: OFF": "RANDOM DENSITY: OFF",
    "IMAGEN RANDOM: ON": "RANDOM VISUAL: ON",
    "IMAGEN RANDOM: OFF": "RANDOM VISUAL: OFF",
    "ALAMBR./SOMBREADO RANDOM: ON": "RANDOM WIREFRAME/SHADED: ON",
    "ALAMBR./SOMBREADO RANDOM: OFF": "RANDOM WIREFRAME/SHADED: OFF",
    "F11 pantalla completa · Esc salir/volver": "F11 fullscreen · Esc exit/return",
    "Espacio pausa · Tab panel · ←/→ efecto": "Space pause · Tab panel · ←/→ effect",
    "A auto · M medidores · W alambre · C mono · P paleta": "A auto · M meters · W wire · C mono · P palette",
    "Verde": "Green",
    "Cian": "Cyan",
    "Magenta": "Magenta",
    "Ámbar": "Amber",
    "Azul": "Blue",
    "Rojo": "Red",
    "Violeta": "Violet",
    "Rosa": "Pink",
    "Turquesa": "Turquoise",
    "Naranja": "Orange",
    "Matrix": "Matrix",
    "Cian y magenta": "Cyan and magenta",
    "Verde terminal": "Terminal green",
    "Ámbar retro": "Retro amber",
    "Arcoíris": "Rainbow",
    "Azul eléctrico y violeta": "Electric blue and violet",
    "Blanco y negro": "Black and white",
    "Automática (reactiva)": "Automatic (reactive)",
    "Rojo neón": "Neon red",
    "Océano profundo": "Deep ocean",
    "Atardecer synthwave": "Synthwave sunset",
    "Verde tóxico": "Toxic green",
    "Hielo polar": "Polar ice",
    "Fuego": "Fire",
    "Partículas y explosiones": "Particles and explosions",
    "Cráneo 3D": "3D Skull",
    "Cerebro 3D": "3D Brain",
    "Rostro 3D": "3D Face",
    "Cubo 3D": "3D Cube",
    "Tetraedro / Estrella": "Tetrahedron / Star",
    "Ondas líquidas": "Liquid waves",
    "Humo y plasma": "Smoke and plasma",
    "Túnel": "Tunnel",
    "Vórtice": "Vortex",
    "Visual DJ ASCII": "ASCII DJ Name",
    "Osciloscopio": "Oscilloscope",
    "Ecualizador circular": "Circular equalizer",
    "Lluvia de meteoros": "Meteor shower",
    "Portal de ondas": "Wave portal",
    "Glitch digital": "Digital glitch",
    "(ninguno)": "(none)",
}


class UI:
    def __init__(self, scale: float):
        self.sc = scale
        names = "consolas,lucidaconsole,couriernew,dejavusansmono,monospace"
        self.font = pygame.font.SysFont(names, self.s(15))
        self.small = pygame.font.SysFont(names, self.s(13))
        self.big = pygame.font.SysFont(names, self.s(19), bold=True)
        self.scroll = 0
        self.content_h = 0
        self.active = None
        self.open_dd = None
        self.dd_scroll = 0
        self._popup = None
        self._just_opened = False
        self._tc: dict = {}
        self.row_n = 1
        self.row_i = 0
        self.row_h = 0
        self.language = "Español"

    def s(self, v):
        return int(round(v * self.sc))

    def set_language(self, language):
        self.language = language if language in ("Español", "English") else "Español"

    def tr(self, txt):
        if self.language == "English":
            translated = TRANSLATIONS.get(txt)
            if translated is not None:
                return translated
            for source, target in (
                ("Capturando: ", "Capturing: "),
                ("Error de audio: ", "Audio error: "),
                ("Conectando con «", "Connecting to “"),
            ):
                if txt.startswith(source):
                    return target + txt[len(source):].replace("»", "”")
            return txt
        return txt

    def set_theme(self, theme):
        global ACCENT, ACCENT_D, TEXT, DIM, LINE, PANEL, CONTROL, CONTROL_HOVER, POPUP
        colors = THEMES.get(theme, THEMES["Verde"])
        ACCENT, ACCENT_D, TEXT, DIM, LINE = colors
        PANEL, CONTROL, CONTROL_HOVER, POPUP = THEME_SURFACES.get(theme, THEME_SURFACES["Verde"])

    # ------------------------------------------------------------ texto
    def text(self, font, txt, color):
        key = (id(font), txt, color)
        surf = self._tc.get(key)
        if surf is None:
            if len(self._tc) > 800:
                self._tc.clear()
            surf = font.render(txt, True, color)
            self._tc[key] = surf
        return surf

    def fit(self, font, txt, maxw):
        if font.size(txt)[0] <= maxw:
            return txt
        while len(txt) > 1 and font.size(txt + "…")[0] > maxw:
            txt = txt[:-1]
        return txt + "…"

    # ------------------------------------------------------------ ciclo
    def begin(self, surf, rect, mouse, down, clicked, released, wheel):
        self.surf, self.rect = surf, rect
        self.mx, self.my = mouse
        self.down, self.clicked, self.released, self.wheel = down, clicked, released, wheel
        self.inside = rect.collidepoint(mouse)
        self.modal = self.open_dd is not None
        self._popup = None
        self._just_opened = False
        maxs = max(0, self.content_h - rect.h)
        if self.inside and wheel and not self.modal:
            self.scroll -= wheel * self.s(42)
        self.scroll = max(0, min(self.scroll, maxs))
        pad = self.s(14)
        self.x = rect.x + pad
        self.w = rect.w - 2 * pad - self.s(6)
        self.y = rect.y + pad - self.scroll
        self.row_n, self.row_i, self.row_h = 1, 0, 0
        pygame.draw.rect(surf, PANEL, rect)
        pygame.draw.line(surf, LINE, (rect.right - 1, rect.y), (rect.right - 1, rect.bottom))
        surf.set_clip(rect)

    def end(self):
        self.content_h = self.y + self.scroll - self.rect.y + self.s(12)
        r = self.rect
        if self.content_h > r.h:        # barra de desplazamiento
            bh = max(self.s(24), int(r.h * r.h / self.content_h))
            by = r.y + int((r.h - bh) * self.scroll / max(1, self.content_h - r.h))
            pygame.draw.rect(self.surf, ACCENT_D, (r.right - self.s(5), by, self.s(3), bh))
        self.surf.set_clip(None)
        self._draw_popup()

    # ------------------------------------------------------------ layout
    def row(self, n):
        self.row_n, self.row_i, self.row_h = n, 0, 0

    def _slot(self, h):
        g = self.s(6)
        if self.row_n > 1:
            wc = (self.w - g * (self.row_n - 1)) / self.row_n
            r = pygame.Rect(int(self.x + self.row_i * (wc + g)), self.y, int(wc), h)
            self.row_i += 1
            self.row_h = max(self.row_h, h)
            if self.row_i >= self.row_n:
                self.y += self.row_h + g
                self.row_n, self.row_i, self.row_h = 1, 0, 0
            return r
        r = pygame.Rect(self.x, self.y, self.w, h)
        self.y += h + g
        return r

    def _hover(self, r, allow=False):
        if self.modal and not allow:
            return False
        return self.inside and r.collidepoint(self.mx, self.my)

    def gap(self, px):
        self.y += self.s(px)

    # ------------------------------------------------------------ widgets
    def title(self, txt, sub=None):
        self.surf.blit(self.text(self.big, self.tr(txt), ACCENT), (self.x, self.y))
        self.y += self.big.get_height() + self.s(2)
        if sub:
            self.label(self.tr(sub), DIM, small=True)

    def label(self, txt, color=TEXT, small=False, wrap=False):
        txt = self.tr(txt)
        f = self.small if small else self.font
        if wrap:
            words, line, lines = txt.split(" "), "", []
            for w in words:
                t = (line + " " + w).strip()
                if f.size(t)[0] <= self.w:
                    line = t
                else:
                    lines.append(line)
                    line = w
            lines.append(line)
        else:
            lines = [self.fit(f, txt, self.w)]
        for ln in lines:
            self.surf.blit(self.text(f, ln, color), (self.x, self.y))
            self.y += f.get_height() + self.s(1)
        self.y += self.s(3)

    def separator(self):
        self.y += self.s(3)
        pygame.draw.line(self.surf, LINE, (self.x, self.y), (self.x + self.w, self.y))
        self.y += self.s(8)

    def button(self, txt, toggled=False, accent=False):
        txt = self.tr(txt)
        r = self._slot(self.s(28))
        hv = self._hover(r)
        fill = ACCENT_D if toggled else CONTROL_HOVER if hv else CONTROL
        pygame.draw.rect(self.surf, fill, r)
        pygame.draw.rect(self.surf, ACCENT if (toggled or accent or hv) else LINE, r, 1)
        t = self.text(self.font, self.fit(self.font, txt, r.w - self.s(8)), ACCENT if toggled else TEXT)
        self.surf.blit(t, (r.centerx - t.get_width() // 2, r.centery - t.get_height() // 2))
        return hv and self.clicked

    def slider(self, uid, label, value, vmin, vmax, fmt="{:.2f}"):
        label = self.tr(label)
        r = self._slot(self.s(38))
        self.surf.blit(self.text(self.small, label, DIM), (r.x, r.y))
        vt = self.text(self.small, fmt.format(value), TEXT)
        self.surf.blit(vt, (r.right - vt.get_width(), r.y))
        track = pygame.Rect(r.x, r.y + self.s(25), r.w, self.s(4))
        hit = pygame.Rect(r.x, r.y + self.s(16), r.w, self.s(22))
        released = False
        if self._hover(hit) and self.clicked:
            self.active = uid
        if self.active == uid:
            frac = min(1.0, max(0.0, (self.mx - track.x) / max(1, track.w)))
            value = vmin + (vmax - vmin) * frac
            if self.released or not self.down:
                self.active = None
                released = True
        frac = (value - vmin) / (vmax - vmin)
        pygame.draw.rect(self.surf, LINE, track)
        pygame.draw.rect(self.surf, ACCENT, (track.x, track.y, int(track.w * frac), track.h))
        kx = track.x + int(track.w * frac)
        pygame.draw.rect(self.surf, TEXT if self.active == uid else ACCENT,
                         (kx - self.s(4), track.y - self.s(5), self.s(8), self.s(14)))
        return value, released

    def dropdown(self, uid, label, items, index, on_select):
        label = self.tr(label)
        items = [self.tr(item) for item in items]
        self.label(label, DIM, small=True)
        r = self._slot(self.s(28))
        opened = self.open_dd == uid
        hv = self._hover(r, allow=opened)
        pygame.draw.rect(self.surf, CONTROL, r)
        pygame.draw.rect(self.surf, ACCENT if (hv or opened) else LINE, r, 1)
        cur = items[index] if 0 <= index < len(items) else "—"
        self.surf.blit(self.text(self.font, self.fit(self.font, cur, r.w - self.s(26)), TEXT),
                       (r.x + self.s(8), r.centery - self.font.get_height() // 2))
        self.surf.blit(self.text(self.font, "▾" if not opened else "▴", ACCENT), (r.right - self.s(18), r.centery - self.font.get_height() // 2))
        if hv and self.clicked:
            if opened:
                self.open_dd = None
            else:
                self.open_dd = uid
                self.dd_scroll = max(0, index - 3)
                self._just_opened = True
                opened = True
        if opened:
            self._popup = (uid, pygame.Rect(r), items, index, on_select)

    def meter(self, label, value, color=None):
        label = self.tr(label)
        color = ACCENT if color is None else color
        r = self._slot(self.font.get_height() + self.s(2))
        cw = self.font.size("M")[0]
        lw = cw * 4
        n = max(6, (r.w - lw) // cw - 6)
        fill = int(max(0.0, min(1.0, value)) * n + 0.5)
        self.surf.blit(self.text(self.font, label, DIM), (r.x, r.y))
        self.surf.blit(self.text(self.font, "#" * fill, color), (r.x + lw, r.y))
        self.surf.blit(self.text(self.font, "." * (n - fill), LINE), (r.x + lw + fill * cw, r.y))
        self.surf.blit(self.text(self.font, f"{int(value * 100):3d}", DIM), (r.x + lw + n * cw + cw, r.y))

    def text_input(self, label, value, focused=False):
        label = self.tr(label)
        self.label(label, DIM, small=True)
        r = self._slot(self.s(30))
        hovered = self._hover(r)
        pygame.draw.rect(self.surf, CONTROL, r)
        pygame.draw.rect(self.surf, ACCENT if focused or (hovered and self.clicked) else LINE, r, 1)
        shown = self.fit(self.font, (value or "DJ") + ("_" if focused else ""), r.w - self.s(16))
        self.surf.blit(self.text(self.font, shown, TEXT), (r.x + self.s(8), r.centery - self.font.get_height() // 2))
        return hovered and self.clicked

    # ------------------------------------------------------------ popup
    def _draw_popup(self):
        if self.open_dd is None:
            return
        if self._popup is None or self._popup[0] != self.open_dd:
            self.open_dd = None          # el desplegable ya no existe en pantalla
            return
        uid, hr, items, index, on_select = self._popup
        ih = self.s(24)
        vis = min(len(items), 9)
        sw, sh = self.surf.get_size()
        pr = pygame.Rect(hr.x, hr.bottom + 1, max(hr.w, self.s(260)) if hr.w < self.s(260) else hr.w, vis * ih + 2)
        pr.w = min(pr.w, sw - pr.x - 4)
        if pr.bottom > sh:
            pr.bottom = hr.y - 1
        over = pr.collidepoint(self.mx, self.my)
        if over and self.wheel:
            self.dd_scroll -= self.wheel
        self.dd_scroll = max(0, min(self.dd_scroll, max(0, len(items) - vis)))
        pygame.draw.rect(self.surf, POPUP, pr)
        pygame.draw.rect(self.surf, ACCENT, pr, 1)
        chosen = None
        for k in range(vis):
            i = self.dd_scroll + k
            ir = pygame.Rect(pr.x + 1, pr.y + 1 + k * ih, pr.w - 2, ih)
            hv = ir.collidepoint(self.mx, self.my)
            if hv or i == index:
                pygame.draw.rect(self.surf, ACCENT_D if i == index else CONTROL_HOVER, ir)
            self.surf.blit(self.text(self.font, self.fit(self.font, items[i], ir.w - self.s(12)), TEXT if hv else DIM if i != index else ACCENT),
                           (ir.x + self.s(6), ir.centery - self.font.get_height() // 2))
            if hv and self.clicked and not self._just_opened:
                chosen = i
        if len(items) > vis:
            self.surf.blit(self.text(self.small, f"{self.dd_scroll + 1}-{self.dd_scroll + vis}/{len(items)}", DIM), (pr.right - self.s(70), pr.bottom - self.s(15)))
        if chosen is not None:
            self.open_dd = None
            on_select(chosen)
        elif self.clicked and not self._just_opened and not over and not hr.collidepoint(self.mx, self.my):
            self.open_dd = None
