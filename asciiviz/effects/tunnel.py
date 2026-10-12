"""Túnel 3D y vórtice giratorio con perspectiva."""
from __future__ import annotations
import numpy as np
from .base import Effect
from ..mathutil import PERLIN, smoothstep


class Tunnel(Effect):
    name = "Túnel"

    def __init__(self):
        super().__init__()
        self.z = 0.0
        self.rot = 0.0
        self.flash = 0.0

    def render(self, ctx):
        cv = self.cv
        t = ctx.t
        speed = 0.9 + 2.6 * ctx.bass + 1.2 * ctx.vol
        self.z += ctx.dt * speed
        self.rot += ctx.dt * (0.25 + 0.7 * ctx.mid)
        if ctx.peak:
            self.flash = max(self.flash, ctx.peak_strength)
        self.flash *= np.exp(-ctx.dt * 4.0)
        # el túnel serpentea: el centro se desplaza
        cx = 0.28 * np.sin(t * 0.37) + 0.08 * np.sin(t * 1.3)
        cy = 0.20 * np.cos(t * 0.29)
        x = ctx.X - cx
        y = ctx.Y - cy
        r = np.hypot(x, y) * (1.0 - 0.12 * ctx.bass - 0.1 * self.flash)
        a = np.arctan2(y, x) + self.rot
        depth = 0.55 / (r + 0.04)                      # profundidad en perspectiva
        v = depth + self.z
        u = a / np.pi * 4.0 + 0.35 * np.sin(depth * 0.7 + t * 0.3)
        # paneles con aristas luminosas
        gu = np.abs(((u + 0.5) % 1.0) - 0.5)
        gv = np.abs(((v * 1.4 + 0.5) % 1.0) - 0.5)
        edge = np.exp(-gu * 14) + np.exp(-gv * 12)
        checker = (np.floor(u) + np.floor(v * 1.4)) % 2
        pan = 0.18 + 0.20 * checker + 0.55 * np.clip(edge, 0, 1)
        fog = np.clip(r * 2.2, 0, 1) ** 0.8              # el fondo del túnel se oscurece
        lum = pan * fog + 0.5 * self.flash * np.exp(-r * 3)
        lum += 0.3 * ctx.treb * np.clip(PERLIN.noise(u * 3, v * 2) - 0.2, 0, 1) * fog
        cv.lum[:] = np.clip(lum * (0.85 + 0.3 * ctx.vol), 0, 1)
        cv.hue[:] = (0.05 * v + 0.35 * (a / (2 * np.pi)) % 1.0 + 0.4 * np.clip(edge, 0, 1)) % 1.0


class Vortex(Effect):
    name = "Vórtice"

    def __init__(self):
        super().__init__()
        self.rot = 0.0
        self.inflow = 0.0
        self.flash = 0.0

    def render(self, ctx):
        cv = self.cv
        t = ctx.t
        self.rot += ctx.dt * (0.6 + 1.6 * ctx.mid + 0.8 * ctx.bass)
        self.inflow += ctx.dt * (0.8 + 2.0 * ctx.bass)
        if ctx.peak:
            self.flash = max(self.flash, ctx.peak_strength)
        self.flash *= np.exp(-ctx.dt * 3.0)
        tilt = 1.0 + 0.9 * (0.5 + 0.5 * np.sin(t * 0.15))      # inclinación del disco (perspectiva)
        x = ctx.X
        y = ctx.Y * tilt
        r = np.hypot(x, y) + 1e-3
        a = np.arctan2(y, x)
        depth = 1.0 / (r + 0.12)
        arms = 5
        tw = 2.3 + 1.5 * ctx.bass
        spiral = a * arms + tw * np.log(r + 0.08) * arms * 0.55 - self.rot * arms * 0.4
        arm = 0.5 + 0.5 * np.sin(spiral)
        arm = arm ** (2.4 + 1.2 * (1 - ctx.vol))
        dust = 0.5 + 0.5 * np.sin(depth * 3.2 - self.inflow * 2.0 + a * 2)
        core = np.exp(-r * (3.2 - 1.2 * ctx.bass))
        nz = PERLIN.fbm(np.cos(a) * 1.6 + depth * 0.35 - self.inflow * 0.25, np.sin(a) * 1.6 + t * 0.1, 3)
        body = (0.10 + 1.0 * arm * (0.55 + 0.45 * dust)) * np.clip(1.45 - r * 0.45, 0, 1) * (0.75 + 0.5 * (nz + 0.4))
        lum = body + 0.9 * core + 0.6 * self.flash * np.exp(-((r - (1 - self.flash) * 1.8) / 0.15) ** 2)
        lum += 0.35 * ctx.treb * np.clip(PERLIN.noise(a * 8 + t, r * 9 - t * 2) - 0.2, 0, 1)
        cv.lum[:] = np.clip(lum * (0.85 + 0.3 * ctx.vol), 0, 1)
        cv.hue[:] = np.clip(0.2 + 0.55 * arm + 0.25 * core + 0.1 * (a / np.pi), 0, 1)
