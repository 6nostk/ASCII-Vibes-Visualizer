"""Ondas líquidas: superficie con interferencia de varias ondas, vista en perspectiva."""
from __future__ import annotations
import numpy as np
from .base import Effect, project
from ..mathutil import smoothstep


class LiquidWaves(Effect):
    name = "Ondas líquidas"
    NX = 250
    NZ = 150

    def __init__(self):
        super().__init__()
        self.xn = np.linspace(-1.0, 1.0, self.NX, dtype=np.float32)
        s = np.linspace(0, 1, self.NZ, dtype=np.float32) ** 1.8
        self.zs = (-1.7 + 14.0 * s).astype(np.float32)
        self.X, self.Z = np.meshgrid(self.xn, self.zs)
        self.X = (self.X * (self.Z + 2.4 + 0.4) * 1.6).astype(np.float32)   # el ancho crece con la distancia
        self.rings: list[list[float]] = []   # [t0, amplitud]
        self.drift = 0.0
        self.sun_pulse = 0.0

    def height(self, ctx):
        X, Z, t = self.X, self.Z, ctx.t
        self.drift += ctx.dt * (0.5 + 1.2 * ctx.mid)
        d = self.drift
        h = np.zeros_like(X)
        # ondas direccionales cuyos ángulos derivan lentamente -> interferencia continua
        for i, (k, w, a, th) in enumerate(((1.6, 1.3, 0.55, 0.3), (2.7, 1.9, 0.30, 1.9),
                                           (4.1, 2.6, 0.17, 3.6), (6.3, 3.4, 0.09, 5.0))):
            ang = th + 0.11 * np.sin(t * 0.13 + i)
            h += a * np.sin(k * (X * np.cos(ang) + Z * np.sin(ang)) - w * d)
        # fuentes radiales que se desplazan
        for (cx, cz, k, w, a) in ((-1.2, 2.0, 3.0, 2.0, 0.5), (1.4, 3.5, 2.2, 1.6, 0.45)):
            r = np.hypot(X - cx - 0.5 * np.sin(t * 0.2), Z - cz)
            h += a * np.sin(k * r - w * d) / (1.0 + 0.7 * r)
        # anillos de graves: cada pico lanza una onda que se expande
        if ctx.peak:
            self.rings.append([t, 0.5 + 0.9 * ctx.peak_strength])
            self.rings = self.rings[-5:]
        r0 = np.hypot(X, Z - 1.5)
        for t0, amp in self.rings:
            age = t - t0
            if age < 4.0:
                h += amp * np.exp(-((r0 - age * 2.3) / 0.55) ** 2) * np.cos(6.0 * (r0 - age * 2.3)) * np.exp(-age * 0.55)
        h += 0.035 * ctx.treb * np.sin(23 * X + 17 * Z + 9 * t)
        amp_tot = 0.22 + 0.55 * ctx.bass + 0.12 * ctx.vol
        return h * amp_tot

    def render(self, ctx):
        cv = self.cv
        cv.clear()
        h = self.height(ctx)
        hx = np.gradient(h, self.X[0], axis=1) if False else np.gradient(h, axis=1) / (np.gradient(self.X, axis=1) + 1e-6)
        hz = np.gradient(h, axis=0) / (np.gradient(self.Z, axis=0) + 1e-6)
        n = np.stack([-hx, np.ones_like(hx), -hz], -1)
        n /= np.linalg.norm(n, axis=-1, keepdims=True)
        L = np.array([0.35, 0.80, -0.45], np.float32); L /= np.linalg.norm(L)
        V = np.array([0.0, 0.6, -0.8], np.float32); V /= np.linalg.norm(V)
        H = L + V; H /= np.linalg.norm(H)
        diff = np.clip(n @ L, 0, 1)
        spec = np.clip(n @ H, 0, 1) ** 40
        # cámara: altura, inclinación
        cam_y, cam_z, pitch = 1.05, -2.4, 0.34
        sp, cp = np.sin(pitch), np.cos(pitch)
        vy = h - cam_y
        vz = self.Z - cam_z
        zc = -vy * sp + vz * cp
        yc = vy * cp + vz * sp
        F = ctx.unit * 1.25
        zc_safe = np.maximum(zc, 0.25)
        col = ctx.cols * 0.5 + self.X / zc_safe * F / ctx.cw
        row = ctx.rows * 0.62 - yc / zc_safe * F / ctx.ch
        # sol retro al fondo (reacciona a los graves)
        self.draw_sun(ctx, row_h=float(np.median(row[-1])) + 1.0)
        hn = h / (0.22 + 0.55 * ctx.bass + 0.12 * ctx.vol + 1e-3)
        fog = np.exp(-zc * 0.10)
        lum = (0.22 + 0.55 * diff + 0.9 * spec + 0.28 * np.clip(hn - 0.5, 0, 1)) * (0.45 + 0.55 * fog)
        lum = lum * (0.85 + 0.3 * ctx.vol)
        hue = np.clip(0.15 + 0.50 * (0.5 + 0.5 * np.tanh(hn)) + 0.25 * spec + 0.04 * ctx.t * 0, 0, 1)
        ok = zc > 0.3
        cv.plot(col[ok], row[ok], -zc[ok], np.clip(lum[ok], 0, 1), hue[ok])
        cv.fill_holes()

    def draw_sun(self, ctx, row_h):
        cv = self.cv
        rr, cc = np.mgrid[0:cv.rows, 0:cv.cols]
        x = (cc - cv.cols / 2) * ctx.cw
        y = (row_h - rr) * ctx.ch                      # píxeles por encima del horizonte
        R = ctx.unit * (0.42 + 0.06 * ctx.bass)
        r = np.hypot(x, y - R * 0.5)
        disc = (r < R) & (y > 0)
        stripes = np.sin((y / (ctx.ch * 1.4)) * 1.3 - ctx.t * 0.6) > (-0.6 + 1.2 * (1 - np.clip(y / (R * 1.5), 0, 1)))
        lum = np.where(disc & stripes, 0.55 + 0.35 * (1 - r / R), 0.0).astype(np.float32)
        cv.lum[:] = lum
        cv.hue[:] = np.clip(0.80 - 0.25 * (y / (R * 1.4)), 0, 1)
