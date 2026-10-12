"""Cráneo, cerebro y rostro 3D (nubes de puntos con normales) rodeados de un HUD ASCII."""
from __future__ import annotations
import numpy as np
from .base import Effect, project, light_dir, shade_portrait
from .hud import Aura
from ..mathutil import rot_matrix


class MeshEffect(Effect):
    cloud = ""
    spin = (0.18, 0.55, 0.06)   # velocidades de giro (X, Y, Z)
    ao_strength = 0.9
    scale = 1.0
    bump = 0.035                # amplitud de la deformación por graves
    key = 0.35                  # peso de la luz clave
    base = 0.14                 # luz ambiente
    front = 0.45                # luz frontal (hacia la cámara)
    expo = 0.88                 # exposición (evita saturar todo a '@')
    stipple = 0.05              # grano de la superficie
    accent_hue = 1.0
    contrast = 1.0              # contraste tonal (caras muy diferenciadas = aspecto facetado)

    def __init__(self):
        super().__init__()
        self.ax = 0.25
        self.ay = 0.0
        self.az = 0.0
        self.rng = np.random.default_rng(11)
        self.zoom = 0.0
        self.zoom_v = 0.0
        self.aura = Aura()

    def angles(self, ctx):
        sx, sy, sz = self.spin
        self.ay += ctx.dt * (sy + 0.9 * ctx.mid)
        self.ax = 0.22 * np.sin(ctx.t * 0.31) + 0.08 * ctx.bass
        self.az = 0.05 * np.sin(ctx.t * 0.23)
        return self.ax, self.ay, self.az

    def render(self, ctx):
        cv = self.cv
        cv.clear()
        data = ctx.geo.get(self.cloud) or ctx.geo.placeholder()
        P, N, AO, ACC = data
        if ctx.peak:
            self.zoom_v += 2.4 * ctx.peak_strength
        self.zoom_v += (-60.0 * self.zoom - 9.0 * self.zoom_v) * ctx.dt
        self.zoom += self.zoom_v * ctx.dt
        R = rot_matrix(*self.angles(ctx))
        nz = N @ R[2]
        m = nz > -0.15                      # descarta caras traseras
        Pm, Nm, AOm, ACCm = P[m], N[m], AO[m], ACC[m]
        t = ctx.t
        disp = (self.bump * ctx.bass * np.sin(5.0 * Pm[:, 1] + 3.0 * t)
                + 0.45 * self.bump * ctx.mid * np.sin(9.0 * Pm[:, 0] - 4.0 * t + 6.0 * Pm[:, 2]))
        s = self.scale * (1.0 + 0.06 * ctx.bass + 0.08 * self.zoom)
        Pm = Pm * s + Nm * disp[:, None]
        Pr = Pm @ R.T
        Nr = Nm @ R.T
        L = light_dir(t * 0.35 + 1.6 * ctx.mid)
        lum, diff, rim = shade_portrait(Nr, L, AOm, self.ao_strength, self.key, self.base, self.front)
        lum = lum + self.rng.normal(0.0, self.stipple, lum.shape[0]).astype(np.float32)   # grano halftone
        lum = 0.45 + (lum - 0.45) * self.contrast
        lum = lum * self.expo * (0.85 + 0.15 * Pr[:, 2]) * (0.85 + 0.30 * ctx.vol)
        if ctx.treb > 0.05:
            sp = self.rng.random(lum.shape[0]) < 0.010 * ctx.treb
            lum[sp] = 1.0
        hue = np.clip(0.30 + 0.28 * (0.5 + 0.5 * Pr[:, 2]) + 0.16 * (1.0 - diff), 0.0, 1.0)
        if ACCm.any():                       # puntos de acento (ojos)
            hue = np.where(ACCm > 0.5, self.accent_hue, hue)
            lum = np.where(ACCm > 0.5, np.maximum(lum, 0.88), lum)
        col, row, near = project(ctx, Pr)
        cv.plot(col, row, near, np.clip(lum, 0, 1), hue)
        cv.fill_holes()
        self.aura.draw(ctx, cv)


class Skull(MeshEffect):
    name = "Cráneo 3D"
    cloud = "skull"
    spin = (0.15, 0.50, 0.05)
    ao_strength = 0.95
    key = 0.40
    front = 0.58
    expo = 1.02
    scale = 1.30


class Brain(MeshEffect):
    name = "Cerebro 3D"
    cloud = "brain"
    spin = (0.12, 0.42, 0.04)
    ao_strength = 0.95
    contrast = 1.25
    key = 0.38
    stipple = 0.04
    bump = 0.04
    front = 0.52
    expo = 0.98
    scale = 1.25


class Face(MeshEffect):
    name = "Rostro 3D"
    cloud = "face"
    spin = (0.0, 0.28, 0.0)
    ao_strength = 0.80
    key = 0.75
    base = 0.12
    front = 0.22
    contrast = 1.8
    stipple = 0.05
    bump = 0.012
    expo = 1.18
    scale = 1.05

    def angles(self, ctx):
        # Evita el perfil extremo de esta malla frontal delgada.
        self.ay = float(np.clip(
            0.58 * np.sin(ctx.t * 0.36) + 0.12 * ctx.mid * np.sin(ctx.t * 1.3),
            -0.68, 0.68,
        ))
        self.ax = 0.10 * np.sin(ctx.t * 0.21) + 0.06 * ctx.bass
        return self.ax, self.ay, 0.04 * np.sin(ctx.t * 0.17)

    def render(self, ctx):
        cv = self.cv
        cv.clear()
        data = ctx.geo.get(self.cloud) or ctx.geo.placeholder()
        P, N, AO, ACC = data
        blink = np.sin(ctx.t * 0.78 + 0.6) > 0.992
        mouth_open = min(
            0.20,
            0.18 * max(0.0, np.sin(ctx.t * 1.15)) ** 1.6
            + 0.10 * ctx.bass
            + 0.10 * ctx.mid,
        )
        R = rot_matrix(*self.angles(ctx))
        s = self.scale * (1.0 + 0.06 * ctx.bass)
        Pr = P * s @ R.T
        Nr = N @ R.T
        L = light_dir(ctx.t * 0.35 + 1.6 * ctx.mid)
        lum, diff, _ = shade_portrait(Nr, L, AO, self.ao_strength, self.key, self.base, self.front)
        lum = lum + self.rng.normal(0.0, self.stipple, lum.shape[0]).astype(np.float32)
        lum = (0.45 + (lum - 0.45) * self.contrast) * self.expo * (0.85 + 0.15 * Pr[:, 2]) * (0.85 + 0.30 * ctx.vol)
        hue = np.clip(0.30 + 0.28 * (0.5 + 0.5 * Pr[:, 2]) + 0.16 * (1.0 - diff), 0.0, 1.0)
        eye = ACC > 0.5
        hue = np.where(eye, self.accent_hue, hue)
        lum = np.where(eye, np.maximum(lum, 0.88), lum)
        if blink:
            lum = np.where(eye, 0.0, lum)
        col, row, near = project(ctx, Pr)
        cv.plot(col, row, near, np.clip(lum, 0, 1), hue)

        if mouth_open > 0.025:
            mx, my = np.meshgrid(
                np.linspace(-0.24, 0.24, 48, dtype=np.float32),
                np.linspace(-mouth_open / 2, mouth_open / 2, max(4, int(mouth_open * 55)), dtype=np.float32),
            )
            inside = (mx / 0.24) ** 2 + (my / (mouth_open / 2 + 1e-6)) ** 2 <= 1.0
            mouth = np.stack((mx[inside], my[inside] - 0.37, np.full(inside.sum(), 0.34, np.float32)), axis=1) * s
            mouth = mouth @ R.T
            mc, mr, mz = project(ctx, mouth)
            cv.plot(mc, mr, mz + 0.015, np.zeros(len(mouth), np.float32), np.zeros(len(mouth), np.float32))
        elif mouth_open <= 0.025:
            mouth = np.stack((
                np.linspace(-0.21, 0.21, 36, dtype=np.float32),
                np.full(36, -0.37, np.float32),
                np.full(36, 0.35, np.float32),
            ), axis=1) * s @ R.T
            mc, mr, mz = project(ctx, mouth)
            cv.plot(mc, mr, mz + 0.015, np.full(36, 0.04, np.float32), np.full(36, self.accent_hue, np.float32))

        if blink:
            eye_x = np.linspace(0.15, 0.39, 20, dtype=np.float32)
            eye_y = 0.17 + 0.35 * (eye_x - 0.27)
            eyes = np.concatenate((
                np.stack((-eye_x, eye_y, np.full_like(eye_x, 0.42)), axis=1),
                np.stack((eye_x, eye_y, np.full_like(eye_x, 0.42)), axis=1),
            )) * s @ R.T
            ec, er, ez = project(ctx, eyes)
            cv.plot(ec, er, ez + 0.015, np.ones(len(eyes), np.float32),
                    np.full(len(eyes), self.accent_hue, np.float32))

        cv.fill_holes()
        self.aura.draw(ctx, cv)
