"""Partículas ASCII: órbitas, estelas, explosiones sincronizadas con los picos."""
from __future__ import annotations
import numpy as np
from .base import Effect, project
from ..mathutil import rot_matrix


class Particles(Effect):
    name = "Partículas y explosiones"
    N = 5000
    RING = 900

    def __init__(self):
        super().__init__()
        rng = np.random.default_rng(21)
        self.rng = rng
        N = self.N
        self.pos = np.zeros((N, 3), np.float32)
        self.vel = np.zeros((N, 3), np.float32)
        self.life = np.zeros(N, np.float32)
        self.maxlife = np.ones(N, np.float32)
        self.hue = np.zeros(N, np.float32)
        self.kind = np.zeros(N, np.int8)          # 0 flujo, 1 explosión, 2 chispa
        self.rphase = rng.uniform(0, 2 * np.pi, self.RING).astype(np.float32)
        self.rrad = rng.uniform(0.75, 1.05, self.RING).astype(np.float32)
        self.ry = rng.normal(0, 0.12, self.RING).astype(np.float32)
        self.rspd = rng.uniform(0.6, 1.4, self.RING).astype(np.float32)
        self.cam = 0.0
        self.emit_acc = 0.0

    def _spawn(self, m, kind, strength=1.0):
        free = np.flatnonzero(self.life <= 0)[:m]
        k = len(free)
        if k == 0:
            return
        rng = self.rng
        d = rng.normal(size=(k, 3)).astype(np.float32)
        d /= np.linalg.norm(d, axis=1, keepdims=True) + 1e-6
        if kind == 1:
            sp = rng.uniform(1.2, 3.2, k).astype(np.float32) * (0.6 + 0.7 * strength)
            self.pos[free] = d * 0.08
            self.vel[free] = d * sp[:, None]
            life = rng.uniform(1.4, 3.0, k)
        elif kind == 2:
            self.pos[free] = d * rng.uniform(0.5, 1.6, (k, 1)).astype(np.float32)
            self.vel[free] = rng.normal(0, 0.25, (k, 3)).astype(np.float32)
            life = rng.uniform(0.25, 0.7, k)
        else:
            r = rng.uniform(0.15, 0.7, k).astype(np.float32)
            self.pos[free] = d * r[:, None]
            tang = np.cross(np.array([0, 1, 0], np.float32), d)
            self.vel[free] = tang * rng.uniform(0.6, 1.4, (k, 1)).astype(np.float32) + d * 0.3
            life = rng.uniform(2.0, 4.5, k)
        self.life[free] = life
        self.maxlife[free] = life
        self.kind[free] = kind
        self.hue[free] = rng.uniform(0, 1, k) if kind == 1 else rng.uniform(0.0, 0.6, k)

    def render(self, ctx):
        cv = self.cv
        dt = float(min(ctx.dt, 0.05))
        cv.decay(0.80 - 0.08 * ctx.treb)
        # emisión continua (siempre hay movimiento) + reactiva
        self.emit_acc += dt * (60 + 220 * ctx.mid + 120 * ctx.vol)
        m = int(self.emit_acc)
        self.emit_acc -= m
        self._spawn(m, 0)
        if ctx.peak:
            self._spawn(int(260 + 700 * ctx.peak_strength), 1, ctx.peak_strength)
        if ctx.treb > 0.12:
            self._spawn(int(ctx.treb * 90 * dt * 60 / 60 * 3), 2)
        # física: atracción al centro + giro (se agrupan) + fricción
        alive = self.life > 0
        p, v = self.pos, self.vel
        r2 = np.sum(p * p, axis=1, keepdims=True) + 0.05
        tang = np.stack([-p[:, 2], np.zeros(self.N, np.float32), p[:, 0]], 1)
        k_att = 2.2 + 2.5 * ctx.bass
        v += (-p * k_att + tang * (1.2 + 1.5 * ctx.mid)) * dt
        v *= np.exp(-dt * np.where(self.kind == 1, 0.9, 1.4))[:, None]
        p += v * dt
        self.life -= dt * alive
        # cámara orbital
        self.cam += ctx.dt * (0.25 + 0.4 * ctx.mid)
        R = rot_matrix(0.35 * np.sin(ctx.t * 0.2) + 0.15, self.cam, 0.0)
        a = alive & (self.life > 0)
        Pa = p[a] @ R.T
        fade = np.clip(self.life[a] / self.maxlife[a] * 1.4, 0, 1)
        speed = np.linalg.norm(v[a], axis=1)
        lum = np.clip((0.35 + 0.35 * np.clip(speed / 2, 0, 1)) * fade + 0.25 * (self.kind[a] == 2), 0, 1)
        lum = np.where(self.kind[a] == 1, np.clip(lum + 0.3, 0, 1), lum)
        hue = (self.hue[a] + 0.03 * ctx.t) % 1.0
        D = 4.0
        Pa = Pa * 0.62
        col, row, near = project(ctx, Pa, D)
        cv.plot(col, row, near, lum, hue)
        # estela: segundo punto desplazado contra la velocidad
        Pt = ((p[a] - v[a] * 0.045) @ R.T) * 0.62
        col2, row2, near2 = project(ctx, Pt, D)
        cv.plot(col2, row2, near2 - 0.01, lum * 0.6, hue)
        # halo orbital permanente
        ang = self.rphase + ctx.t * self.rspd * (0.8 + 1.5 * ctx.bass)
        rad = self.rrad * (1.0 + 0.30 * ctx.bass + 0.15 * np.sin(ctx.t * 0.7 + self.rphase * 3))
        ring = np.stack([np.cos(ang) * rad, self.ry * (1 + 2 * ctx.mid) + 0.05 * np.sin(ang * 3 + ctx.t), np.sin(ang) * rad], 1).astype(np.float32)
        Rr = (ring @ R.T) * 0.9
        col, row, near = project(ctx, Rr, D)
        cv.plot(col, row, near, np.full(self.RING, 0.55 + 0.4 * ctx.treb, np.float32), (ang / (2 * np.pi)) % 1.0)
