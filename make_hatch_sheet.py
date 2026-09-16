#!/usr/bin/env python3
"""Lager et referanseark for skravering som skal tegnes for hånd.

Arket viser de fire sonene shaderen bruker, i riktig rekkefølge og med
riktig tetthet. Tegn dem etter, fotografer eller skann, så kan strekene
dine erstatte de syntetiske.

Kjør:  python3 make_hatch_sheet.py
"""

import math
import os

from make_matcaps import SIZE, OUT, clamp, write_png

HERE = os.path.dirname(os.path.abspath(__file__))
WIDTH = 1400
HEIGHT = 600
PAPER = (0.96, 0.95, 0.92)
INK = (0.20, 0.20, 0.23)

# Samme grenser som shaderen bruker.
ZONES = [
    ("MORKEST", "tette streker, krysset", "dense"),
    ("NEST MORKEST", "samme strek, glissere", "sparse"),
    ("NEST LYSEST", "prikker", "dots"),
    ("LYSEST", "blankt", "blank"),
]

SPACING = 12.0     # piksler mellom strekene i ruta
ANGLE_A = 0.62     # radianer, samme som shaderen
ANGLE_B = -0.70


def hash1(x):
    return (math.sin(x * 127.1) * 43758.5453) % 1.0


def stroke_at(x, y, angle, spacing, thickness):
    dx, dy = math.cos(angle), math.sin(angle)
    t = (x * dx + y * dy) / spacing
    line = math.floor(t)
    jitter = hash1(line)
    width = thickness + 0.03 * jitter
    d = abs((t % 1.0) - 0.5)
    if d > width:
        return 0.0
    # Blyanten slipper opp underveis
    ax, ay = -dy, dx
    s = (x * ax + y * ay) / (spacing * 5.0)
    fade = 0.70 + 0.30 * hash1(math.floor(s) * 3.1 + line)
    return fade * (1.0 - d / max(width, 1e-6)) ** 0.4


def dot_at(x, y, spacing):
    cx, cy = math.floor(x / spacing), math.floor(y / spacing)
    fx, fy = (x / spacing) % 1.0, (y / spacing) % 1.0
    if hash1(cx * 7.3 + cy * 13.1) > 0.55:
        return 0.0
    ox = 0.25 + 0.5 * hash1(cx * 3.7 + cy * 9.2)
    oy = 0.25 + 0.5 * hash1(cx * 5.1 + cy * 2.6)
    d = math.hypot(fx - ox, fy - oy)
    r = 0.11
    return 1.0 if d < r else max(0.0, 1.0 - (d - r) / 0.06)


def zone_ink(kind, x, y):
    if kind == "dense":
        a = stroke_at(x, y, ANGLE_A, SPACING, 0.16)
        b = stroke_at(x, y, ANGLE_B, SPACING * 1.1, 0.16)
        return max(a, b)
    if kind == "sparse":
        return stroke_at(x, y, ANGLE_A, SPACING * 1.9, 0.13)
    if kind == "dots":
        return dot_at(x, y, SPACING * 1.25)
    return 0.0


def glyph_rows():
    """Bittelitt 5x7-skrift, nok til overskriftene."""
    font = {
        "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
        "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
        "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
        "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
        "G": ["01110", "10001", "10000", "10111", "10001", "10001", "01110"],
        "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
        "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
        "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
        "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
        "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
        "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
        "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
        "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
        "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
        "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
        "C": ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
        "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
        "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
        "J": ["00111", "00010", "00010", "00010", "00010", "10010", "01100"],
        "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
        "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
        "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
        "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
        "2": ["01110", "10001", "00001", "00110", "01000", "10000", "11111"],
        "3": ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
        "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
        "0": ["01110", "10011", "10101", "10101", "10101", "11001", "01110"],
        ".": ["00000", "00000", "00000", "00000", "00000", "01100", "01100"],
        " ": ["00000"] * 7,
    }
    return font


FONT = glyph_rows()


def draw_text(pixels, text, x0, y0, scale=3):
    for index, ch in enumerate(text.upper()):
        glyph = FONT.get(ch, FONT[" "])
        for gy, line in enumerate(glyph):
            for gx, bit in enumerate(line):
                if bit != "1":
                    continue
                for sy in range(scale):
                    for sx in range(scale):
                        px = x0 + (index * 6 + gx) * scale + sx
                        py = y0 + gy * scale + sy
                        if 0 <= py < HEIGHT and 0 <= px < WIDTH:
                            pixels[py][px] = tuple(
                                int(round(255 * c)) for c in INK)


def main():
    pixels = [[tuple(int(round(255 * c)) for c in PAPER)
               for _ in range(WIDTH)] for _ in range(HEIGHT)]

    margin = 60
    box = 280
    gap = 40
    top = 250

    for i, (title, _desc, kind) in enumerate(ZONES):
        x0 = margin + i * (box + gap)
        for y in range(top, top + box):
            for x in range(x0, x0 + box):
                # ramme
                on_edge = (x in (x0, x0 + box - 1)
                           or y in (top, top + box - 1))
                if on_edge:
                    pixels[y][x] = (90, 90, 96)
                    continue
                ink = clamp(zone_ink(kind, x - x0, y - top))
                if ink <= 0.0:
                    continue
                pixels[y][x] = tuple(
                    int(round(255 * (PAPER[c] + (INK[c] - PAPER[c]) * ink)))
                    for c in range(3))
        draw_text(pixels, str(i + 1) + " " + title, x0, top - 34, 2)

    draw_text(pixels, "SKRAVERING FIRE TRINN", margin, 60, 5)
    draw_text(pixels, "TEGN HVER RUTE 10 GANGER 10 CM MED SAMME BLYANT",
              margin, 130, 2)
    draw_text(pixels, "LA STREKENE GAA UT OVER KANTEN", margin, 165, 2)
    draw_text(pixels, "FOTOGRAFER FLATT OG JEVNT BELYST", margin, 200, 2)

    path = os.path.join(HERE, "hatch_reference.png")
    write_png(path, pixels, None) if False else _write(path, pixels)
    print("skrev", path)


def _write(path, pixels):
    """write_png er kvadratisk; her trenger vi et rektangel."""
    import struct
    import zlib
    raw = bytearray()
    for row in pixels:
        raw.append(0)
        for (r, g, b) in row:
            raw += bytes((r, g, b))

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", WIDTH, HEIGHT,
                                        8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
           + chunk(b"IEND", b""))
    with open(path, "wb") as fh:
        fh.write(png)


if __name__ == "__main__":
    main()
