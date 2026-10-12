"""Visuales musicales: osciloscopio, ecualizador, meteoros, portal y glitch."""
from __future__ import annotations

import numpy as np

from .base import Effect


class Oscilloscope(Effect):
    name = "Osciloscopio"

    def render(self, ctx):
        cv = self.cv
        cv.clear()
        cols = max(32, ctx.cols * 2)
        x = np.linspace(0.0, 1.0, cols, dtype=np.float32)
        center = (ctx.rows - 1) * 0.5
        amplitude = ctx.rows * (0.10 + 0.25 * np.clip(ctx.vol, 0.0, 1.0))
        phase = ctx.t * (2.0 + 4.0 * ctx.bass)
        carrier = (
            np.sin(2.0 * np.pi * (2.0 * x + phase * 0.10))
            + 0.38 * np.sin(2.0 * np.pi * (5.0 * x - phase * 0.17))
            + 0.16 * np.sin(2.0 * np.pi * (11.0 * x + phase * 0.11))
        )
        carrier /= 1.54
        wave = center - carrier * amplitude
        col = x * (ctx.cols - 1)
        hue = (0.50 + 0.38 * x + ctx.t * 0.025) % 1.0
        lum = np.clip(0.58 + 0.35 * np.abs(carrier), 0.0, 1.0)
        cv.plot(col, wave, np.zeros_like(col), lum, hue)
        cv.plot(col, 2.0 * center - wave, np.full_like(col, -0.01), lum * 0.62,
                (hue + 0.22) % 1.0)
        if ctx.peak:
            cv.plot(col, np.full_like(col, center), np.full_like(col, 0.01),
                    np.full_like(col, 0.25 + 0.7 * ctx.peak_strength),
                    np.full_like(col, 0.92))


class RingEqualizer(Effect):
    name = "Ecualizador circular"

    def render(self, ctx):
        cv = self.cv
        cv.clear()
        count = int(max(48, min(144, ctx.cols * 1.2)))
        angles = np.linspace(0, 2.0 * np.pi, count, endpoint=False, dtype=np.float32)
        center_x, center_y = (ctx.cols - 1) * 0.5, (ctx.rows - 1) * 0.5
        radius = min(ctx.cols * 0.20, ctx.rows * 0.23)
        band_mix = np.array((ctx.bass, ctx.mid, ctx.treb, ctx.vol), dtype=np.float32)
        band_mix = np.clip(band_mix, 0.0, 1.0)
        band_idx = np.arange(count) % len(band_mix)
        levels = band_mix[band_idx]
        levels = np.clip(levels * 0.78 + 0.12 + 0.08 * np.sin(angles * 7.0 + ctx.t * 2.0),
                         0.08, 1.0)
        lengths = (2.0 + levels * min(ctx.rows, ctx.cols) * 0.19)
        steps = max(3, int(min(ctx.rows, ctx.cols) * 0.20))
        step = np.arange(steps, dtype=np.float32)[None, :] / max(1, steps - 1)
        radial = radius + step * lengths[:, None]
        cols = center_x + np.cos(angles)[:, None] * radial
        rows = center_y + np.sin(angles)[:, None] * radial
        lum = np.broadcast_to((0.35 + levels * 0.62)[:, None], cols.shape)
        hue = np.broadcast_to(((angles / (2.0 * np.pi) + ctx.t * 0.025) % 1.0)[:, None], cols.shape)
        cv.plot(cols.ravel(), rows.ravel(), np.zeros(cols.size, np.float32),
                lum.ravel(), hue.ravel())

        ring_angles = np.linspace(0, 2.0 * np.pi, 240, endpoint=False, dtype=np.float32)
        ring_x = center_x + np.cos(ring_angles) * radius
        ring_y = center_y + np.sin(ring_angles) * radius
        cv.plot(ring_x, ring_y, np.full_like(ring_x, -0.01),
                np.full_like(ring_x, 0.45), (ring_angles / (2 * np.pi) + 0.55) % 1.0)


class MeteorShower(Effect):
    name = "Lluvia de meteoros"
    COUNT = 72

    def __init__(self):
        super().__init__()
        self.rng = np.random.default_rng(105)
        self.x = np.empty(0, np.float32)
        self.y = np.empty(0, np.float32)
        self.speed = np.empty(0, np.float32)
        self.length = np.empty(0, np.float32)
        self.hue = np.empty(0, np.float32)
        self.active = np.empty(0, bool)
        self._shape = None

    def on_resize(self, ctx):
        self._shape = (ctx.rows, ctx.cols)
        self.x = self.rng.uniform(-ctx.cols, ctx.cols, self.COUNT).astype(np.float32)
        self.y = self.rng.uniform(-ctx.rows, ctx.rows, self.COUNT).astype(np.float32)
        self.speed = self.rng.uniform(8.0, 24.0, self.COUNT).astype(np.float32)
        self.length = self.rng.uniform(3.0, 12.0, self.COUNT).astype(np.float32)
        self.hue = self.rng.uniform(0.48, 0.86, self.COUNT).astype(np.float32)
        self.active = self.rng.random(self.COUNT) < 0.68

    def render(self, ctx):
        cv = self.cv
        cv.clear()
        if self._shape != (ctx.rows, ctx.cols):
            self.on_resize(ctx)
        dt = min(max(float(ctx.dt), 0.0), 0.05)
        self.y += self.speed * dt * (0.75 + np.clip(ctx.bass, 0.0, 1.5))
        offscreen = self.y - self.length > ctx.rows
        self.active[offscreen] = True
        self.y[offscreen] = self.rng.uniform(-ctx.rows * 0.5, -1.0, int(offscreen.sum()))
        self.x[offscreen] = self.rng.uniform(0.0, max(1, ctx.cols), int(offscreen.sum()))
        if ctx.peak:
            spawn_count = min(self.COUNT, 5 + int(12 * ctx.peak_strength))
            chosen = self.rng.choice(self.COUNT, size=spawn_count, replace=False)
            self.active[chosen] = True
            self.y[chosen] = self.rng.uniform(-ctx.rows * 0.7, 0.0, spawn_count)
            self.x[chosen] = self.rng.uniform(0.0, max(1, ctx.cols), spawn_count)
            self.speed[chosen] = self.rng.uniform(12.0, 30.0, spawn_count)
        active = self.active & (self.y >= 0) & (self.y < ctx.rows + self.length)
        head_x, head_y = self.x[active], self.y[active]
        for tail in range(5):
            frac = tail / 4.0
            cv.plot(head_x - frac * self.length[active] * 0.42,
                    head_y - frac * self.length[active],
                    np.zeros_like(head_x),
                    np.full_like(head_x, 0.95 - frac * 0.72),
                    (self.hue[active] + frac * 0.08) % 1.0)


class WavePortal(Effect):
    name = "Portal de ondas"
    RING_COUNT = 7

    def __init__(self):
        super().__init__()
        self.rings = []
        self.last_pulse = 0.0

    def render(self, ctx):
        cv = self.cv
        cv.clear()
        dt = max(0.0, float(ctx.dt))
        self.last_pulse += dt
        if ctx.peak:
            self.rings.append([0.0, float(np.clip(ctx.peak_strength, 0.2, 1.0))])
        if self.last_pulse >= 0.72:
            self.rings.append([0.0, float(np.clip(0.25 + ctx.bass * 0.55, 0.2, 0.8))])
            self.last_pulse %= 0.72
        self.rings = [[age + dt, strength] for age, strength in self.rings if age + dt < 3.2]

        center_x, center_y = (ctx.cols - 1) * 0.5, (ctx.rows - 1) * 0.5
        max_radius = np.hypot(ctx.cols * 0.5, ctx.rows * 0.5)
        angles = np.linspace(0.0, 2.0 * np.pi, max(120, ctx.cols * 2),
                             endpoint=False, dtype=np.float32)
        for age, strength in self.rings[-self.RING_COUNT:]:
            radius = 2.0 + age * max_radius * 0.52
            wobble = 1.0 + 0.035 * np.sin(angles * 9.0 - age * 5.0)
            r = radius * wobble
            x = center_x + np.cos(angles) * r
            y = center_y + np.sin(angles) * r
            fade = max(0.0, 1.0 - age / 3.2)
            lum = np.full_like(x, (0.35 + strength * 0.62) * fade)
            hue = (0.78 + age * 0.11 + angles / (2.0 * np.pi) * 0.18) % 1.0
            cv.plot(x, y, np.zeros_like(x), lum, hue)

        core_radius = 1.5 + np.clip(ctx.bass, 0.0, 1.0) * 3.0
        cv.plot(center_x + np.cos(angles) * core_radius,
                center_y + np.sin(angles) * core_radius,
                np.full_like(angles, 0.02),
                np.full_like(angles, 0.88), np.full_like(angles, 0.52))


class Glitch(Effect):
    name = "Glitch digital"
    CHARS = "01#%+=<>[]{}"

    def __init__(self):
        super().__init__()
        self.rng = np.random.default_rng(707)
        self.phase = 0.0

    def render(self, ctx):
        cv = self.cv
        cv.clear()
        self.phase += max(0.0, float(ctx.dt)) * (2.0 + ctx.treb * 5.0)
        band_count = max(3, ctx.rows // 8)
        for band in range(band_count):
            row = int((band * 7 + self.phase * (3 + band % 3)) % max(1, ctx.rows))
            width = int(self.rng.integers(max(3, ctx.cols // 12), max(4, ctx.cols // 3)))
            col = int(self.rng.integers(0, max(1, ctx.cols - width + 1)))
            shift = int(self.rng.integers(-max(1, ctx.cols // 8), max(2, ctx.cols // 8)))
            hue = (0.52 + band * 0.11 + self.phase * 0.025) % 1.0
            text = "".join(self.rng.choice(tuple(self.CHARS), size=width))
            cv.put_text(row, col + shift, text, 0.25 + 0.55 * self.rng.random(), hue)
            if band % 2 == 0 and row + 1 < ctx.rows:
                cv.put_text(row + 1, col, text[::-1], 0.18 + 0.3 * ctx.vol,
                            (hue + 0.22) % 1.0)

        if ctx.peak:
            count = max(8, ctx.cols // 2)
            cols = self.rng.integers(0, ctx.cols, count)
            rows = self.rng.integers(0, ctx.rows, count)
            cv.plot(cols.astype(np.float32), rows.astype(np.float32),
                    np.zeros(count, np.float32), np.ones(count, np.float32),
                    self.rng.choice(np.array([0.52, 0.88]), count).astype(np.float32))
