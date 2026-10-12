"""Paletas de color. Cada paleta es una tabla de P posiciones de color."""
from __future__ import annotations
import colorsys
from dataclasses import dataclass
import numpy as np

P = 32  # posiciones de color por paleta
B = 6   # niveles de brillo por posición
BRIGHT = (0.30, 0.48, 0.66, 0.82, 0.94, 1.0)


def _gradient(stops):
    xs = [s[0] for s in stops]
    out = np.zeros((P, 3), np.float32)
    for i in range(P):
        t = i / (P - 1)
        for k in range(3):
            out[i, k] = np.interp(t, xs, [s[1][k] for s in stops])
    return out


def _wheel(sat, val=1.0):
    out = np.zeros((P, 3), np.float32)
    for i in range(P):
        r, g, b = colorsys.hsv_to_rgb(i / P, sat, val)
        out[i] = (r * 255, g * 255, b * 255)
    return out


@dataclass
class Palette:
    name: str
    colors: np.ndarray
    cyclic: bool = False   # el valor de color da la vuelta (arcoíris)
    auto: bool = False     # el desplazamiento de tono reacciona a la música

    def rgb(self, pi: int, bi: int):
        c = self.colors[pi] * BRIGHT[bi]
        if bi == B - 1:      # nivel máximo: se acerca al blanco (efecto "brillo")
            c = c + (255.0 - c) * 0.35
        return tuple(int(max(0, min(255, v))) for v in c)


PALETTES = [
    Palette("Cian y magenta", _gradient([(0, (0, 235, 255)), (0.5, (140, 110, 255)), (1, (255, 40, 200))])),
    Palette("Verde terminal", _gradient([(0, (0, 130, 40)), (1, (110, 255, 130))])),
    Palette("Ámbar retro", _gradient([(0, (190, 80, 0)), (1, (255, 200, 60))])),
    Palette("Arcoíris", _wheel(0.85), cyclic=True),
    Palette("Azul eléctrico y violeta", _gradient([(0, (40, 120, 255)), (0.55, (110, 95, 255)), (1, (195, 60, 255))])),
    Palette("Blanco y negro", _gradient([(0, (160, 160, 160)), (1, (255, 255, 255))])),
    Palette("Automática (reactiva)", _wheel(0.75), cyclic=True, auto=True),
    Palette("Rojo neón", _gradient([(0, (95, 0, 20)), (0.48, (255, 30, 65)), (1, (255, 190, 210))])),
    Palette("Océano profundo", _gradient([(0, (0, 35, 95)), (0.5, (0, 165, 210)), (1, (130, 255, 235))])),
    Palette("Atardecer synthwave", _gradient([(0, (35, 15, 100)), (0.48, (225, 35, 170)), (1, (255, 175, 75))])),
    Palette("Verde tóxico", _gradient([(0, (15, 65, 25)), (0.5, (90, 225, 35)), (1, (225, 255, 90))])),
    Palette("Hielo polar", _gradient([(0, (45, 95, 160)), (0.55, (115, 205, 255)), (1, (235, 255, 255))])),
    Palette("Fuego", _gradient([(0, (105, 12, 0)), (0.48, (255, 75, 0)), (1, (255, 235, 90))])),
]
