"""Humo y plasma: ruido Perlin con deformación de dominio, remolinos y turbulencia."""
from __future__ import annotations
import numpy as np
from .base import Effect
from ..mathutil import PERLIN, smoothstep


class SmokePlasma(Effect):
    name = "Humo y plasma"

    def __init__(self):
        super().__init__()
        self.flow = 0.0
        self.swirl = 0.0
        self.flash = 0.0

    def render(self, ctx):
        cv = self.cv
        t = ctx.t
        self.flow += ctx.dt * (0.18 + 0.35 * ctx.mid)
        self.swirl += ctx.dt * (0.25 + 0.9 * ctx.bass)
        if ctx.peak:
            self.flash = max(self.flash, ctx.peak_strength)
        self.flash *= np.exp(-ctx.dt * 3.5)
        X, Y, Rad = ctx.X, ctx.Y, ctx.Rad
        # remolino: rotación dependiente del radio
        a = self.swirl * 0.6 * np.exp(-Rad * 0.9) + 0.4 * np.sin(t * 0.17)
        ca, sa = np.cos(a), np.sin(a)
        u = (X * ca - Y * sa) * 1.35
        v = (X * sa + Y * ca) * 1.35
        f = self.flow
        warp = 1.0 + 1.6 * ctx.bass + 0.8 * self.flash
        qx = PERLIN.fbm(u + f * 0.9, v - f * 0.6, 3)
        qy = PERLIN.fbm(u - f * 0.7 + 5.2, v + f * 0.8 + 1.3, 3)
        w = PERLIN.fbm(u + warp * 1.7 * qx + f * 0.2, v + warp * 1.7 * qy - f * 0.15, 4)
        dens = np.clip(0.52 + 0.95 * w, 0, 1)
        dens = smoothstep(0.30 - 0.1 * ctx.vol, 0.82, dens) ** 1.1
        if ctx.treb > 0.04:                       # chispas de agudos: octava fina
            fine = PERLIN.noise(u * 9 + t * 3, v * 9 - t * 2)
            dens = np.clip(dens + 0.35 * ctx.treb * np.clip(fine - 0.25, 0, 1) * 2.0, 0, 1)
        if self.flash > 0.05:                     # onda expansiva en los picos
            rr = (1.0 - self.flash) * 2.2
            dens = np.clip(dens + 0.5 * self.flash * np.exp(-((Rad - rr) / 0.18) ** 2), 0, 1)
        cv.lum[:] = dens * (0.8 + 0.25 * ctx.vol)
        cv.hue[:] = np.clip(0.5 + 0.6 * qx + 0.35 * w + 0.12 * np.sin(t * 0.2), 0, 1)
