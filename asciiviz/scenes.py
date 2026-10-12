"""Contexto de animación y gestor de escenas (efecto actual, transiciones y modo AUTO)."""
from __future__ import annotations
import random
import numpy as np


class Ctx:
    """Estado compartido que reciben los efectos en cada fotograma."""

    def __init__(self):
        self.rows = self.cols = 0
        self.cw = 8
        self.ch = 16
        self.unit = 300.0
        self.t = 0.0          # tiempo de animación (escalado por la velocidad)
        self.dt = 0.016       # delta escalado por la velocidad
        self.rdt = 0.016      # delta real
        self.vol = self.bass = self.mid = self.treb = 0.0
        self.peak = False
        self.peak_strength = 0.0
        self.wire = False
        self.name = "DJ"
        self.geo = None
        self.X = self.Y = self.Rad = None
        self._grid_key = None

    def set_grid(self, rows, cols, cw, ch):
        self.rows, self.cols, self.cw, self.ch = rows, cols, cw, ch
        self.unit = min(rows * ch * 0.46, cols * cw * 0.40)
        key = (rows, cols, cw, ch)
        if key != self._grid_key:
            self._grid_key = key
            half_h = rows * ch / 2.0
            xs = (np.arange(cols, dtype=np.float32) - cols / 2 + 0.5) * cw / half_h
            ys = -(np.arange(rows, dtype=np.float32) - rows / 2 + 0.5) * ch / half_h
            self.X, self.Y = np.meshgrid(xs, ys)
            self.Rad = np.hypot(self.X, self.Y).astype(np.float32)


class SceneManager:
    TRANS_TIME = 1.5

    def __init__(self, effect_classes):
        self.effects = [c() for c in effect_classes]
        self.names = [e.name for e in self.effects]
        self.cur = 0
        self.nxt = None
        self.prog = 0.0
        self.auto = False
        self.auto_secs = 18.0
        self.elapsed = 0.0
        self.history = [0]
        self.field = None
        self.lum = None
        self.hue = None
        self.ovr = None
        self.rng = np.random.default_rng(9)

    # --- control
    def request(self, idx: int, instant=False):
        idx = idx % len(self.effects)
        if self.nxt is not None:
            self.cur, self.nxt, self.prog = self.nxt, None, 0.0
        if idx == self.cur:
            return
        if instant:
            self.cur = idx
        else:
            self.nxt = idx
            self.prog = 0.0
            self.field = None
        self.elapsed = 0.0
        self.history.append(idx)
        self.history = self.history[-8:]

    def pick_auto(self):
        """Elige un efecto distinto de los últimos 3 para evitar repeticiones."""
        recent = set(self.history[-3:]) | {self.cur}
        cands = [i for i in range(len(self.effects)) if i not in recent]
        return random.choice(cands or [i for i in range(len(self.effects)) if i != self.cur])

    @property
    def active_index(self):
        return self.nxt if self.nxt is not None else self.cur

    # --- fotograma
    def update(self, ctx, advance=True):
        if advance and self.auto and self.nxt is None:
            self.elapsed += ctx.rdt
            big_hit = ctx.peak and ctx.peak_strength > 0.85 and self.elapsed > 0.55 * self.auto_secs
            if self.elapsed >= self.auto_secs or big_hit:
                self.request(self.pick_auto())
        eff = self.effects[self.cur]
        eff.ensure(ctx)
        if advance:
            eff.render(ctx)
        if self.nxt is None:
            self.lum, self.hue, self.ovr = eff.cv.lum, eff.cv.hue, eff.cv.ovr
            return
        e2 = self.effects[self.nxt]
        e2.ensure(ctx)
        if advance:
            e2.render(ctx)
            self.prog += ctx.rdt / self.TRANS_TIME
        if self.field is None or self.field.shape != (ctx.rows, ctx.cols):
            noise = self.rng.random((ctx.rows, ctx.cols)).astype(np.float32)
            self.field = np.clip(ctx.Rad / (ctx.Rad.max() + 1e-6), 0, 1) * 0.65 + noise * 0.35
        p = min(1.0, self.prog)
        edge = p * 1.25 - 0.12
        use_b = self.field < edge
        band = np.abs(self.field - edge) < 0.045
        lum = np.where(use_b, e2.cv.lum, eff.cv.lum)
        hue = np.where(use_b, e2.cv.hue, eff.cv.hue)
        lum = np.where(band, np.maximum(lum, 0.95), lum)       # borde luminoso de la transición
        self.ovr = np.where(use_b, e2.cv.ovr, eff.cv.ovr)
        self.lum, self.hue = lum, hue
        if self.prog >= 1.0:
            self.cur, self.nxt, self.prog, self.field = self.nxt, None, 0.0, None
