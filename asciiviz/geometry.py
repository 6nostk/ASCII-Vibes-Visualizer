"""Geometría procedural: campos de distancia con signo (SDF) -> nubes de puntos con normales.

Cráneo, cerebro y rostro se modelan con primitivas (elipsoides, cápsulas, cajas) combinadas con
uniones suaves. Después se extrae la superficie como una nube densa de puntos con normales
(vértices + normales de superficie), que el motor rota, proyecta y sombrea en cada fotograma.
"""
from __future__ import annotations
import threading
import numpy as np


# ---------------------------------------------------------------- primitivas SDF
def _len3(a, b, c):
    return np.sqrt(a * a + b * b + c * c)


def sd_ellipsoid(x, y, z, c, r):
    px = (x - c[0]) / r[0]
    py = (y - c[1]) / r[1]
    pz = (z - c[2]) / r[2]
    k0 = _len3(px, py, pz)
    k1 = _len3(px / r[0], py / r[1], pz / r[2])
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-6)


def sd_sphere(x, y, z, c, r):
    return _len3(x - c[0], y - c[1], z - c[2]) - r


def sd_capsule(x, y, z, a, b, r):
    pax, pay, paz = x - a[0], y - a[1], z - a[2]
    bax, bay, baz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    h = np.clip((pax * bax + pay * bay + paz * baz) / (bax * bax + bay * bay + baz * baz), 0, 1)
    return _len3(pax - bax * h, pay - bay * h, paz - baz * h) - r


def sd_box(x, y, z, c, b, rr=0.0):
    qx = np.abs(x - c[0]) - b[0] + rr
    qy = np.abs(y - c[1]) - b[1] + rr
    qz = np.abs(z - c[2]) - b[2] + rr
    out = _len3(np.maximum(qx, 0), np.maximum(qy, 0), np.maximum(qz, 0))
    return out + np.minimum(np.maximum(qx, np.maximum(qy, qz)), 0) - rr


def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b + (a - b) * h - k * h * (1.0 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


# ---------------------------------------------------------------- formas
def skull_sdf(x, y, z):
    """Cráneo humano estilizado SIN mandíbula. Frente = +Z, arriba = +Y."""
    ax = np.abs(x)
    d = sd_ellipsoid(x, y, z, (0, 0.30, -0.10), (0.60, 0.56, 0.70))                  # bóveda craneal
    d = smin(d, sd_ellipsoid(x, y, z, (0, -0.12, -0.22), (0.50, 0.38, 0.52)), 0.14)  # base y occipital
    d = smin(d, sd_box(x, y, z, (0, -0.25, 0.36), (0.26, 0.22, 0.17), 0.10), 0.16)   # maxilar
    d = smin(d, sd_ellipsoid(ax, y, z, (0.46, -0.08, 0.34), (0.11, 0.08, 0.15)), 0.12)  # pómulos suaves
    d = smin(d, sd_ellipsoid(x, y, z, (0, 0.17, 0.54), (0.44, 0.06, 0.12)), 0.14)    # arcos superciliares
    # dientes superiores (repetición de dominio)
    s = 0.07
    qx = np.mod(x + s / 2, s) - s / 2
    zc = -1.7 * x * x
    up = sd_box(qx, y, z - zc, (0, -0.505, 0.53), (0.024, 0.06, 0.04), 0.012)
    d = smin(d, np.maximum(up, np.abs(x) - 0.23), 0.01)
    # cavidades: órbitas, nariz, sienes
    d = smax(d, -sd_ellipsoid(ax, y, z, (0.27, 0.00, 0.50), (0.21, 0.18, 0.34)), 0.05)
    d = smax(d, -sd_ellipsoid(x, y, z, (0, -0.21, 0.70), (0.10, 0.17, 0.30)), 0.04)
    d = smax(d, -sd_ellipsoid(ax, y, z, (0.80, 0.02, 0.22), (0.17, 0.24, 0.26)), 0.12)
    return d


def brain_sdf(x, y, z):
    """Cerebro estilizado: cerebro ovalado único con circunvoluciones, cerebelo y tronco."""
    ax = np.abs(x)
    cer = sd_ellipsoid(x, y, z, (0, 0.06, 0.0), (0.66, 0.54, 0.90))           # cerebro (un solo óvalo)
    cer = smin(cer, sd_ellipsoid(ax, y, z, (0.50, -0.20, 0.12), (0.28, 0.20, 0.50)), 0.12)   # lóbulos temporales
    cer = smin(cer, sd_ellipsoid(x, y, z, (0, 0.0, 0.52), (0.50, 0.46, 0.44)), 0.10)         # lóbulo frontal
    cer = smax(cer, -0.42 - y, 0.10)                                          # base algo plana
    k = 18.0
    f = (np.sin(k * x + 1.8 * np.sin(0.9 * k * y + 1.0))
         + np.sin(k * y + 1.8 * np.sin(0.9 * k * z + 2.0))
         + np.sin(k * z + 1.8 * np.sin(0.9 * k * x + 4.0)))
    cer = cer + 0.034 * np.exp(-(f / 0.55) ** 2) - 0.004 + 0.006 * np.sin(2.3 * f)   # surcos y pliegues
    fis = np.minimum(0.010 - ax, y - 0.10)                                    # fisura interhemisférica (arriba)
    cer = smax(cer, fis, 0.015)
    cb = sd_ellipsoid(x, y, z, (0, -0.40, -0.62), (0.42, 0.20, 0.28))        # cerebelo
    cb = cb + 0.010 * np.sin(46.0 * y + 3.0 * x)
    tronco = sd_capsule(x, y, z, (0, -0.30, -0.18), (0, -0.80, -0.30), 0.110)
    d = smin(cer, cb, 0.05)
    d = smin(d, tronco, 0.06)
    return d


def face_sdf(x, y, z):
    """Rostro humano estilizado (cabeza calva con rasgos). Frente = +Z."""
    ax = np.abs(x)
    d = sd_ellipsoid(x, y, z, (0, 0.08, -0.06), (0.50, 0.66, 0.58))                 # cráneo
    d = smin(d, sd_ellipsoid(x, y, z, (0, -0.42, 0.14), (0.34, 0.30, 0.38)), 0.20)   # mandíbula
    d = smin(d, sd_ellipsoid(ax, y, z, (0.30, -0.12, 0.40), (0.15, 0.12, 0.10)), 0.12)  # pómulos
    d = smin(d, sd_capsule(x, y, z, (0, -0.64, -0.06), (0, -1.02, -0.12), 0.23), 0.14)  # cuello
    # frente / ceja
    d = smin(d, sd_capsule(ax, y, z, (0.02, 0.26, 0.47), (0.31, 0.25, 0.43), 0.040), 0.05)
    # cuencas y ojos
    d = smax(d, -sd_ellipsoid(ax, y, z, (0.20, 0.17, 0.51), (0.12, 0.07, 0.09)), 0.05)
    d = smin(d, sd_ellipsoid(ax, y, z, (0.20, 0.17, 0.455), (0.082, 0.058, 0.06)), 0.01)
    # nariz
    nar = sd_capsule(x, y, z, (0, 0.14, 0.50), (0, -0.10, 0.63), 0.043)
    nar = smin(nar, sd_sphere(x, y, z, (0, -0.12, 0.665), 0.062), 0.05)
    nar = smin(nar, sd_sphere(ax, y, z, (0.065, -0.13, 0.60), 0.042), 0.04)
    d = smin(d, nar, 0.05)
    # labios y boca
    lab = smin(sd_ellipsoid(x, y, z, (0, -0.285, 0.545), (0.115, 0.028, 0.055)),
               sd_ellipsoid(x, y, z, (0, -0.345, 0.535), (0.095, 0.034, 0.055)), 0.01)
    d = smin(d, lab, 0.03)
    d = smax(d, -sd_ellipsoid(x, y, z, (0, -0.315, 0.58), (0.13, 0.030, 0.12)), 0.02)
    # barbilla y orejas
    d = smin(d, sd_ellipsoid(x, y, z, (0, -0.52, 0.45), (0.12, 0.08, 0.10)), 0.08)
    d = smin(d, sd_ellipsoid(ax, y, z, (0.51, 0.04, -0.04), (0.05, 0.14, 0.09)), 0.04)
    return d


SHAPES = {
    # nombre: (función, límites inferior/superior, resolución)
    "skull": (skull_sdf, (-0.95, -1.00, -0.95), (0.95, 0.90, 0.95), 150),
    "brain": (brain_sdf, (-1.10, -1.00, -1.05), (1.10, 0.70, 1.05), 200),
}


def _grad(sdf, x, y, z, e):
    gx = sdf(x + e, y, z) - sdf(x - e, y, z)
    gy = sdf(x, y + e, z) - sdf(x, y - e, z)
    gz = sdf(x, y, z + e) - sdf(x, y, z - e)
    n = np.sqrt(gx * gx + gy * gy + gz * gz) + 1e-9
    return gx / n, gy / n, gz / n


def sdf_to_cloud(sdf, lo, hi, res, shell=0.9, max_points=70000, seed=3):
    """Convierte un SDF en una nube de puntos de superficie con normales."""
    lo = np.array(lo, np.float32)
    hi = np.array(hi, np.float32)
    step = float((hi - lo).max() / res)
    xs = np.arange(lo[0], hi[0], step, dtype=np.float32)
    ys = np.arange(lo[1], hi[1], step, dtype=np.float32)
    zs = np.arange(lo[2], hi[2], step, dtype=np.float32)
    yy, zz = np.meshgrid(ys, zs, indexing="ij")
    yf, zf = yy.ravel(), zz.ravel()
    chunks = []
    for i0 in range(0, len(xs), 6):
        xc = xs[i0:i0 + 6]
        X = np.repeat(xc, yf.size)
        Y = np.tile(yf, xc.size)
        Z = np.tile(zf, xc.size)
        d = sdf(X, Y, Z)
        m = np.abs(d) < step * shell
        if m.any():
            chunks.append(np.stack([X[m], Y[m], Z[m], d[m]], 1))
    arr = np.concatenate(chunks).astype(np.float32)
    x, y, z, d = arr[:, 0], arr[:, 1], arr[:, 2], arr[:, 3]
    e = step * 0.5
    for _ in range(2):
        gx, gy, gz = _grad(sdf, x, y, z, e)
        x = x - d * gx
        y = y - d * gy
        z = z - d * gz
        d = sdf(x, y, z)
    gx, gy, gz = _grad(sdf, x, y, z, e)
    keep = np.abs(d) < step * 0.5
    # oclusión ambiental aproximada: los huecos (órbitas, nariz, surcos) quedan oscuros
    ao = np.zeros_like(x)
    for dist, w in ((0.05, 0.5), (0.14, 0.5)):
        dd = sdf(x + gx * dist, y + gy * dist, z + gz * dist)
        ao += w * np.clip(dd / dist, 0.0, 1.0)
    pts = np.stack([x, y, z], 1)[keep].astype(np.float32)
    nrm = np.stack([gx, gy, gz], 1)[keep].astype(np.float32)
    ao = ao[keep].astype(np.float32)
    if len(pts) > max_points:
        sel = np.random.default_rng(seed).choice(len(pts), max_points, replace=False)
        pts, nrm, ao = pts[sel], nrm[sel], ao[sel]
    return pts, nrm, ao


def _sm(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _face_depth(x, y):
    """Relieve de la máscara (profundidad z) con rasgos angulosos."""
    ax = np.abs(x)
    dome = 0.34 * np.sqrt(np.clip(1.0 - (x / 0.66) ** 2 - (y / 1.15) ** 2, 0.0, 1.0))
    nose = (0.16 * np.exp(-(x / 0.075) ** 2) * _sm(-0.16, 0.30, y) * _sm(0.34, 0.20, y)
            + 0.16 * np.exp(-((x / 0.10) ** 2 + ((y + 0.16) / 0.075) ** 2))
            + 0.06 * np.exp(-(((ax - 0.15) / 0.07) ** 2 + ((y + 0.15) / 0.06) ** 2)))
    brow = 0.12 * np.exp(-((y - 0.31) / 0.05) ** 2) * _sm(0.55, 0.30, ax)
    eyes = -0.17 * np.exp(-(((ax - 0.25) / 0.12) ** 2 + ((y - 0.17) / 0.06) ** 2))
    cheek = 0.12 * np.exp(-(((ax - 0.38) / 0.10) ** 2 + ((y + 0.08) / 0.10) ** 2))
    mouth = -0.07 * np.exp(-((x / 0.26) ** 2 + ((y + 0.37) / 0.09) ** 2))
    lips = 0.07 * np.exp(-((x / 0.20) ** 2 + ((np.abs(y + 0.37) - 0.13) / 0.05) ** 2))
    chin = 0.13 * np.exp(-((x / 0.12) ** 2 + ((y + 0.78) / 0.10) ** 2))
    fore = 0.07 * _sm(0.35, 0.65, y)
    return dome + nose + brow + eyes + cheek + mouth + lips + chin + fore


def build_face_mask(n=18, seed=5):
    """Máscara facial 'low-poly': malla gruesa de triángulos con sombreado plano por faceta.
    Silueta hexagonal, ojos angulosos resaltados y boca abierta (hueco)."""
    rng = np.random.default_rng(seed)
    ys = np.array([0.80, 0.60, 0.40, 0.20, 0.02, -0.16, -0.30, -0.44, -0.58, -0.70, -0.82], np.float32)
    hw = np.array([0.30, 0.50, 0.56, 0.57, 0.55, 0.50, 0.44, 0.38, 0.30, 0.23, 0.14], np.float32)
    us = np.array([-1.0, -0.66, -0.33, 0.0, 0.33, 0.66, 1.0], np.float32)
    X = us[None, :] * hw[:, None]
    Y = np.repeat(ys[:, None], len(us), 1)
    Z = 1.10 * _face_depth(X, Y)
    V = np.stack([X, Y, Z], -1)
    ii, jj = np.meshgrid(np.arange(len(ys) - 1), np.arange(len(us) - 1), indexing="ij")
    tris = []
    for i, j in zip(ii.ravel(), jj.ravel()):
        a, b, c, d = (i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j)
        if (i + j) % 2 == 0:
            tris += [(a, b, c), (a, c, d)]
        else:
            tris += [(a, b, d), (b, c, d)]
    gi, gj = np.meshgrid(np.arange(n + 1), np.arange(n + 1))
    m = (gi + gj) <= n
    bu, bv = gi[m].astype(np.float32) / n, gj[m].astype(np.float32) / n
    P, N, AO, ACC = [], [], [], []
    for t in tris:
        A, B, C = (V[p] for p in t)
        cen = (A + B + C) / 3.0
        cx, cy = abs(float(cen[0])), float(cen[1])
        nn = np.cross(B - A, C - A)
        nn = nn / (np.linalg.norm(nn) + 1e-9)
        if nn[2] < 0:
            nn = -nn
        pts = A[None] + bu[:, None] * (B - A)[None] + bv[:, None] * (C - A)[None]
        P.append(pts)
        N.append(np.tile(nn, (len(pts), 1)))
        ao = float(np.clip(0.88 + rng.uniform(-0.28, 0.12), 0.35, 1.0))
        eye = ((cx - 0.27) / 0.13) ** 2 + ((cy - 0.17 - 0.35 * (cx - 0.27)) / 0.065) ** 2 < 1.0
        AO.append(np.full(len(pts), ao, np.float32))
        ACC.append(np.full(len(pts), 1.0 if eye else 0.0, np.float32))
    P = np.concatenate(P).astype(np.float32)
    P[:, 2] -= 0.12
    return P, np.concatenate(N).astype(np.float32), np.concatenate(AO), np.concatenate(ACC)


class Geometry:
    """Genera las mallas orgánicas en un hilo de fondo para no bloquear la interfaz."""

    def __init__(self):
        self.clouds: dict[str, tuple] = {}
        self.status = "pendiente"
        self._thread = None
        n = 3500
        i = np.arange(n, dtype=np.float32) + 0.5
        phi = np.arccos(1 - 2 * i / n)
        th = np.pi * (1 + 5 ** 0.5) * i
        p = np.stack([np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi), np.cos(phi)], 1).astype(np.float32)
        self._placeholder = (p * 0.7, p.copy(), np.ones(n, np.float32), np.zeros(n, np.float32))

    def start(self):
        if self._thread is None:
            self._thread = threading.Thread(target=self._work, name="geometry", daemon=True)
            self._thread.start()

    def _work(self):
        self.clouds["face"] = build_face_mask()
        for name, (fn, lo, hi, res) in SHAPES.items():
            self.status = f"generando {name}…"
            try:
                P, N, AO = sdf_to_cloud(fn, lo, hi, res)
                self.clouds[name] = (P, N, AO, np.zeros(len(P), np.float32))
            except Exception as exc:  # pragma: no cover
                self.status = f"error generando {name}: {exc}"
                return
        self.status = "listo"

    def get(self, name):
        return self.clouds.get(name)

    def placeholder(self):
        return self._placeholder

    @property
    def ready(self):
        return self.status == "listo"
