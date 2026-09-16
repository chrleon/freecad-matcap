#!/usr/bin/env python3
"""Lager settet med matcaps: metall, leire og lys plast.

Blenders egne matcaps er laget for sculpting, der man vil se formen uten at
materialet stjeler oppmerksomhet. Derfor er de fleste av dem med vilje
flate og mørke, og til presentasjonsbilder av CAD faller de igjennom.
bl_metal_bronze er praktisk talt sort, og hard surface har knapt form i
det hele tatt. To av dem duger, resten er byttet ut med disse.

Kjør:  python3 make_matcaps.py
"""

import math
import os
import struct
import zlib

SIZE = 512
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "matcaps")


# --------------------------------------------------------------- PNG

def write_png(path, rows, size):
    raw = bytearray()
    for y in range(size):
        raw.append(0)
        for (r, g, b) in rows[y]:
            raw += bytes((r, g, b))

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
           + chunk(b"IEND", b""))
    with open(path, "wb") as fh:
        fh.write(png)


# ------------------------------------------------------------ verktøy

def clamp(v, lo=0.0, hi=1.0):
    return lo if v < lo else hi if v > hi else v


def mix(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def smoothstep(t):
    t = clamp(t)
    return t * t * (3.0 - 2.0 * t)


def normalize(v):
    n = math.sqrt(sum(c * c for c in v))
    return tuple(c / n for c in v)


# Utenfor kula. Shaderen slår aldri opp lenger ut enn radius 0,98, så alt
# her er bare for øyet. En smal brem med kantfargen hindrer at filtreringen
# drar mørke inn i silhuetten; utenfor den går det mot bakgrunnsfargen, så
# teksturen ser ut som en kule og ikke som en gradient i miniatyrene.
MARGIN = 0.06
OUTSIDE = (0.05, 0.05, 0.06)


def outside_fade(radius):
    return smoothstep((radius - 1.0) / MARGIN)


# Tre lys: hovedlys oppe til venstre, fyll fra høyre, svak bounce nedenfra.
LIGHTS = [(normalize((-0.42, 0.62, 0.66)), 1.00),
          (normalize((0.68, 0.26, 0.69)), 0.40),
          (normalize((0.05, -0.80, 0.60)), 0.22)]


def light_terms(nx, ny, nz):
    diffuse = 0.0
    wrapped = 0.0
    for (lx, ly, lz), weight in LIGHTS:
        ndl = nx * lx + ny * ly + nz * lz
        if ndl > 0.0:
            diffuse += ndl * weight
        wrapped += clamp((ndl + 0.45) / 1.45) * weight
    return diffuse, wrapped


def light_maxima(samples=96):
    """Største verdi de to lysleddene faktisk når over kula.

    Gjettede normaliseringstall er grunnen til at to tidligere forsøk ble
    feil: ett delte på for lite og klipte hele oversiden til én farge, det
    neste delte på for mye og ga en hvit plast som kom ut grå. Her måles
    det i stedet, og da stemmer det for enhver lysoppstilling.
    """
    top_diffuse = 0.0
    top_wrapped = 0.0
    for j in range(samples):
        ny = 1.0 - 2.0 * (j + 0.5) / samples
        for i in range(samples):
            nx = 2.0 * (i + 0.5) / samples - 1.0
            rr = nx * nx + ny * ny
            if rr >= 1.0:
                continue
            d, w = light_terms(nx, ny, math.sqrt(1.0 - rr))
            top_diffuse = max(top_diffuse, d)
            top_wrapped = max(top_wrapped, w)
    return top_diffuse, top_wrapped


MAX_DIFFUSE, MAX_WRAPPED = light_maxima()


def environment(reflected, sky, horizon, ground, band=0.35):
    """Studiomiljø: himmel over, bred softbox-stripe, gulv under.

    En smal, hard horisont gir CD-plate. Vi vil ha softbox, altså en bred
    stripe med myk overgang og et gulv som bouncer i stedet for å være
    svart.
    """
    y = clamp(reflected[1], -1.0, 1.0)
    far = sky if y >= 0 else ground
    t = abs(y) / band
    if t < 1.0:
        return mix(horizon, far, smoothstep(t) * 0.55)
    near = mix(horizon, far, 0.55)
    return mix(near, far, smoothstep((abs(y) - band) / (1.0 - band)))


def render(base, sky, horizon, ground, metallic, roughness,
           spec_power, spec_strength, wrap=0.0, rim=0.0, gamma=1.06):
    rows = []
    for py in range(SIZE):
        row = []
        ny = 1.0 - 2.0 * (py + 0.5) / SIZE
        for px in range(SIZE):
            nx = 2.0 * (px + 0.5) / SIZE - 1.0
            rr = nx * nx + ny * ny
            fade = 0.0
            if rr >= 1.0:
                # Utenfor kula projiserer vi inn på kanten. En svart flate
                # helt inntil silhuetten ville blandet seg inn via
                # filtreringen og gitt en mørk ring rundt hele modellen.
                radius = math.sqrt(rr)
                fade = outside_fade(radius)
                inv = 0.9995 / radius
                nx, ny = nx * inv, ny * inv
                rr = nx * nx + ny * ny
            nz = math.sqrt(max(0.0, 1.0 - rr))

            spec = 0.0
            for (lx, ly, lz), weight in LIGHTS:
                hx, hy, hz = lx, ly, lz + 1.0
                hl = math.sqrt(hx * hx + hy * hy + hz * hz)
                ndh = clamp((nx * hx + ny * hy + nz * hz) / hl)
                spec += (ndh ** spec_power) * weight

            # Wrapped diffuse: lyset fortsetter litt forbi terminatoren.
            # Slik ser plast ut, fordi den sprer lys under overflaten.
            diffuse, wrapped = light_terms(nx, ny, nz)
            diffuse = clamp(diffuse / MAX_DIFFUSE)
            wrapped = clamp(wrapped / MAX_WRAPPED)
            light = diffuse * (1.0 - wrap) + wrapped * wrap

            d = 2.0 * nz
            env = environment((d * nx, d * ny, d * nz - 1.0),
                              sky, horizon, ground)
            average = tuple((sky[i] + horizon[i] + ground[i]) / 3.0
                            for i in range(3))
            env = mix(env, average, clamp(roughness))

            fresnel = (1.0 - nz) ** 4.0
            rim_term = (1.0 - nz) ** 3.0

            col = []
            for i in range(3):
                dielectric = base[i] * (0.14 + 0.92 * light)
                metal = env[i] * base[i] * (0.55 + 0.45 * light)
                c = dielectric + (metal - dielectric) * metallic
                c += env[i] * fresnel * (0.30 + 0.5 * metallic)
                c += spec * spec_strength
                c += rim * rim_term * (0.45 * base[i] + 0.30)
                col.append(clamp(c ** (1.0 / gamma)))
            if fade:
                col = mix(col, OUTSIDE, fade)
            row.append(tuple(int(round(255 * clamp(c))) for c in col))
        rows.append(row)
    return rows


# ---------------------------------------------------------------- toon

# Nøkkellyset for de trinnvise materialene. Oppe til venstre, litt mot
# betrakteren, som i en tegning.
KEY = normalize((-0.40, 0.55, 0.73))


def key_light_samples(samples=160):
    """Alle lysverdiene nøkkellyset gir over kula, sortert.

    Brukes til å legge tersklene etter areal i stedet for etter verdi.
    Vi ser bare den fremre halvkula, og nøkkellyset peker delvis mot oss,
    så verdiene klumper seg i det lyse. Fordeler man tersklene jevnt over
    tallområdet, havner tre av fire trinn oppå hverandre og materialet ser
    ensfarget ut. To forsøk gikk i den fella før dette.
    """
    values = []
    for j in range(samples):
        ny = 1.0 - 2.0 * (j + 0.5) / samples
        for i in range(samples):
            nx = 2.0 * (i + 0.5) / samples - 1.0
            rr = nx * nx + ny * ny
            if rr >= 1.0:
                continue
            nz = math.sqrt(1.0 - rr)
            values.append(0.5 + 0.5 * (nx * KEY[0] + ny * KEY[1]
                                       + nz * KEY[2]))
    values.sort()
    return values


KEY_VALUES = key_light_samples()


def area_threshold(fraction):
    """Lysverdien der den gitte andelen av kula er mørkere."""
    index = int(clamp(fraction) * (len(KEY_VALUES) - 1))
    return KEY_VALUES[index]

def render_toon(levels, thresholds, blur=0.06, rim=None, rim_at=0.86,
                rim_blur=0.05, spec=None, spec_power=200, spec_at=0.55):
    """Flate fargefelt med tydelige skiller, i stedet for en gradient.

    En matcap er en oppslagstabell, og ingenting krever at den er glatt.
    Legger vi inn trinn, får vi rene terminatorlinjer uten å regne dem ut,
    og de holder seg like rene uansett hvor tett geometrien er tessellert.

    Hvert trinn har sin egen farge, ikke bare sin egen lyshet. Skyggene går
    kjøligere og mer mettede, lysene varmere og blassere. Det er det som
    skiller håndmalt fra en modell med kontrasten skrudd opp.

    thresholds er andeler av kulas areal, ikke lysverdier. 0,25 betyr at
    det mørkeste trinnet dekker en fjerdedel av flaten. Blur oppgis på
    samme måte, slik at en myk kant er like myk uansett hvor i spennet
    trinnet ligger.
    """
    cuts = [area_threshold(f) for f in thresholds]
    spans = [max(1e-4, area_threshold(min(1.0, f + blur))
                 - area_threshold(max(0.0, f - blur)))
             for f in thresholds]

    rows = []
    for py in range(SIZE):
        row = []
        ny = 1.0 - 2.0 * (py + 0.5) / SIZE
        for px in range(SIZE):
            nx = 2.0 * (px + 0.5) / SIZE - 1.0
            rr = nx * nx + ny * ny
            fade = 0.0
            if rr >= 1.0:
                radius = math.sqrt(rr)
                fade = outside_fade(radius)
                inv = 0.9995 / radius
                nx, ny = nx * inv, ny * inv
                rr = nx * nx + ny * ny
            nz = math.sqrt(max(0.0, 1.0 - rr))

            # Ett nøkkellys, ikke tre. Med flere lys krysser terminatorene
            # hverandre, trinnene blir uryddige flekker, og bunnlyset
            # spiser opp det mørkeste trinnet. Her legger bandene seg som
            # rene buer, forskjøvet mot lyset.
            #
            # (ndl + 1) / 2 og ikke clamp(ndl): da fordeler de fire
            # trinnene seg over hele kula i stedet for å klumpe seg på
            # den opplyste halvdelen.
            ndl = nx * KEY[0] + ny * KEY[1] + nz * KEY[2]
            light = 0.5 + 0.5 * ndl

            colour = levels[0]
            for i, threshold in enumerate(cuts):
                # Med blur = 0 blir kanten hard som en tegneserie. Litt
                # blur gir den myke, malte kanten uten at trinnet går i
                # oppløsning.
                span = spans[i]
                t = smoothstep((light - threshold) / span + 0.5)
                colour = mix(colour, levels[i + 1], t)

            if rim is not None:
                edge = 1.0 - nz
                colour = mix(colour, rim,
                             smoothstep((edge - rim_at) / rim_blur))

            if spec is not None:
                hx, hy, hz = KEY[0], KEY[1], KEY[2] + 1.0
                hl = math.sqrt(hx * hx + hy * hy + hz * hz)
                ndh = clamp((nx * hx + ny * hy + nz * hz) / hl)
                # Høylyset er også et trinn, ikke en gradient.
                colour = mix(colour, spec,
                             smoothstep((ndh ** spec_power - spec_at) / 0.25))

            if fade:
                colour = mix(colour, OUTSIDE, fade)
            row.append(tuple(int(round(255 * clamp(c))) for c in colour))
        rows.append(row)
    return rows


# Fire trinn. Skyggen dekker en knapp fjerdedel, mellomtonen mest, og
# høylyset en liten flekk, slik en tegner ville fordelt dem.
TOON_CUTS = [0.24, 0.58, 0.88]
TOON_BLUR = 0.05

TOON = {
    # Skyggene kjøligere og mer mettede, lysene varmere og blassere.
    "toon_paper": dict(
        levels=[(0.48, 0.48, 0.58), (0.70, 0.68, 0.71),
                (0.88, 0.86, 0.83), (0.98, 0.97, 0.93)],
        thresholds=TOON_CUTS, blur=TOON_BLUR,
        rim=(1.0, 0.99, 0.94), spec=(1.0, 1.0, 0.98)),

    "toon_sky": dict(
        levels=[(0.26, 0.34, 0.52), (0.44, 0.56, 0.72),
                (0.65, 0.77, 0.88), (0.87, 0.94, 0.98)],
        thresholds=TOON_CUTS, blur=TOON_BLUR,
        rim=(0.96, 0.98, 1.0), spec=(1.0, 1.0, 1.0)),

    "toon_clay": dict(
        levels=[(0.40, 0.28, 0.33), (0.66, 0.43, 0.37),
                (0.85, 0.63, 0.48), (0.96, 0.84, 0.69)],
        thresholds=TOON_CUTS, blur=TOON_BLUR,
        rim=(1.0, 0.92, 0.78), spec=(1.0, 0.97, 0.90)),

    "toon_moss": dict(
        levels=[(0.22, 0.31, 0.30), (0.37, 0.50, 0.38),
                (0.58, 0.70, 0.47), (0.81, 0.88, 0.65)],
        thresholds=TOON_CUTS, blur=TOON_BLUR,
        rim=(0.94, 0.99, 0.86), spec=(1.0, 1.0, 0.94)),
}


# ------------------------------------------------------------- presets

STUDIO = dict(sky=(0.72, 0.77, 0.88),
              horizon=(0.98, 0.98, 0.97),
              ground=(0.32, 0.32, 0.35))

SOFT = dict(sky=(0.80, 0.83, 0.88),
            horizon=(0.94, 0.94, 0.93),
            ground=(0.42, 0.42, 0.44))

PRESETS = {
    # metall
    "metal_steel": dict(base=(0.70, 0.72, 0.75), metallic=1.0, roughness=0.30,
                        spec_power=90, spec_strength=0.40, **STUDIO),
    "metal_alu": dict(base=(0.78, 0.79, 0.80), metallic=1.0, roughness=0.45,
                      spec_power=45, spec_strength=0.28, **STUDIO),
    "metal_dark": dict(base=(0.44, 0.45, 0.48), metallic=1.0, roughness=0.22,
                       spec_power=120, spec_strength=0.45, **STUDIO),

    # leire
    "clay_light": dict(base=(0.80, 0.78, 0.75), metallic=0.0, roughness=0.9,
                       spec_power=16, spec_strength=0.05, wrap=0.35, **SOFT),
    "clay_warm": dict(base=(0.78, 0.68, 0.58), metallic=0.0, roughness=0.9,
                      spec_power=16, spec_strength=0.05, wrap=0.35, **SOFT),

    # lys plast
    "plast_white": dict(base=(0.90, 0.90, 0.89), metallic=0.0, roughness=0.6,
                        spec_power=34, spec_strength=0.16, wrap=0.45,
                        rim=0.22, **SOFT),
    "plast_grey": dict(base=(0.74, 0.75, 0.77), metallic=0.05, roughness=0.55,
                       spec_power=40, spec_strength=0.20, wrap=0.40,
                       rim=0.18, **SOFT),
    "plast_cream": dict(base=(0.91, 0.87, 0.78), metallic=0.0, roughness=0.65,
                        spec_power=30, spec_strength=0.15, wrap=0.45,
                        rim=0.26, **SOFT),

    # printet plast. Mer spredning og tydeligere kantglød enn støpt plast,
    # fordi lagene slipper gjennom lys i kantene. Uten det ser printet PLA
    # ut som gips.
    "print_pla_grey": dict(base=(0.70, 0.70, 0.71), metallic=0.0,
                           roughness=0.85, spec_power=22, spec_strength=0.10,
                           wrap=0.55, rim=0.30, **SOFT),
}


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, kwargs in sorted(PRESETS.items()):
        path = os.path.join(OUT, name + ".png")
        write_png(path, render(**kwargs), SIZE)
        print("skrev", path)
    for name, kwargs in sorted(TOON.items()):
        path = os.path.join(OUT, name + ".png")
        write_png(path, render_toon(**kwargs), SIZE)
        print("skrev", path)


if __name__ == "__main__":
    main()
