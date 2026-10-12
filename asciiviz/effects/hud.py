"""Decoración 'HUD' alrededor de las figuras 3D: hélices de ADN, anillos orbitales, nodos,
marco, escalera de datos, gráfico de barras y onda de volumen. Todo en caracteres ASCII."""
from __future__ import annotations
import numpy as np
from ..mathutil import PERLIN, rot_matrix


class Aura:
    def __init__(self, seed=4):
        rng = np.random.default_rng(seed)
        self.hist = np.zeros(512, np.float32)          # historial de volumen (onda inferior)
        self.bars = np.zeros(20, np.float32)
        self.nodes = rng.normal(size=(70, 3)).astype(np.float32)
        self.nodes /= np.linalg.norm(self.nodes, axis=1, keepdims=True)
        self.nodes *= rng.uniform(1.15, 1.75, (70, 1)).astype(np.float32)
        self.nph = rng.uniform(0, 6.28, 70).astype(np.float32)
        self.frame = 0
        self.env = 0.0
        self.rng = rng

    def _scr(self, ctx, x, y):
        return ctx.cols * 0.5 + x * ctx.unit / ctx.cw, ctx.rows * 0.5 - y * ctx.unit / ctx.ch

    def draw(self, ctx, cv):
        t = ctx.t
        self.frame += 1
        if ctx.peak:
            self.env = max(self.env, ctx.peak_strength)
        self.env *= float(np.exp(-ctx.rdt * 4.0))
        self.hist[:-1] = self.hist[1:]
        self.hist[-1] = ctx.vol
        hw = ctx.cols * ctx.cw * 0.5 / ctx.unit        # semiancho de la pantalla en unidades
        # ---- hélices de ADN verticales a ambos lados
        yy = np.linspace(-1.05, 1.05, 150, dtype=np.float32)
        for side, x0 in ((-1, -min(hw * 0.82, 1.75)), (1, min(hw * 0.82, 1.75))):
            amp = 0.17 + 0.10 * ctx.bass
            ph = yy * 6.0 + t * 1.3 * side
            for s, hue in ((0.0, 0.25), (np.pi, 0.80)):
                x = x0 + amp * np.sin(ph + s)
                z = amp * np.cos(ph + s)
                col, row = self._scr(ctx, x, yy)
                cv.plot(col, row, z - 4.0, 0.42 + 0.32 * (z / amp), np.full_like(col, hue))
            for k in range(0, len(yy), 6):             # peldaños
                xs = np.linspace(x0 - amp * np.sin(ph[k]), x0 + amp * np.sin(ph[k]), 7, dtype=np.float32)
                col, row = self._scr(ctx, xs, np.full(7, yy[k], np.float32))
                cv.plot(col, row, np.full(7, -4.5, np.float32), np.full(7, 0.38, np.float32), np.full(7, 0.5, np.float32))
        # ---- anillos orbitales (pasan por delante y por detrás de la figura)
        th = np.linspace(0, 2 * np.pi, 260, endpoint=False, dtype=np.float32)
        for k, (tilt, spd, rad) in enumerate(((1.15, 0.45, 1.30), (0.35, -0.32, 1.52))):
            r = rad * (1.0 + 0.10 * ctx.bass + 0.25 * self.env)
            ring = np.stack([r * np.cos(th), np.zeros_like(th), r * np.sin(th)], 1)
            R = rot_matrix(tilt + 0.2 * np.sin(t * 0.3 + k), t * spd, 0.4 * k)
            P = ring @ R.T
            f = 4.2 / (4.2 - P[:, 2])
            col = ctx.cols * 0.5 + P[:, 0] * f * ctx.unit / ctx.cw
            row = ctx.rows * 0.5 - P[:, 1] * f * ctx.unit / ctx.ch
            dash = (np.arange(len(th)) // 3) % 2 == 0
            lum = np.where(dash, 0.78, 0.30) * (0.65 + 0.35 * (P[:, 2] > 0))
            cv.plot(col, row, P[:, 2], lum.astype(np.float32), np.full_like(col, 0.55 + 0.25 * k))
        # ---- nodos flotantes (constelación)
        drift = 0.07 * np.sin(t * 0.8 + self.nph)[:, None]
        Pn = (self.nodes * (1.0 + drift + 0.12 * ctx.bass)) @ rot_matrix(0.2, t * 0.12, 0.0).T
        f = 4.2 / (4.2 - Pn[:, 2])
        col = ctx.cols * 0.5 + Pn[:, 0] * f * ctx.unit / ctx.cw
        row = ctx.rows * 0.5 - Pn[:, 1] * f * ctx.unit / ctx.ch
        tw = 0.5 + 0.5 * np.sin(t * 2.0 + self.nph * 3) * (0.4 + ctx.treb)
        cv.plot(col, row, Pn[:, 2], np.clip(0.45 + 0.55 * tw, 0, 1).astype(np.float32), np.full_like(col, 0.7))
        # ---- marco, textos y gráficos de datos (capa de texto)
        R_, C_ = cv.rows, cv.cols
        L = 0.55
        for rr, cc, h, v in ((1, 1, 1, 1), (1, C_ - 2, 1, -1), (R_ - 2, 1, -1, 1), (R_ - 2, C_ - 2, -1, -1)):
            for i in range(10):
                cv.put_text(rr, cc + v * i, "-", L, 0.85)
            for i in range(1, 5):
                cv.put_text(rr + h * i, cc, "|", L, 0.85)
            cv.put_text(rr, cc, "+", 0.9, 0.85)
        cv.put_text(2, 4, f"AV_SC_AA_V01_{self.frame % 100000:05d}:010", 0.6, 0.35)
        cv.put_text(3, 4, f"{int(abs(PERLIN.noise(t * 0.1, 3.0)) * 999999):06d} {int(t * 100) % 100000:05d}", 0.4, 0.35)
        lab = "SYSTEM DATA RATES"
        cv.put_text(2, C_ - len(lab) - 4, lab, 0.6, 0.35)
        # escalera de barras a la izquierda
        for r in range(6, R_ - 6):
            n = int(1 + 7 * abs(PERLIN.noise(r * 0.37, t * 0.25)) * (0.5 + 0.9 * ctx.vol))
            cv.put_text(r, 3, "=" * n, 0.38, 0.4)
        # barras reactivas arriba a la derecha
        tgt = np.abs(PERLIN.noise(np.arange(20) * 0.7, t * 0.9)) * 0.6 + 0.5 * np.array(
            [ctx.bass] * 7 + [ctx.mid] * 7 + [ctx.treb] * 6, np.float32)
        self.bars += (tgt.astype(np.float32) - self.bars) * 0.35
        for i, b in enumerate(self.bars):
            h = int(np.clip(b, 0, 1.2) * 6)
            for k in range(h):
                cv.put_text(10 - k, C_ - 24 + i, "|", 0.55, 0.3 + 0.4 * k / 6)
        # onda de volumen en la parte inferior
        w = max(10, C_ - 24)
        seg = self.hist[-w:] if w <= len(self.hist) else self.hist
        for i, v in enumerate(seg):
            r = R_ - 4 - int(np.clip(v, 0, 1.2) * 3)
            cv.put_text(r, 12 + i, "-", 0.45, 0.5)
        cv.put_text(R_ - 3, 4, "AA_B3_V5_10104", 0.4, 0.35)
        cv.put_text(R_ - 3, C_ - 22, f"{int(ctx.vol * 100):03d}:{int(ctx.bass * 100):03d}:{int(ctx.treb * 100):03d}", 0.5, 0.35)
