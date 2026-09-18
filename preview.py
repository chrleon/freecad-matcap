#!/usr/bin/env python3
"""Viser en matcap på en produktform, uten å starte FreeCAD.

Rendrer en avrundet kasse med fas, omtrent som et frest aluminiumshus, og
shader den med matcapen alene. Det er den ærlige testen: en matcap på en
kule sier lite, for kula er nettopp det teksturen allerede er.

    python3 preview.py metal_steel
    python3 preview.py metal_steel --blast 0.05 --out /tmp/test.png

Kjører i ren Python, ingen avhengigheter. Et bilde tar noen sekunder.
"""

import argparse
import math
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
MATCAPS = os.path.join(HERE, "matcaps")


# ------------------------------------------------------------- PNG inn

def read_png(path):
    """Leser en 8-bits RGB- eller RGBA-PNG uten interlacing."""
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("ikke en PNG: %s" % path)

    pos = 8
    idat = bytearray()
    width = height = depth = colour = None
    while pos < len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        tag = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if tag == b"IHDR":
            width, height, depth, colour, _, _, interlace = struct.unpack(
                ">IIBBBBB", body)
            if depth != 8 or colour not in (2, 6) or interlace:
                raise ValueError("støtter bare 8-bits RGB/RGBA uten interlace")
        elif tag == b"IDAT":
            idat += body
        elif tag == b"IEND":
            break

    channels = 3 if colour == 2 else 4
    raw = zlib.decompress(bytes(idat))
    stride = width * channels

    out = bytearray(height * stride)
    prev = bytearray(stride)
    pos = 0
    for y in range(height):
        filt = raw[pos]
        pos += 1
        line = bytearray(raw[pos:pos + stride])
        pos += stride
        # PNG-filtrene. Uten dem blir bildet en skrå grøt.
        if filt == 1:
            for i in range(channels, stride):
                line[i] = (line[i] + line[i - channels]) & 0xFF
        elif filt == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif filt == 3:
            for i in range(stride):
                left = line[i - channels] if i >= channels else 0
                line[i] = (line[i] + ((left + prev[i]) >> 1)) & 0xFF
        elif filt == 4:
            for i in range(stride):
                a = line[i - channels] if i >= channels else 0
                b = prev[i]
                c = prev[i - channels] if i >= channels else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 0xFF
        elif filt != 0:
            raise ValueError("ukjent PNG-filter %d" % filt)
        out[y * stride:(y + 1) * stride] = line
        prev = line

    return width, height, channels, bytes(out)


def write_png(path, rows, width, height):
    raw = bytearray()
    for row in rows:
        raw.append(0)
        for (r, g, b) in row:
            raw += bytes((r, g, b))

    def chunk(tag, body):
        return (struct.pack(">I", len(body)) + tag + body
                + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF))

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height,
                                        8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(bytes(raw), 6))
           + chunk(b"IEND", b""))
    with open(path, "wb") as fh:
        fh.write(png)


class MatCap(object):
    def __init__(self, path):
        self.w, self.h, self.ch, self.px = read_png(path)

    def lookup(self, nx, ny):
        # Samme margin som shaderen: 0,49 og ikke 0,5, ellers treffer
        # oppslaget ytterkanten ved silhuetten.
        u = nx * 0.49 + 0.5
        v = 1.0 - (ny * 0.49 + 0.5)
        x = min(self.w - 1, max(0, int(u * self.w)))
        y = min(self.h - 1, max(0, int(v * self.h)))
        i = (y * self.w + x) * self.ch
        return (self.px[i] / 255.0, self.px[i + 1] / 255.0,
                self.px[i + 2] / 255.0)


# ------------------------------------------------------------ geometri

BOX = (1.55, 0.42, 1.05)   # halve mål
ROUND = 0.16               # hjørneradius
CHAMFER = 0.055            # fas langs toppkanten
SPHERE = 1.15

# Kassa er 3,1 enheter bred og forestiller et hus på omtrent 100 mm.
# Uten dette forholdet betyr ikke kornmålet noe fysisk.
UNIT_MM = 100.0 / (BOX[0] * 2.0)

SHAPE = "box"


def sphere(p):
    return math.sqrt(p[0] * p[0] + p[1] * p[1] + p[2] * p[2]) - SPHERE


def rounded_box(p):
    x, y, z = abs(p[0]) - BOX[0], abs(p[1]) - BOX[1], abs(p[2]) - BOX[2]
    dx, dy, dz = max(x, 0.0), max(y, 0.0), max(z, 0.0)
    outside = math.sqrt(dx * dx + dy * dy + dz * dz)
    inside = min(max(x, max(y, z)), 0.0)
    return outside + inside - ROUND


def sdf_chamfered(p):
    """Avrundet kasse med en fas rundt toppflaten.

    Fasen er det som gjør formen til et produkt og ikke en kloss: det er
    der lyset fanges i en tynn lys strek, og den streken er halve grunnen
    til at frest aluminium ser dyrt ut.
    """
    base = rounded_box(p)
    # Enkel fas: trekk fra en skråflate i hvert av de fire toppkantene.
    cut = -1e9
    for sx, sz in ((1.0, 0.0), (-1.0, 0.0), (0.0, 1.0), (0.0, -1.0)):
        reach = BOX[0] if sx else BOX[2]
        plane = ((p[0] * sx + p[2] * sz) + p[1]
                 - (reach + BOX[1] - CHAMFER)) * 0.7071
        cut = max(cut, plane)
    return max(base, cut)


def scene(p):
    return sphere(p) if SHAPE == "sphere" else sdf_chamfered(p)


def normal_at(p, eps=0.0015):
    dx = scene((p[0] + eps, p[1], p[2])) - scene((p[0] - eps, p[1], p[2]))
    dy = scene((p[0], p[1] + eps, p[2])) - scene((p[0], p[1] - eps, p[2]))
    dz = scene((p[0], p[1], p[2] + eps)) - scene((p[0], p[1], p[2] - eps))
    n = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
    return (dx / n, dy / n, dz / n)


# ---------------------------------------------------------------- støy

def hash3(x, y, z):
    return (math.sin(x * 12.9898 + y * 78.233 + z * 37.719)
            * 43758.5453) % 1.0


def vnoise3(x, y, z):
    ix, iy, iz = math.floor(x), math.floor(y), math.floor(z)
    fx, fy, fz = x - ix, y - iy, z - iz
    fx = fx * fx * (3 - 2 * fx)
    fy = fy * fy * (3 - 2 * fy)
    fz = fz * fz * (3 - 2 * fz)
    out = 0.0
    for dz in (0, 1):
        for dy in (0, 1):
            for dx in (0, 1):
                w = ((fx if dx else 1 - fx) * (fy if dy else 1 - fy)
                     * (fz if dz else 1 - fz))
                out += w * hash3(ix + dx, iy + dy, iz + dz)
    return out


def blast(p, n, amount, scale):
    """Samme forstyrrelse som shaderen: stigning projisert på flaten."""
    if amount <= 0.0:
        return n
    e = 0.35 / scale
    g = []
    for axis in range(3):
        a = list(p)
        b = list(p)
        a[axis] += e
        b[axis] -= e
        g.append((vnoise3(a[0] * scale, a[1] * scale, a[2] * scale)
                  - vnoise3(b[0] * scale, b[1] * scale, b[2] * scale))
                 / (2.0 * e) / scale)
    dot = sum(g[i] * n[i] for i in range(3))
    out = [n[i] - amount * (g[i] - n[i] * dot) for i in range(3)]
    length = math.sqrt(sum(c * c for c in out)) or 1.0
    return tuple(c / length for c in out)


# -------------------------------------------------------------- render

BACKGROUND = (0.95, 0.95, 0.95)


def render(matcap, width, height, amount, scale):
    cam = (2.5, 2.1, 3.4)
    target = (0.0, -0.05, 0.0)

    fwd = [target[i] - cam[i] for i in range(3)]
    fl = math.sqrt(sum(c * c for c in fwd))
    fwd = [c / fl for c in fwd]
    right = [fwd[2], 0.0, -fwd[0]]
    rl = math.sqrt(sum(c * c for c in right))
    right = [c / rl for c in right]
    # cross(fwd, right), ikke cross(right, fwd). Motsatt rekkefølge gir
    # en opp-vektor som peker ned, og da henter toppflaten farge fra
    # undersiden av matcapen. Bildet ser nesten riktig ut, bare underlig
    # flatt, som er den verste sorten feil.
    up = [fwd[1] * right[2] - fwd[2] * right[1],
          fwd[2] * right[0] - fwd[0] * right[2],
          fwd[0] * right[1] - fwd[1] * right[0]]

    aspect = width / float(height)
    rows = []
    for py in range(height):
        row = []
        sy = 1.0 - 2.0 * (py + 0.5) / height
        for px in range(width):
            sx = (2.0 * (px + 0.5) / width - 1.0) * aspect
            d = [fwd[i] * 1.9 + right[i] * sx + up[i] * sy for i in range(3)]
            dl = math.sqrt(sum(c * c for c in d))
            d = [c / dl for c in d]

            t = 0.0
            hit = False
            for _ in range(70):
                p = (cam[0] + d[0] * t, cam[1] + d[1] * t, cam[2] + d[2] * t)
                dist = scene(p)
                if dist < 0.0012:
                    hit = True
                    break
                t += dist
                if t > 12.0:
                    break

            if not hit:
                row.append(tuple(int(255 * c) for c in BACKGROUND))
                continue

            p = (cam[0] + d[0] * t, cam[1] + d[1] * t, cam[2] + d[2] * t)
            n = normal_at(p)
            n = blast(p, n, amount, scale)

            # Normalen til view-space, som gl_NormalMatrix gjør i shaderen.
            nx = n[0] * right[0] + n[1] * right[1] + n[2] * right[2]
            ny = n[0] * up[0] + n[1] * up[1] + n[2] * up[2]
            col = matcap.lookup(nx, ny)
            row.append(tuple(min(255, int(255 * c)) for c in col))
        rows.append(row)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name", help="navn på matcap, uten .png")
    ap.add_argument("--blast", type=float, default=0.0,
                    help="kornstørrelse i mm, 0 for glatt. Under omtrent "
                         "0,3 mm er kornet mindre enn en piksel her og "
                         "leses som en svak mykning, ikke som prikker.")
    ap.add_argument("--shape", choices=("box", "sphere"), default="box",
                    help="kule gjengir teksturen slik den er, kassa viser "
                         "hvordan den oppfører seg på ekte flater")
    ap.add_argument("--depth", type=float, default=0.16)
    ap.add_argument("--width", type=int, default=560)
    ap.add_argument("--height", type=int, default=360)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    # Pensjonerte teksturer ligger i extra/ og skal fortsatt kunne
    # forhåndsvises; det er ofte nettopp da man vil se på dem igjen.
    path = os.path.join(MATCAPS, args.name + ".png")
    if not os.path.exists(path):
        path = os.path.join(MATCAPS, "extra", args.name + ".png")
    if not os.path.exists(path):
        sys.exit("fant ikke %s.png, verken i matcaps/ eller matcaps/extra/"
                 % args.name)

    global SHAPE
    SHAPE = args.shape
    # Perioder per enhet: kornet er oppgitt i millimeter på emnet.
    scale = (UNIT_MM / args.blast) if args.blast > 0 else 1.0
    amount = args.depth if args.blast > 0 else 0.0

    rows = render(MatCap(path), args.width, args.height, amount, scale)
    out = args.out or os.path.join(HERE, "preview_%s.png" % args.name)
    write_png(out, rows, args.width, args.height)
    print("skrev", out)


if __name__ == "__main__":
    main()
