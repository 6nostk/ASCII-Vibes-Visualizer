"""Animated ASCII wordmark effect for a DJ name."""
from __future__ import annotations
import numpy as np

from .base import Effect


_FONT = {
    "A": ("###", "#.#", "###", "#.#", "#.#"),
    "B": ("##.", "#.#", "##.", "#.#", "##."),
    "C": (".##", "#..", "#..", "#..", ".##"),
    "D": ("##.", "#.#", "#.#", "#.#", "##."),
    "E": ("###", "#..", "##.", "#..", "###"),
    "F": ("###", "#..", "##.", "#..", "#.."),
    "G": (".##", "#..", "#.#", "#.#", ".##"),
    "H": ("#.#", "#.#", "###", "#.#", "#.#"),
    "I": ("###", ".#.", ".#.", ".#.", "###"),
    "J": ("..#", "..#", "..#", "#.#", ".#."),
    "K": ("#.#", "#.#", "##.", "#.#", "#.#"),
    "L": ("#..", "#..", "#..", "#..", "###"),
    "M": ("#.#", "###", "###", "#.#", "#.#"),
    "N": ("#.#", "###", "###", "###", "#.#"),
    "O": (".#.", "#.#", "#.#", "#.#", ".#."),
    "P": ("##.", "#.#", "##.", "#..", "#.."),
    "Q": (".#.", "#.#", "#.#", ".##", "..#"),
    "R": ("##.", "#.#", "##.", "#.#", "#.#"),
    "S": (".##", "#..", ".#.", "..#", "##."),
    "T": ("###", ".#.", ".#.", ".#.", ".#."),
    "U": ("#.#", "#.#", "#.#", "#.#", "###"),
    "V": ("#.#", "#.#", "#.#", "#.#", ".#."),
    "W": ("#.#", "#.#", "###", "###", "#.#"),
    "X": ("#.#", "#.#", ".#.", "#.#", "#.#"),
    "Y": ("#.#", "#.#", ".#.", ".#.", ".#."),
    "Z": ("###", "..#", ".#.", "#..", "###"),
    "0": ("###", "#.#", "#.#", "#.#", "###"),
    "1": (".#.", "##.", ".#.", ".#.", "###"),
    "2": ("##.", "..#", ".#.", "#..", "###"),
    "3": ("##.", "..#", ".#.", "..#", "##."),
    "4": ("#.#", "#.#", "###", "..#", "..#"),
    "5": ("###", "#..", "##.", "..#", "##."),
    "6": (".##", "#..", "###", "#.#", "###"),
    "7": ("###", "..#", ".#.", ".#.", ".#."),
    "8": ("###", "#.#", "###", "#.#", "###"),
    "9": ("###", "#.#", "###", "..#", "##."),
    "-": ("...", "...", "###", "...", "..."),
    "_": ("...", "...", "...", "...", "###"),
}


class NameArt(Effect):
    name = "Visual DJ ASCII"
    _RAIN_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ[]|/\\-_+<>:=%.*#"

    def __init__(self):
        super().__init__()
        self.pulse = 0.0
        self.rain_rng = np.random.default_rng(2026)
        self.rain_shape = None
        self.rain_cols = np.empty(0, dtype=np.int32)
        self.rain_heads = np.empty(0, dtype=np.float32)
        self.rain_speeds = np.empty(0, dtype=np.float32)
        self.rain_lengths = np.empty(0, dtype=np.int32)

    def _draw_matrix_rain(self, ctx):
        shape = (ctx.rows, ctx.cols)
        if shape != self.rain_shape:
            self.rain_shape = shape
            self.rain_cols = np.arange(0, ctx.cols, 2, dtype=np.int32)
            count = len(self.rain_cols)
            self.rain_heads = self.rain_rng.uniform(0, max(1, ctx.rows), count).astype(np.float32)
            self.rain_speeds = self.rain_rng.uniform(7.0, 19.0, count).astype(np.float32)
            self.rain_lengths = self.rain_rng.integers(5, 15, count, dtype=np.int32)

        self.rain_heads += self.rain_speeds * max(0.0, float(ctx.dt))
        reset = self.rain_heads >= ctx.rows + self.rain_lengths
        reset_count = int(np.count_nonzero(reset))
        if reset_count:
            self.rain_heads[reset] = self.rain_rng.uniform(-8.0, 0.0, reset_count)
            self.rain_speeds[reset] = self.rain_rng.uniform(7.0, 19.0, reset_count)
            self.rain_lengths[reset] = self.rain_rng.integers(5, 15, reset_count)

        glyph_count = len(self._RAIN_CHARS)
        for col, head, length in zip(self.rain_cols, self.rain_heads, self.rain_lengths):
            head_row = int(head)
            for offset in range(int(length)):
                row = head_row - offset
                if not 0 <= row < ctx.rows:
                    continue
                glyph = self._RAIN_CHARS[int(self.rain_rng.integers(glyph_count))]
                if offset == 0:
                    lum, hue = 0.95, 0.35
                else:
                    lum = max(0.14, 0.62 * (1.0 - offset / (length + 1.0)))
                    hue = (0.32 + offset * 0.003) % 1.0
                self.cv.put_text(row, int(col), glyph, lum, hue)

    def render(self, ctx):
        cv = self.cv
        cv.clear()
        self._draw_matrix_rain(ctx)
        name = "".join(ch for ch in (ctx.name or "DJ").upper()[:16]
                       if ch in _FONT or ch == " ")
        if not name:
            name = "DJ"
        scale = max(1, min(3, (ctx.cols - 8) // max(1, len(name) * 6 - 1),
                           (ctx.rows - 8) // 7))
        glyph_width = len(name) * 6 - 1
        total_width = glyph_width * scale
        total_height = 7 * scale
        start_col = max(0, (ctx.cols - total_width) // 2)
        start_row = max(0, (ctx.rows - total_height) // 2)
        phase = ctx.t * 0.7
        drift_x = int(round(np.sin(phase * 0.6) * min(3, max(0, (ctx.cols - total_width) // 2))))
        drift_y = int(round(np.sin(phase) * min(2, max(0, (ctx.rows - total_height) // 2))))
        col0 = max(0, min(ctx.cols - total_width, start_col + drift_x))
        row0 = max(0, min(ctx.rows - total_height, start_row + drift_y))

        cx = col0 + total_width / 2.0
        cy = row0 + total_height / 2.0
        signal = max(
            float(ctx.vol),
            float(ctx.bass) * 0.9,
            float(ctx.mid) * 0.7,
            float(ctx.treb) * 0.5,
            float(ctx.peak_strength) if ctx.peak else 0.0,
        )
        target_pulse = float(np.clip(signal, 0.0, 1.0))
        pulse_dt = max(0.0, float(ctx.dt))
        pulse_rate = 12.0 if target_pulse > self.pulse else 4.0
        self.pulse += (target_pulse - self.pulse) * (1.0 - np.exp(-pulse_rate * pulse_dt))
        half_width = max(1.0, total_width / 2.0)
        half_height = max(1.0, total_height / 2.0)
        max_pulse_scale = min(
            1.24,
            (cx - 1.0) / half_width,
            (ctx.cols - 2.0 - cx) / half_width,
            (cy - 1.0) / half_height,
            (ctx.rows - 2.0 - cy) / half_height,
        )
        pulse_scale = 1.0 + max(0.0, max_pulse_scale - 1.0) * self.pulse
        arc_w = total_width * 0.68
        arc_h = total_height * 0.86

        def add_brain_arc(side, offset, color_h):
            for i in range(32):
                t = i / 31.0
                x = cx + side * (arc_w * (0.38 + 0.22 * t) + 4.0 * np.sin(phase + t * 8.0 + offset))
                y = cy + arc_h * (t - 0.5) * 0.9 + 8.0 * np.sin(phase * 1.8 + t * 20.0 + offset)
                lum = 0.30 + 0.35 * np.sin((t + offset) * 7.0 + phase)
                cv.plot(np.array([x], dtype=np.float32),
                        np.array([y], dtype=np.float32),
                        np.array([0.0], dtype=np.float32),
                        np.array([lum], dtype=np.float32),
                        np.array([color_h], dtype=np.float32))

        for side in (-1.0, 1.0):
            for wave in range(6):
                y_base = cy - arc_h * 0.38 + wave * (arc_h * 0.14)
                for i in range(20):
                    t = i / 19.0
                    x = cx + side * (arc_w * (0.34 + 0.18 * t) + 12.0 * np.sin(phase * 1.3 + t * 10.0 + wave))
                    y = y_base + (arc_h * 0.16) * np.sin((t * 4.0) + phase + wave * 0.9)
                    lum = 0.22 + 0.38 * np.sin(t * 10.0 + phase + wave)
                    if abs(x - cx) < arc_w * 0.9:
                        cv.plot(np.array([x], dtype=np.float32),
                                np.array([y], dtype=np.float32),
                                np.array([0.0], dtype=np.float32),
                                np.array([lum], dtype=np.float32),
                                np.array([(0.64 + wave * 0.04 + side * 0.1 + ctx.t * 0.02) % 1.0], dtype=np.float32))

        for j in range(12):
            ang = j / 11.0 * np.pi * 2.0 + phase * 0.8
            node_x = cx + np.cos(ang) * (arc_w * 0.56)
            node_y = cy + np.sin(ang * 1.6 + phase) * (arc_h * 0.42)
            lum = 0.45 + 0.25 * np.sin(phase + j)
            cv.plot(np.array([node_x], dtype=np.float32),
                    np.array([node_y], dtype=np.float32),
                    np.array([0.0], dtype=np.float32),
                    np.array([lum], dtype=np.float32),
                    np.array([(0.72 + j * 0.03) % 1.0], dtype=np.float32))

        add_brain_arc(-1.0, 0.2, 0.58)
        add_brain_arc(1.0, 1.8, 0.74)

        bar_values = [
            (ctx.bass, 0.82, 0.20),
            (ctx.mid, 0.67, 0.00),
            (ctx.treb, 0.52, 0.35),
            (ctx.vol, 0.92, 0.70),
        ]
        for side, (value, hue_base, dy) in zip((-1.0, 1.0, -1.0, 1.0), bar_values):
            base_x = cx + side * (arc_w * 0.98 + 10.0)
            h = 18 + int(22 * value)
            for i in range(h):
                y = cy - h // 2 + i + int(np.sin(phase * 2.0 + i * 0.6 + dy) * 1.5)
                x = base_x + np.sin(phase + i * 0.55 + dy) * 1.0
                lum = 0.2 + 0.55 * (i / max(1, h)) * (0.7 + value)
                cv.plot(np.array([x], dtype=np.float32),
                        np.array([y], dtype=np.float32),
                        np.array([0.0], dtype=np.float32),
                        np.array([lum], dtype=np.float32),
                        np.array([(hue_base + i * 0.018) % 1.0], dtype=np.float32))

        left = int(max(0, col0 - 4))
        right = int(min(ctx.cols - 1, col0 + total_width + 6))
        top = int(max(0, row0 - 2))
        bottom = int(min(ctx.rows - 1, row0 + total_height + 4))

        for x in range(left, right + 1):
            if x % 8 in (0, 1, 2):
                cv.plot(np.array([x], dtype=np.float32),
                        np.array([top], dtype=np.float32),
                        np.array([0.0], dtype=np.float32),
                        np.array([0.3 + 0.2 * np.sin(phase + x * 0.2)], dtype=np.float32),
                        np.array([(0.72 + (x * 0.017)) % 1.0], dtype=np.float32))
                cv.plot(np.array([x], dtype=np.float32),
                        np.array([bottom], dtype=np.float32),
                        np.array([0.0], dtype=np.float32),
                        np.array([0.3 + 0.2 * np.sin(phase + x * 0.2 + 2.0)], dtype=np.float32),
                        np.array([(0.72 + (x * 0.017)) % 1.0], dtype=np.float32))

        for y in range(top, bottom + 1):
            if y % 5 == 0:
                cv.plot(np.array([left], dtype=np.float32),
                        np.array([y], dtype=np.float32),
                        np.array([0.0], dtype=np.float32),
                        np.array([0.25 + 0.25 * np.sin(phase + y * 0.3)], dtype=np.float32),
                        np.array([(0.56 + y * 0.03) % 1.0], dtype=np.float32))
                cv.plot(np.array([right], dtype=np.float32),
                        np.array([y], dtype=np.float32),
                        np.array([0.0], dtype=np.float32),
                        np.array([0.25 + 0.25 * np.sin(phase + y * 0.3 + 1.3)], dtype=np.float32),
                        np.array([(0.56 + y * 0.03) % 1.0], dtype=np.float32))

        for scan in range(0, total_height, 3):
            y = row0 + scan + int(np.sin(phase * 2.0 + scan * 0.2) * 1.5)
            if 0 <= y < ctx.rows:
                for x in range(col0 - 2, col0 + total_width + 2):
                    if (x + scan) % 5 == 0:
                        cv.plot(np.array([x], dtype=np.float32),
                                np.array([y], dtype=np.float32),
                                np.array([0.0], dtype=np.float32),
                                np.array([0.2 + 0.3 * np.sin(phase + x * 0.13)], dtype=np.float32),
                                np.array([(0.92 + scan * 0.02) % 1.0], dtype=np.float32))

        levels = (
            (ctx.bass, 0.52),
            (ctx.mid, 0.82),
            (ctx.treb, 0.94),
            (ctx.vol, 0.72),
        )
        strip_width = min(total_width, max(0, ctx.cols - 4))
        strip_col = max(0, (ctx.cols - strip_width) // 2)
        segment_count = max(1, strip_width // 4)
        for row_start, reverse in ((row0 - len(levels) - 1, False),
                                   (row0 + total_height + 1, True)):
            if strip_width < 4:
                continue
            for band, (value, hue) in enumerate(levels):
                row = row_start + band
                if not 0 <= row < ctx.rows:
                    continue
                amount = int(round(np.clip(value, 0.0, 1.0) * segment_count))
                col = strip_col + strip_width - segment_count if reverse else strip_col
                cv.put_text(row, col, "." * segment_count, 0.18, hue)
                if amount:
                    active_col = col + segment_count - amount if reverse else col
                    cv.put_text(row, active_col, "#" * amount, 0.82,
                                (hue + phase * 0.025) % 1.0)

        led_row = row0 - 1
        if 0 <= led_row < ctx.rows:
            led_count = 4 if ctx.peak else 1 + int(np.clip(ctx.vol, 0.0, 1.0) * 3)
            led_hue = (0.91 + phase * 0.03) % 1.0
            cv.put_text(led_row, max(0, col0 - 3), "*" * led_count, 0.65, led_hue)
            cv.put_text(led_row, min(ctx.cols - led_count, col0 + total_width + 1),
                        "*" * led_count, 0.65, (0.52 + phase * 0.03) % 1.0)

        for char_index, char in enumerate(name):
            if char == " ":
                continue
            source = _FONT.get(char, _FONT["-"])
            rows = [source[index] for index in (0, 0, 1, 2, 2, 3, 4)]
            for row, line in enumerate(rows):
                pixels = [line[index] for index in (0, 0, 1, 2, 2)]
                for col, pixel in enumerate(pixels):
                    if pixel != "#":
                        continue
                    x0 = col0 + (char_index * 6 + col) * scale
                    y0 = row0 + row * scale
                    x1 = int(round(cx + (x0 - cx) * pulse_scale))
                    x2 = int(round(cx + (x0 + scale - cx) * pulse_scale))
                    y1 = int(round(cy + (y0 - cy) * pulse_scale))
                    y2 = int(round(cy + (y0 + scale - cy) * pulse_scale))
                    glyph = "#" * max(1, x2 - x1)
                    hue = (char_index * 0.09 + ctx.t * 0.035) % 1.0
                    for y in range(y1, max(y1 + 1, y2)):
                        cv.put_text(y, x1, glyph, 1.0, hue)
