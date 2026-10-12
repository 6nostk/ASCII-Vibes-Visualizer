"""Aplicación principal: ventana, bucle de render, atajos de teclado y panel de controles."""
from __future__ import annotations
import json
import math
import os
import random
import sys
import time

import pygame

from . import ui as UIM
from .audio import AudioEngine, BACKEND_ERROR
from .canvas import AsciiRenderer
from .effects import EFFECT_CLASSES
from .geometry import Geometry
from .palettes import PALETTES
from .scenes import Ctx, SceneManager

APP_SETTINGS_DIR = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")),
    "ASCII-Vibes-Visualizer",
)
SETTINGS_PATH = os.path.join(APP_SETTINGS_DIR, "settings.json")
LEGACY_SETTINGS_PATH = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")),
    "ASCIIAudioVisualizer",
    "settings.json",
)

DEFAULTS = dict(effect=0, auto=True, auto_secs=18.0, palette=0, auto_colors=False, mono=False, wire=False,
                intensity=1.0, speed=1.0, sensitivity=1.0, brightness=1.0, density=1.35,
                random_scenes=False, overlay_meters=False, device_key=None,
                language="Español", theme="Verde", dj_name="DJ")

RANDOM_CONTROLS = {
    "intensity": ("intensidad", 0.0, 2.0),
    "sensitivity": ("sensibilidad", 0.3, 3.0),
    "speed": ("velocidad", 0.2, 3.0),
    "brightness": ("brillo", 0.4, 1.6),
    "density": ("densidad", 0.5, 2.2),
}


def _dpi_aware():
    if sys.platform == "win32":
        try:
            import ctypes
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def _asset_path(filename):
    bundle_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(bundle_dir, filename)


class App:
    def __init__(self, demo=False, fullscreen=False):
        _dpi_aware()
        pygame.init()
        pygame.display.set_caption("ASCII-Vibes-Visualizer")
        pygame.display.set_icon(pygame.image.load(_asset_path("ASCII Vibes Visualizer logo.png")))
        dw, dh = pygame.display.get_desktop_sizes()[0]
        self.scale = max(1.0, round(dh / 1080 * 4) / 4)
        size = (min(int(1280 * min(self.scale, 1.6)), int(dw * 0.92)), min(int(780 * min(self.scale, 1.6)), int(dh * 0.9)))
        self.windowed_size = size
        self.screen = pygame.display.set_mode(size, pygame.RESIZABLE)
        self.fullscreen = False
        self.st = dict(DEFAULTS)
        self._load_settings()
        self.ui = UIM.UI(self.scale)
        self.st["language"] = self.st["language"] if self.st["language"] in ("Español", "English") else "Español"
        self.st["theme"] = self.st["theme"] if self.st["theme"] in UIM.THEMES else "Verde"
        self.st["dj_name"] = self.clean_dj_name(self.st["dj_name"])
        self.ui.set_language(self.st["language"])
        self.ui.set_theme(self.st["theme"])
        self.name_input_focused = False
        self.renderer = AsciiRenderer()
        self.apply_density()
        self.geo = Geometry()
        self.geo.start()
        self.ctx = Ctx()
        self.ctx.geo = self.geo
        self.scene = SceneManager(EFFECT_CLASSES)
        self.scene.request(int(self.st["effect"]) % len(self.scene.effects), instant=True)
        self.scene.auto = bool(self.st["auto"]) and not bool(self.st["random_scenes"])
        self.scene.auto_secs = float(self.st["auto_secs"])
        self.random_originals = {}
        self.random_control_elapsed = {}
        self.random_control_interval = {}
        self.random_wire_original = None
        self.random_wire_elapsed = 0.0
        self.random_wire_interval = random.uniform(1.0, 2.5)
        self.random_scene_elapsed = 0.0
        self.random_scene_interval = random.uniform(20.01, 99.99)
        self.audio = AudioEngine()
        self.audio.set_sensitivity(self.st["sensitivity"])
        self.audio.refresh_devices(wait=True, preferred_key=self.st["device_key"])
        if demo:
            demo_dev = next((d for d in self.audio.devices if d.kind == "demo"), None)
            if demo_dev:
                self.audio.select(demo_dev)
        else:
            self.audio.start()
        self.panel_visible = True
        self.panel_w = self.ui.s(340)
        self.clock = pygame.time.Clock()
        self.running = True
        self.paused = False
        self.last_peak = self.audio.snapshot().peak_count
        self.hue_phase = 0.0
        self.palette_elapsed = 0.0
        self.fps = 60.0
        self.toast_txt, self.toast_until = "", 0.0
        self.peak_flash = 0.0
        self.feats = self.audio.snapshot()
        self.clicked = self.released = False
        self.down = False
        self.wheel = 0
        self.last_move = time.time()
        self.cursor_hidden = False
        self.view = pygame.Rect(0, 0, 10, 10)
        self.grid = (10, 10)
        if fullscreen:
            self.set_fullscreen(True)

    # ------------------------------------------------------------ ajustes
    def _load_settings(self):
        for path in (SETTINGS_PATH, LEGACY_SETTINGS_PATH):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(data, dict):
                for k in DEFAULTS:
                    if k in data:
                        self.st[k] = data[k]
                return

    def _save_settings(self):
        try:
            self.st["effect"] = self.scene.active_index
            self.st["auto"] = self.scene.auto
            self.st["auto_secs"] = self.scene.auto_secs
            sel = self.audio.selected
            self.st["device_key"] = sel.key if sel else None
            os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
            with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
                json.dump(self.st, f, indent=2)
        except Exception:
            pass

    def apply_density(self):
        self.renderer.set_font_size(round(16 * self.scale / max(0.4, float(self.st["density"]))))

    def toast(self, txt):
        self.toast_txt, self.toast_until = txt, time.time() + 1.8

    @staticmethod
    def clean_dj_name(value):
        valid = "".join(ch for ch in str(value).upper() if ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 _-")
        return valid[:16]

    def set_language(self, language):
        self.st["language"] = language if language in ("Español", "English") else "Español"
        self.ui.set_language(self.st["language"])

    def set_theme(self, theme):
        self.st["theme"] = theme if theme in UIM.THEMES else "Verde"
        self.ui.set_theme(self.st["theme"])

    def toggle_random_control(self, key):
        if key in self.random_originals:
            self.st[key] = self.random_originals.pop(key)
            self.random_control_elapsed.pop(key, None)
            self.random_control_interval.pop(key, None)
            self.toast(f"{RANDOM_CONTROLS[key][0].capitalize()}: valor restaurado")
        else:
            label, low, high = RANDOM_CONTROLS[key]
            self.random_originals[key] = self.st[key]
            self.st[key] = random.uniform(low, high)
            self.random_control_elapsed[key] = 0.0
            self.random_control_interval[key] = random.uniform(1.0, 2.5)
            self.toast(f"{label.capitalize()}: valor aleatorio")
        self._apply_control_side_effect(key)

    def _apply_control_side_effect(self, key):
        if key == "density":
            self.apply_density()
        elif key == "sensitivity":
            self.audio.set_sensitivity(self.st[key])

    def update_random_controls(self, rdt):
        if self.paused:
            return
        for key in tuple(self.random_originals):
            self.random_control_elapsed[key] += rdt
            if self.random_control_elapsed[key] < self.random_control_interval[key]:
                continue
            _, low, high = RANDOM_CONTROLS[key]
            self.st[key] = random.uniform(low, high)
            self.random_control_elapsed[key] = 0.0
            self.random_control_interval[key] = random.uniform(1.0, 2.5)
            self._apply_control_side_effect(key)

    def set_random_wire(self, enabled):
        if enabled and self.random_wire_original is None:
            self.random_wire_original = bool(self.st["wire"])
        elif not enabled and self.random_wire_original is not None:
            self.st["wire"] = self.random_wire_original
            self.random_wire_original = None
        self.random_wire_elapsed = 0.0
        self.random_wire_interval = random.uniform(1.0, 2.5)

    def toggle_wire_manually(self):
        if self.random_wire_original is not None:
            self.set_random_wire(False)
        self.st["wire"] = not self.st["wire"]

    def update_random_wire(self, rdt):
        if self.random_wire_original is None or self.paused:
            return
        self.random_wire_elapsed += rdt
        if self.random_wire_elapsed >= self.random_wire_interval:
            self.st["wire"] = not self.st["wire"]
            self.random_wire_elapsed = 0.0
            self.random_wire_interval = random.uniform(1.0, 2.5)

    def set_random_scenes(self, enabled):
        self.st["random_scenes"] = bool(enabled)
        self.random_scene_elapsed = 0.0
        self.random_scene_interval = random.uniform(20.01, 99.99)
        if enabled:
            self.scene.auto = False
            self.scene.elapsed = 0.0

    # ------------------------------------------------------------ ventana
    def set_fullscreen(self, on):
        if on == self.fullscreen:
            return
        if on:
            self.windowed_size = self.screen.get_size()
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            self.panel_visible = False
        else:
            self.screen = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
            self.panel_visible = True
            pygame.mouse.set_visible(True)
            self.cursor_hidden = False
        self.fullscreen = on
        self.renderer.invalidate()
        self.ui._tc.clear()

    # ------------------------------------------------------------ eventos
    def handle_events(self):
        self.clicked = self.released = False
        self.wheel = 0
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.running = False
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                self.clicked = True
                self.down = True
                if self.name_input_focused:
                    self.name_input_focused = False
                    pygame.key.stop_text_input()
            elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                self.released = True
                self.down = False
            elif ev.type == pygame.MOUSEWHEEL:
                self.wheel += ev.y
            elif ev.type == pygame.MOUSEMOTION:
                self.last_move = time.time()
            elif ev.type == pygame.KEYDOWN:
                self.on_key(ev.key)
            elif ev.type == pygame.TEXTINPUT and self.name_input_focused:
                self.st["dj_name"] = self.clean_dj_name(self.st["dj_name"] + ev.text)
        if time.time() - self.last_move < 0.01 and self.cursor_hidden:
            pygame.mouse.set_visible(True)
            self.cursor_hidden = False

    def on_key(self, key):
        if self.name_input_focused:
            if key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE):
                self.name_input_focused = False
                pygame.key.stop_text_input()
            elif key == pygame.K_BACKSPACE:
                self.st["dj_name"] = self.st["dj_name"][:-1]
            return
        sc = self.scene
        if key == pygame.K_F11:
            self.set_fullscreen(not self.fullscreen)
        elif key == pygame.K_ESCAPE:
            if self.fullscreen:
                self.set_fullscreen(False)
            elif not self.panel_visible:
                self.panel_visible = True
        elif key == pygame.K_SPACE:
            self.paused = not self.paused
            self.toast("PAUSA" if self.paused else "REANUDADO")
        elif key == pygame.K_TAB:
            self.panel_visible = not self.panel_visible
        elif key in (pygame.K_RIGHT, pygame.K_LEFT):
            d = 1 if key == pygame.K_RIGHT else -1
            self.set_random_scenes(False)
            sc.auto = False
            sc.request(sc.active_index + d)
            self.toast(sc.names[sc.active_index % len(sc.names)])
        elif key == pygame.K_a:
            self.set_random_scenes(False)
            sc.auto = not sc.auto
            sc.elapsed = 0
            self.toast("AUTO: " + ("ON" if sc.auto else "OFF"))
        elif key == pygame.K_m:
            self.st["overlay_meters"] = not self.st["overlay_meters"]
            self.toast("Medidores: " + ("ON" if self.st["overlay_meters"] else "OFF"))
        elif key == pygame.K_w:
            self.toggle_wire_manually()
            self.toast("Estilo: " + ("ALAMBRE" if self.st["wire"] else "SOMBREADO"))
        elif key == pygame.K_c:
            self.st["mono"] = not self.st["mono"]
            self.toast("Monocromo: " + ("ON" if self.st["mono"] else "OFF"))
        elif key == pygame.K_p:
            self.select_palette(self.st["palette"] + 1)

    # ------------------------------------------------------------ actualización
    def update(self, rdt):
        st, ctx, sc = self.st, self.ctx, self.scene
        self.update_random_controls(rdt)
        self.update_random_wire(rdt)
        self.screen = pygame.display.get_surface()
        W, H = self.screen.get_size()
        px = self.panel_w if self.panel_visible else 0
        self.view = pygame.Rect(px, 0, max(50, W - px), H)
        rows, cols = self.renderer.grid_for(self.view.w, self.view.h)
        self.grid = (rows, cols)
        ctx.set_grid(rows, cols, self.renderer.cw, self.renderer.chh)
        f = self.audio.snapshot()
        self.feats = f
        k = float(st["intensity"])
        new_peak = f.peak_count != self.last_peak
        self.last_peak = f.peak_count
        ctx.rdt = rdt
        ctx.dt = 0.0 if self.paused else rdt * float(st["speed"])
        ctx.t += ctx.dt
        ctx.vol, ctx.bass, ctx.mid, ctx.treb = f.vol * k, f.bass * k, f.mid * k, f.treb * k
        ctx.peak = bool(new_peak and not self.paused and k > 0.05)
        ctx.peak_strength = min(1.0, f.peak_strength * min(1.0, 0.4 + k * 0.6))
        ctx.wire = bool(st["wire"])
        ctx.name = st["dj_name"]
        if ctx.peak:
            self.peak_flash = 1.0
        self.peak_flash *= math.exp(-rdt * 6)
        if st["auto_colors"] and not self.paused:
            self.palette_elapsed += rdt
            if self.palette_elapsed >= 8.0:
                steps = int(self.palette_elapsed / 8.0)
                st["palette"] = (st["palette"] + steps) % len(PALETTES)
                self.palette_elapsed %= 8.0
        if st["random_scenes"] and not self.paused and sc.nxt is None:
            self.random_scene_elapsed += rdt
            if self.random_scene_elapsed >= self.random_scene_interval:
                sc.request(sc.pick_auto())
                self.random_scene_elapsed = 0.0
                self.random_scene_interval = random.uniform(20.01, 99.99)
        pal = PALETTES[st["palette"] % len(PALETTES)]
        if not self.paused:
            if pal.auto:
                self.hue_phase += rdt * (0.015 + 0.20 * f.treb + 0.10 * f.bass)
            else:
                self.hue_phase += rdt * 0.02
        sc.auto_secs = float(sc.auto_secs)
        sc.update(ctx, advance=not self.paused)

    def select_palette(self, index):
        self.st["palette"] = index % len(PALETTES)
        self.palette_elapsed = 0.0
        self.toast(PALETTES[self.st["palette"]].name)

    # ------------------------------------------------------------ dibujo
    def draw(self):
        st = self.st
        scr = self.screen
        scr.fill((0, 0, 0))
        rows, cols = self.grid
        r = self.renderer
        ox = self.view.x + (self.view.w - cols * r.cw) // 2
        oy = (self.view.h - rows * r.chh) // 2
        pal = PALETTES[st["palette"] % len(PALETTES)]
        shift = self.hue_phase + (0.35 * (self.feats.mid - self.feats.bass) if pal.auto else 0.0)
        if self.scene.lum is not None and self.scene.lum.shape == (rows, cols):
            r.draw(scr, ox, oy, self.scene.lum, self.scene.hue, pal, float(st["brightness"]), shift, bool(st["mono"]), self.scene.ovr)
        if self.panel_visible:
            self.draw_panel()
        else:
            if st["overlay_meters"]:
                self.draw_overlay_meters()
            if self.audio.is_error:
                msg = self.ui.fit(self.ui.small, self.audio.status, scr.get_width() - 30)
                scr.blit(self.ui.text(self.ui.small, msg, UIM.ERR), (14, scr.get_height() - self.ui.small.get_height() - 8))
        if time.time() < self.toast_until:
            t = self.ui.text(self.ui.big, self.ui.tr(self.toast_txt), UIM.ACCENT)
            bx = pygame.Rect(0, 0, t.get_width() + 28, t.get_height() + 14)
            bx.midbottom = (self.view.centerx, scr.get_height() - 28)
            pygame.draw.rect(scr, (6, 10, 14), bx)
            pygame.draw.rect(scr, UIM.ACCENT, bx, 1)
            scr.blit(t, (bx.x + 14, bx.y + 7))

    def draw_overlay_meters(self):
        f = self.feats
        ui = self.ui
        y = 10
        for lab, v in (("VOL", f.vol), ("BAJ", f.bass), ("MED", f.mid), ("AGU", f.treb)):
            n = 20
            fill = int(min(1.0, v) * n + 0.5)
            txt = f"{lab} [{'#' * fill}{'.' * (n - fill)}]"
            self.screen.blit(ui.text(ui.small, txt, UIM.ACCENT), (12, y))
            y += ui.small.get_height() + 2

    def draw_panel(self):
        ui, st, sc, au = self.ui, self.st, self.scene, self.audio
        prect = pygame.Rect(0, 0, self.panel_w, self.screen.get_height())
        ui.begin(self.screen, prect, pygame.mouse.get_pos(), self.down, self.clicked, self.released, self.wheel)
        ui.title("ASCII-VIBES-VISUALIZER", "retro-futurista · reactivo al sonido")
        rows, cols = self.grid
        status = (f"{self.clock.get_fps():4.0f} fps · grid {cols}x{rows}" if st["language"] == "English"
                  else f"{self.clock.get_fps():4.0f} fps · rejilla {cols}x{rows}")
        ui.label(status, UIM.DIM, small=True)
        ui.gap(2)
        ui.row(2)
        if ui.button("DETENER AUDIO" if au.running else "INICIAR AUDIO", toggled=au.running):
            au.stop() if au.running else au.start()
        if ui.button("REANUDAR" if self.paused else "PAUSAR", toggled=self.paused):
            self.paused = not self.paused
        ui.separator()
        # --- efecto
        items = ["AUTO · alternar efectos"] + sc.names
        idx = 0 if sc.auto else sc.active_index + 1

        def pick_effect(i):
            self.set_random_scenes(False)
            if i == 0:
                sc.auto = True
                sc.elapsed = 0
            else:
                sc.auto = False
                sc.request(i - 1)
        ui.dropdown("fx", "EFECTO VISUAL", items, idx, pick_effect)
        if ui.text_input("NOMBRE DEL DJ (Enter para terminar)", st["dj_name"], self.name_input_focused):
            self.name_input_focused = True
            pygame.key.start_text_input()
        ui.label("Escribe tu nombre y elige la visual DJ ASCII", UIM.DIM, small=True)
        if sc.auto:
            sc.auto_secs, _ = ui.slider("auto", "Duración de cada escena (s)", sc.auto_secs, 5, 60, "{:.0f}")
        if ui.button("IMAGEN RANDOM: " + ("ON" if st["random_scenes"] else "OFF"),
                     toggled=bool(st["random_scenes"])):
            self.set_random_scenes(not st["random_scenes"])
        ui.label("Cambia el efecto cada 20–100 segundos al azar", UIM.DIM, small=True)
        ui.dropdown("pal", "PALETA DE COLORES", [p.name for p in PALETTES], st["palette"] % len(PALETTES),
                    self.select_palette)
        ui.dropdown("theme", "TEMA DE INTERFAZ", list(UIM.THEMES), list(UIM.THEMES).index(st["theme"]),
                    lambda i: self.set_theme(list(UIM.THEMES)[i]))
        languages = ("Español", "English")
        ui.dropdown("language", "IDIOMA", list(languages), languages.index(st["language"]),
                    lambda i: self.set_language(languages[i]))
        if ui.button("COLORES AUTO: " + ("ON" if st["auto_colors"] else "OFF"),
                     toggled=bool(st["auto_colors"])):
            st["auto_colors"] = not st["auto_colors"]
            self.palette_elapsed = 0.0
        ui.row(2)
        if ui.button("MONOCROMO", toggled=bool(st["mono"])):
            st["mono"] = not st["mono"]
        if ui.button("ALAMBRE" if st["wire"] else "SOMBREADO", toggled=bool(st["wire"])):
            self.toggle_wire_manually()
        if ui.button("ALAMBR./SOMBREADO RANDOM: " +
                     ("ON" if self.random_wire_original is not None else "OFF"),
                     toggled=self.random_wire_original is not None):
            self.set_random_wire(self.random_wire_original is None)
        ui.separator()
        # --- audio
        devs = au.devices
        labels = [d.label for d in devs]
        sel = au.selected
        di = next((i for i, d in enumerate(devs) if sel and d.key == sel.key), 0)
        ui.dropdown("dev", "DISPOSITIVO DE AUDIO", labels or ["(ninguno)"], di,
                    lambda i: au.select(devs[i]) if 0 <= i < len(devs) else None)
        if ui.button("ACTUALIZAR DISPOSITIVOS"):
            au.refresh_devices()
        ui.label(au.status, UIM.ERR if au.is_error else UIM.DIM, small=True, wrap=True)
        if BACKEND_ERROR is not None:
            ui.label(BACKEND_ERROR, UIM.WARN, small=True, wrap=True)
        ui.separator()
        # --- parámetros
        st["intensity"], _ = ui.slider("int", "Intensidad de reacción al sonido", st["intensity"], 0.0, 2.0)
        if ui.button("AZAR INTENSIDAD: " + ("ON" if "intensity" in self.random_originals else "OFF"),
                     toggled="intensity" in self.random_originals):
            self.toggle_random_control("intensity")
        st["sensitivity"], rel = ui.slider("sen", "Sensibilidad del audio", st["sensitivity"], 0.3, 3.0)
        if ui.button("AZAR SENSIBILIDAD: " + ("ON" if "sensitivity" in self.random_originals else "OFF"),
                     toggled="sensitivity" in self.random_originals):
            self.toggle_random_control("sensitivity")
        au.set_sensitivity(st["sensitivity"])
        st["speed"], _ = ui.slider("spd", "Velocidad de animación", st["speed"], 0.2, 3.0)
        if ui.button("AZAR VELOCIDAD: " + ("ON" if "speed" in self.random_originals else "OFF"),
                     toggled="speed" in self.random_originals):
            self.toggle_random_control("speed")
        st["brightness"], _ = ui.slider("bri", "Brillo", st["brightness"], 0.4, 1.6)
        if ui.button("AZAR BRILLO: " + ("ON" if "brightness" in self.random_originals else "OFF"),
                     toggled="brightness" in self.random_originals):
            self.toggle_random_control("brightness")
        st["density"], rel = ui.slider("den", "Densidad de caracteres", st["density"], 0.5, 2.2)
        if ui.button("AZAR DENSIDAD: " + ("ON" if "density" in self.random_originals else "OFF"),
                     toggled="density" in self.random_originals):
            self.toggle_random_control("density")
        if rel:
            self.apply_density()
        ui.separator()
        # --- indicadores
        f = self.feats
        ui.label("NIVELES", UIM.DIM, small=True)
        ui.meter("VOL", f.vol)
        ui.meter("BAJ", f.bass, (255, 90, 150))
        ui.meter("MED", f.mid, (255, 200, 80))
        ui.meter("AGU", f.treb, (120, 200, 255))
        ui.meter("PIC", self.peak_flash, (255, 255, 255))
        ui.row(2)
        if ui.button("MEDIDORES EN PANTALLA", toggled=bool(st["overlay_meters"])):
            st["overlay_meters"] = not st["overlay_meters"]
        if ui.button("PANTALLA COMPLETA"):
            self.set_fullscreen(True)
        ui.separator()
        if st["language"] == "English":
            ui.label("F11 fullscreen · Esc exit/return", UIM.DIM, small=True)
            ui.label("Space pause · Tab panel · ←/→ effect", UIM.DIM, small=True)
            ui.label("A auto · M meters · W wire · C mono · P palette", UIM.DIM, small=True)
        else:
            ui.label("F11 pantalla completa · Esc salir/volver", UIM.DIM, small=True)
            ui.label("Espacio pausa · Tab panel · ←/→ efecto", UIM.DIM, small=True)
            ui.label("A auto · M medidores · W alambre · C mono · P paleta", UIM.DIM, small=True)
        ui.end()

    # ------------------------------------------------------------ bucle
    def run(self):
        try:
            while self.running:
                active = pygame.display.get_active()
                rdt = self.clock.tick(60 if active else 15) / 1000.0
                rdt = min(rdt, 0.1)
                self.handle_events()
                self.update(rdt)
                self.draw()
                if self.fullscreen and not self.cursor_hidden and time.time() - self.last_move > 2.5 and not self.panel_visible:
                    pygame.mouse.set_visible(False)
                    self.cursor_hidden = True
                pygame.display.flip()
        finally:
            self._save_settings()
            self.audio.close()
            pygame.quit()
