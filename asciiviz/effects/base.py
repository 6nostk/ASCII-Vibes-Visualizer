"""Base de los efectos y utilidades 3D comunes (proyección y sombreado)."""
from __future__ import annotations
import numpy as np
from ..canvas import Canvas


class Effect:
    name = "Efecto"

    def __init__(self):
        self.cv: Canvas | None = None

    def ensure(self, ctx):
        if self.cv is None or self.cv.rows != ctx.rows or self.cv.cols != ctx.cols:
            self.cv = Canvas(ctx.rows, ctx.cols)
            self.on_resize(ctx)

    def on_resize(self, ctx):
        pass

    def render(self, ctx):  # pragma: no cover
        raise NotImplementedError


def project(ctx, P, D=4.2):
    """Proyección en perspectiva a coordenadas de cuadrícula (col, row) + profundidad."""
    f = D / (D - P[:, 2])
    col = ctx.cols * 0.5 + P[:, 0] * f * ctx.unit / ctx.cw
    row = ctx.rows * 0.5 - P[:, 1] * f * ctx.unit / ctx.ch
    return col, row, P[:, 2]


def light_dir(phase, tilt=0.55):
    v = np.array([np.cos(phase) * 0.7, tilt, 0.65 + 0.35 * np.sin(phase)], np.float32)
    return v / np.linalg.norm(v)


def shade(Nr, L, ao=None, ao_strength=0.9, head=0.20):
    """Iluminación difusa + especular + borde (rim). Devuelve (luminancia, difusa, rim)."""
    diff = np.clip(Nr @ L, 0.0, 1.0)
    H = L + np.array([0, 0, 1], np.float32)
    H = H / np.linalg.norm(H)
    spec = np.clip(Nr @ H, 0.0, 1.0) ** 24
    rim = (1.0 - np.clip(Nr[:, 2], 0.0, 1.0)) ** 2.5
    lum = 0.14 + 0.58 * diff + 0.45 * spec + 0.30 * rim + head * np.clip(Nr[:, 2], 0.0, 1.0)
    if ao is not None:
        lum = lum * (1.0 - ao_strength + ao_strength * ao ** 1.6)
    return lum, diff, rim


def shade_portrait(Nr, L, ao, ao_strength, key=0.35, base=0.16, front=0.55):
    """Sombreado 'retrato ASCII': brillo por orientación a cámara + luz clave + oclusión en huecos."""
    nzc = np.clip(Nr[:, 2], 0.0, 1.0)
    diff = np.clip(Nr @ L, 0.0, 1.0)
    H = L + np.array([0, 0, 1], np.float32)
    H = H / np.linalg.norm(H)
    spec = np.clip(Nr @ H, 0.0, 1.0) ** 30
    rim = (1.0 - nzc) ** 3
    lum = base + front * nzc ** 0.8 + key * diff + 0.25 * spec + 0.12 * rim
    lum = lum * (1.0 - ao_strength + ao_strength * np.clip(ao, 0, 1) ** 1.3)
    return lum, diff, rim
