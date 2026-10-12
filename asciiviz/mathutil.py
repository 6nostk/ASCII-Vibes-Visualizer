"""Utilidades matemáticas: rotaciones, ruido Perlin vectorizado, funciones de suavizado."""
from __future__ import annotations
import numpy as np


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0 + 1e-9), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def rot_matrix(ax: float, ay: float, az: float) -> np.ndarray:
    """Matriz de rotación R = Rz @ Rx @ Ry. Se aplica como P @ R.T"""
    cx, sx = np.cos(ax), np.sin(ax)
    cy, sy = np.cos(ay), np.sin(ay)
    cz, sz = np.cos(az), np.sin(az)
    rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]], np.float32)
    ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]], np.float32)
    rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]], np.float32)
    return (rz @ rx @ ry).astype(np.float32)


def normalize3(v):
    v = np.asarray(v, np.float32)
    return v / (np.linalg.norm(v) + 1e-9)


def _fade(t):
    return t * t * t * (t * (t * 6 - 15) + 10)


class Perlin:
    """Ruido de gradiente 2D (Perlin) totalmente vectorizado con NumPy."""

    def __init__(self, seed: int = 7):
        rng = np.random.default_rng(seed)
        p = rng.permutation(256).astype(np.int32)
        self.perm = np.concatenate([p, p])
        ang = rng.uniform(0, 2 * np.pi, 256)
        self.gx = np.cos(ang).astype(np.float32)
        self.gy = np.sin(ang).astype(np.float32)

    def noise(self, x, y):
        x = np.asarray(x, np.float32)
        y = np.asarray(y, np.float32)
        x0 = np.floor(x)
        y0 = np.floor(y)
        xi = x0.astype(np.int32) & 255
        yi = y0.astype(np.int32) & 255
        xf = x - x0
        yf = y - y0
        u = _fade(xf)
        v = _fade(yf)
        p = self.perm
        aa = p[p[xi] + yi]
        ab = p[p[xi] + yi + 1]
        ba = p[p[xi + 1] + yi]
        bb = p[p[xi + 1] + yi + 1]
        gx, gy = self.gx, self.gy
        n00 = gx[aa] * xf + gy[aa] * yf
        n10 = gx[ba] * (xf - 1) + gy[ba] * yf
        n01 = gx[ab] * xf + gy[ab] * (yf - 1)
        n11 = gx[bb] * (xf - 1) + gy[bb] * (yf - 1)
        nx0 = n00 + u * (n10 - n00)
        nx1 = n01 + u * (n11 - n01)
        return (nx0 + v * (nx1 - nx0)) * 1.41

    def fbm(self, x, y, octaves=4, lac=2.0, gain=0.5):
        total = 0.0
        amp = 1.0
        norm = 0.0
        for _ in range(octaves):
            total = total + amp * self.noise(x, y)
            norm += amp
            x = x * lac + 17.3
            y = y * lac + 9.1
            amp *= gain
        return total / norm


PERLIN = Perlin()
