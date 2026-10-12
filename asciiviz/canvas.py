"""Lienzo ASCII (buffers de luminancia/color) y renderizador de glifos con pygame."""
from __future__ import annotations
import numpy as np
import pygame

from .palettes import P, B, Palette

RAMP = " .,-~:;=!*#$@"
EXTRA = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ[]|/\\-_+<>:=%.*#"
NGLYPH = len(RAMP) + len(EXTRA)
_CODE = {ch: i + 1 for i, ch in enumerate(EXTRA)}


class Canvas:
    """Cuadrícula de caracteres: luminancia (elige el carácter) y tono (elige el color)."""

    def __init__(self, rows: int, cols: int):
        self.rows = rows
        self.cols = cols
        self.lum = np.zeros((rows, cols), np.float32)
        self.hue = np.zeros((rows, cols), np.float32)
        self.cov = np.zeros((rows, cols), bool)
        self.zb = np.full(rows * cols, -1e9, np.float32)
        self.ovr = np.zeros((rows, cols), np.int16)   # capa de texto/HUD (0 = ninguno)

    def put_text(self, row, col, text, lum, hue):
        if not (0 <= row < self.rows):
            return
        for i, ch in enumerate(text):
            cc = col + i
            code = _CODE.get(ch.upper(), 0)
            if 0 <= cc < self.cols and code:
                self.ovr[row, cc] = code
                self.lum[row, cc] = lum
                self.hue[row, cc] = hue

    def clear(self):
        self.ovr[:] = 0
        self.lum[:] = 0
        self.hue[:] = 0
        self.cov[:] = False
        self.zb[:] = -1e9

    def decay(self, k: float):
        """Persistencia: los puntos anteriores se desvanecen (estelas)."""
        self.lum *= k
        self.cov[:] = False
        self.zb[:] = -1e9

    def plot(self, col, row, near, lum, hue):
        """Dibuja puntos con z-buffer. 'near' mayor = más cerca de la cámara."""
        ci = np.rint(col).astype(np.int32)
        ri = np.rint(row).astype(np.int32)
        m = (ci >= 0) & (ci < self.cols) & (ri >= 0) & (ri < self.rows)
        if not m.any():
            return
        flat = ri[m] * self.cols + ci[m]
        nr = near[m]
        order = np.argsort(nr, kind="stable")
        flat = flat[order]
        nr = nr[order]
        lm = np.broadcast_to(lum, near.shape)[m][order]
        hu = np.broadcast_to(hue, near.shape)[m][order]
        keep = nr >= self.zb[flat]
        flat = flat[keep]
        self.zb[flat] = nr[keep]
        self.lum.reshape(-1)[flat] = lm[keep]
        self.hue.reshape(-1)[flat] = hu[keep]
        self.cov.reshape(-1)[flat] = True
        self.ovr.reshape(-1)[flat] = 0

    def fill_holes(self):
        """Rellena celdas vacías rodeadas de celdas pintadas (evita 'agujeros' en superficies)."""
        c = self.cov
        up = np.zeros_like(c); up[1:] = c[:-1]
        dn = np.zeros_like(c); dn[:-1] = c[1:]
        lf = np.zeros_like(c); lf[:, 1:] = c[:, :-1]
        rt = np.zeros_like(c); rt[:, :-1] = c[:, 1:]
        cnt = up.astype(np.int8) + dn + lf + rt
        holes = (~c) & (cnt >= 3)
        if not holes.any():
            return
        lw = self.lum * c
        hw = self.hue * c

        def nb(a):
            o = np.zeros_like(a)
            o[1:] += a[:-1]; o[:-1] += a[1:]; o[:, 1:] += a[:, :-1]; o[:, :-1] += a[:, 1:]
            return o

        den = np.maximum(cnt, 1)
        self.lum[holes] = (nb(lw) / den)[holes] * 0.9
        self.hue[holes] = (nb(hw) / den)[holes]
        self.cov[holes] = True


class AsciiRenderer:
    """Convierte (luminancia, tono) en glifos y los dibuja con una caché de superficies."""

    def __init__(self):
        self.font = None
        self.size = 0
        self.cw = 8
        self.chh = 16
        self._cache: list = []
        self._pal: Palette | None = None
        self._pos_key = None
        self._pos = None

    def set_font_size(self, size: int):
        size = int(max(8, min(44, size)))
        if size == self.size and self.font is not None:
            return
        names = "consolas,lucidaconsole,couriernew,dejavusansmono,menlo,monospace"
        self.font = pygame.font.SysFont(names, size)
        self.size = size
        w, _ = self.font.size("M")
        self.cw = max(4, w)
        self.chh = max(6, self.font.get_height())
        self.invalidate()

    def invalidate(self):
        self._cache = [None] * (NGLYPH * P * B)
        self._pos_key = None

    def grid_for(self, w: int, h: int):
        return max(8, h // self.chh), max(16, w // self.cw)

    def _positions(self, rows, cols, ox, oy):
        key = (rows, cols, ox, oy, self.cw, self.chh)
        if key != self._pos_key:
            cw, chh = self.cw, self.chh
            self._pos = [(ox + c * cw, oy + r * chh) for r in range(rows) for c in range(cols)]
            self._pos_key = key
        return self._pos

    def _make(self, k: int):
        bi = k % B
        t = k // B
        pi = t % P
        ci = t // P
        rgb = self._pal.rgb(pi, bi)
        surf = pygame.Surface((self.cw, self.chh))
        surf.fill((0, 0, 0))
        g = self.font.render((RAMP + EXTRA)[ci], True, rgb, (0, 0, 0))
        surf.blit(g, ((self.cw - g.get_width()) // 2, (self.chh - g.get_height()) // 2))
        return surf.convert()

    def draw(self, surf, ox, oy, lum, hue, pal: Palette, bright=1.0, shift=0.0, mono=False, ovr=None):
        if pal is not self._pal:
            self._pal = pal
            self.invalidate()
        rows, cols = lum.shape
        n = len(RAMP)
        l = (np.clip(lum * bright, 0.0, 1.0) ** 0.8).ravel()
        ci = (l * (n - 1) + 0.5).astype(np.int32)
        if ovr is not None and ovr.shape == lum.shape:
            o = ovr.ravel().astype(np.int32)
            ci = np.where(o > 0, n + o - 1, ci)
        idx = np.flatnonzero(ci > 0)
        if idx.size == 0:
            return
        c = ci[idx]
        h = hue.ravel()[idx]
        lf = l[idx]
        if mono:
            pi = np.full(idx.size, int(0.62 * (P - 1)), np.int32)
        elif pal.cyclic:
            pi = (np.floor(((h + shift) % 1.0) * P).astype(np.int32)) % P
        else:
            pi = np.clip(h * (P - 1) + 0.5, 0, P - 1).astype(np.int32)
        bi = np.clip(lf * 1.15 * (B - 1) + 0.5, 0, B - 1).astype(np.int32)
        keys = (c * P + pi) * B + bi
        cache = self._cache
        for k in np.unique(keys).tolist():
            if cache[k] is None:
                cache[k] = self._make(k)
        pos = self._positions(rows, cols, ox, oy)
        blits = [(cache[k], pos[i]) for i, k in zip(idx.tolist(), keys.tolist())]
        surf.blits(blits, doreturn=False)
