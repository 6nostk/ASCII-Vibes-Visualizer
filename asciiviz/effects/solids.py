"""Cubo y tetraedro/estrella tetraédrica con caras, aristas y profundidad."""
from __future__ import annotations
import numpy as np
from .base import Effect, project, light_dir
from ..mathutil import rot_matrix


def _edge_points(a, b, n):
    t = np.linspace(0, 1, n, dtype=np.float32)[:, None]
    return a[None, :] * (1 - t) + b[None, :] * t


_TRI_CACHE = {}


def _tri_points(a, b, c, n):
    uv = _TRI_CACHE.get(n)
    if uv is None:
        ii, jj = np.meshgrid(np.arange(n + 1), np.arange(n + 1))
        m = (ii + jj) <= n
        uv = (ii[m].astype(np.float32) / n, jj[m].astype(np.float32) / n)
        _TRI_CACHE[n] = uv
    u, v = uv
    return (a[None, :] + u[:, None] * (b - a)[None, :] + v[:, None] * (c - a)[None, :]).astype(np.float32)


class SolidEffect(Effect):
    def __init__(self):
        super().__init__()
        self.ax = self.ay = self.az = 0.3
        self.pulse = 0.0
        self.pulse_v = 0.0
        self.rng = np.random.default_rng(3)
        self._key = None

    def spring(self, ctx):
        if ctx.peak:
            self.pulse_v += 3.2 * ctx.peak_strength
        self.pulse_v += (-55.0 * self.pulse - 8.0 * self.pulse_v) * ctx.dt
        self.pulse += self.pulse_v * ctx.dt

    def rotate(self, ctx):
        k = 1.0 + 1.6 * ctx.bass + 2.0 * self.pulse_v * 0.05
        self.ax += ctx.dt * 0.55 * k
        self.ay += ctx.dt * 0.80 * k
        self.az += ctx.dt * (0.22 + 0.5 * ctx.mid)
        return rot_matrix(self.ax, self.ay, self.az)

    def draw_pts(self, ctx, P, lum, hue, D=4.6):
        col, row, near = project(ctx, P, D)
        self.cv.plot(col, row, near, np.clip(lum, 0, 1), np.broadcast_to(hue, lum.shape).astype(np.float32))


class Cube(SolidEffect):
    name = "Cubo 3D"

    def _build(self, ctx):
        side_cells = 1.3 * ctx.unit / min(ctx.cw, ctx.ch)
        n = int(np.clip(side_cells * 1.4, 36, 110))
        if self._key is not None and abs(n - self._key) < 0.2 * self._key:
            return
        self._key = n
        u = np.linspace(-1, 1, n, dtype=np.float32)
        U, V = np.meshgrid(u, u)
        U, V = U.ravel(), V.ravel()
        pts, nrm, uu, vv = [], [], [], []
        for axis in range(3):
            for sgn in (1.0, -1.0):
                P = np.zeros((U.size, 3), np.float32)
                idx = [i for i in range(3) if i != axis]
                P[:, idx[0]], P[:, idx[1]], P[:, axis] = U, V, sgn
                N = np.zeros_like(P)
                N[:, axis] = sgn
                pts.append(P); nrm.append(N); uu.append(U); vv.append(V)
        self.fp = np.concatenate(pts)
        self.fn = np.concatenate(nrm)
        U = np.concatenate(uu); V = np.concatenate(vv)
        line = (np.abs(((U + 1) * 2 + 0.5) % 1 - 0.5) < 0.05) | (np.abs(((V + 1) * 2 + 0.5) % 1 - 0.5) < 0.05)
        self.fline = line.astype(np.float32)
        corners = np.array([[x, y, z] for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)], np.float32)
        edges = []
        for i in range(8):
            for j in range(i + 1, 8):
                if np.sum(corners[i] != corners[j]) == 1:
                    edges.append(_edge_points(corners[i], corners[j], int(np.clip(n * 1.6, 60, 180))))
        self.ep = np.concatenate(edges)
        self.corners = corners

    def render(self, ctx):
        cv = self.cv
        cv.clear()
        self._build(ctx)
        self.spring(ctx)
        R = self.rotate(ctx)
        size = 0.60 * (1 + 0.10 * ctx.bass + 0.12 * self.pulse)
        L = light_dir(ctx.t * 0.4)
        if not ctx.wire:
            Pf = self.fp * size + self.fn * (0.30 * max(self.pulse, 0.0) + 0.05 * ctx.bass)
            Pr = Pf @ R.T
            Nr = self.fn @ R.T
            diff = np.clip(Nr @ L, 0, 1)
            lum = 0.16 + 0.60 * diff + 0.30 * self.fline * (0.4 + diff)
            lum = lum * (0.85 + 0.30 * ctx.vol)
            hue = 0.15 + 0.5 * (1 - diff) + 0.1 * Pr[:, 2] + 0.3 * self.fline
            if ctx.treb > 0.05:
                sp = self.rng.random(lum.shape[0]) < 0.02 * ctx.treb
                lum[sp] = 1.0
            self.draw_pts(ctx, Pr, lum, hue)
        Er = (self.ep * size) @ R.T
        lum_e = np.full(len(Er), 1.0, np.float32) * (0.75 + 0.25 * (Er[:, 2] / size))
        self.draw_pts(ctx, Er, lum_e, 0.85 + 0.1 * Er[:, 2] / size)
        # cubo interior en alambre, girando en sentido contrario
        R2 = rot_matrix(-self.ay * 0.7, self.ax * 0.9, -self.az)
        Ei = (self.ep * size * (0.42 + 0.12 * ctx.mid + 0.1 * ctx.bass)) @ R2.T
        self.draw_pts(ctx, Ei, np.full(len(Ei), 0.8, np.float32), 0.2 + 0.1 * Ei[:, 2])
        Vr = (self.corners * size) @ R.T
        for k in range(8):                        # vértices brillantes
            cp = np.repeat(Vr[k:k + 1], 1, 0)
            col, row, near = project(ctx, cp, 4.6)
            for dc, dr in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
                cv.plot(col + dc, row + dr, near + 0.01, np.array([1.0]), np.array([0.55]))
        if not ctx.wire:
            cv.fill_holes()

    name = "Cubo 3D"


class Tetra(SolidEffect):
    name = "Tetraedro / Estrella"

    BASE = np.array([[1, 1, 1], [1, -1, -1], [-1, 1, -1], [-1, -1, 1]], np.float32) / np.sqrt(3.0)

    def _tet(self, ctx, V, scale, R, L, hue0, dual):
        Vs = V * scale
        faces = [(0, 1, 2), (0, 3, 1), (0, 2, 3), (1, 3, 2)]
        pts, nrm = [], []
        n = int(np.clip(1.3 * ctx.unit / min(ctx.cw, ctx.ch), 28, 80))
        for f in faces:
            a, b, c = Vs[f[0]], Vs[f[1]], Vs[f[2]]
            nn = np.cross(b - a, c - a)
            nn = nn / (np.linalg.norm(nn) + 1e-9)
            if np.dot(nn, (a + b + c) / 3) < 0:
                nn = -nn
            P = _tri_points(a, b, c, n)
            pts.append(P); nrm.append(np.tile(nn, (len(P), 1)))
        P = np.concatenate(pts) if not ctx.wire else None
        edges = []
        for i in range(4):
            for j in range(i + 1, 4):
                edges.append(_edge_points(Vs[i], Vs[j], 150))
        E = np.concatenate(edges)
        if not ctx.wire:
            Pr = P @ R.T
            Nr = np.concatenate(nrm) @ R.T
            diff = np.clip(Nr @ L, 0, 1)
            lum = (0.16 + 0.62 * diff) * (0.85 + 0.3 * ctx.vol)
            hue = hue0 + 0.35 * (1 - diff) + 0.08 * Pr[:, 2]
            if ctx.treb > 0.05:
                lum[self.rng.random(len(lum)) < 0.02 * ctx.treb] = 1.0
            self.draw_pts(ctx, Pr, lum, hue)
        Er = E @ R.T
        flash = 0.0
        lum_e = np.clip(0.85 + 0.15 * Er[:, 2] / max(scale, 1e-3), 0, 1).astype(np.float32)
        if ctx.treb > 0.05:
            lum_e[self.rng.random(len(lum_e)) < 0.04 * ctx.treb] = 1.0
        self.draw_pts(ctx, Er, lum_e, hue0 + 0.12 + 0.1 * Er[:, 2])
        Vr = Vs @ R.T
        for k in range(4):
            col, row, near = project(ctx, Vr[k:k + 1], 4.6)
            for dc, dr in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
                self.cv.plot(col + dc, row + dr, near + 0.01, np.array([1.0]), np.array([hue0 + 0.2]))

    def render(self, ctx):
        cv = self.cv
        cv.clear()
        self.spring(ctx)
        R = self.rotate(ctx)
        L = light_dir(ctx.t * 0.4)
        size = 0.95 * (1 + 0.10 * ctx.bass + 0.14 * self.pulse)
        # el segundo tetraedro crece y decrece: tetraedro -> estrella tetraédrica
        k = 0.5 + 0.5 * np.sin(ctx.t * 0.22 - 1.2)
        second = 0.06 + 0.94 * float(np.clip(k * 1.4 - 0.1, 0, 1))
        self._tet(ctx, self.BASE, size, R, L, 0.08, False)
        self._tet(ctx, -self.BASE, size * second, R, L, 0.60, True)
        if not ctx.wire:
            cv.fill_holes()
