#!/usr/bin/env python3
"""Henter Blenders matcaps og konverterer dem til PNG.

Blender leverer matcapene sine som lineær EXR. Coin3D leser ikke EXR, så
de må konverteres, og fargene må gjennom en sRGB-transformasjon. Vi bruker
Blender selv til jobben, i bakgrunnsmodus.

Matcapene er CC0, se license.txt i Blenders egen mappe.

Kjør:  python3 import_blender_matcaps.py
"""

import glob
import os
import subprocess
import sys

BLENDER = "/Applications/Blender.app/Contents/MacOS/Blender"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "matcaps")

# check_* er teknisk debugmateriale for å inspisere normaler og
# refleksjoner, ikke materialer. brush_thumbnail_preview er UI-grafikk.
SKIP_PREFIXES = ("check_", "brush_thumbnail")

# Vi henter bare de tre familiene som er nyttige til maskindeler: metall,
# leire og hard surface. Sett FAMILIES til None for å hente alt.
FAMILIES = ("metal", "fullmetal", "clay", "hard_surface")

# Blenders navn -> vårt navn. Alt som ikke står her beholder sitt eget navn,
# med "bl_" foran så det er tydelig hvor det kommer fra.
RENAME = {
    "basic_bright": "bl_basic_bright",
    "basic_dark": "bl_basic_dark",
    "basic_grey": "bl_basic_grey",
    "basic_side": "bl_basic_side",
    "ceramic_dark": "bl_ceramic_dark",
    "ceramic_lightbulb": "bl_ceramic_light",
    "clay_brown": "bl_clay_brown",
    "clay_green": "bl_clay_green",
    "clay_studio": "bl_clay_studio",
    "clay_warm": "bl_clay_warm",
    "fullmetal": "bl_metal_full",
    "hard_surface_grey": "bl_hardsurface_grey",
    "hard_surface_red": "bl_hardsurface_red",
    "metal_bronze": "bl_metal_bronze",
    "metal_carpaint": "bl_metal_carpaint",
    "pearl": "bl_pearl",
    "red_wax": "bl_red_wax",
    "resin": "bl_resin",
    "toon_dark": "bl_toon_dark",
    "toon_light": "bl_toon_light",
}


def find_source_dir():
    pattern = os.path.join(
        "/Applications/Blender.app/Contents/Resources",
        "*", "datafiles", "studiolights", "matcap")
    hits = sorted(glob.glob(pattern))
    return hits[-1] if hits else None


CONVERT = r'''
import bpy, os, sys
args = sys.argv[sys.argv.index("--") + 1:]
out_dir = args[0]
pairs = [a.split("::") for a in args[1:]]

scene = bpy.context.scene
# Standard, ikke Filmic eller AgX: matcapene er allerede ferdig "gradet",
# en filmisk kurve ville vasket ut kontrasten.
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "None"
scene.view_settings.exposure = 0.0
scene.view_settings.gamma = 1.0
scene.display_settings.display_device = "sRGB"
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGB"
scene.render.image_settings.color_depth = "8"

for src, name in pairs:
    img = bpy.data.images.load(src)
    dst = os.path.join(out_dir, name + ".png")
    img.file_format = "PNG"
    img.save_render(filepath=dst, scene=scene)
    print("KONVERTERT", dst)
    bpy.data.images.remove(img)
'''


def main():
    src_dir = find_source_dir()
    if not src_dir:
        sys.exit("Fant ikke Blenders matcap-mappe")
    if not os.path.exists(BLENDER):
        sys.exit("Fant ikke Blender på %s" % BLENDER)
    os.makedirs(OUT, exist_ok=True)

    pairs = []
    for f in sorted(os.listdir(src_dir)):
        if not f.endswith(".exr"):
            continue
        stem = f[:-4]
        if stem.startswith(SKIP_PREFIXES):
            continue
        if FAMILIES and not stem.startswith(FAMILIES):
            continue
        pairs.append("%s::%s" % (os.path.join(src_dir, f),
                                 RENAME.get(stem, "bl_" + stem)))

    print("Henter %d matcaps fra %s" % (len(pairs), src_dir))
    script = os.path.join(HERE, "_convert_tmp.py")
    with open(script, "w") as fh:
        fh.write(CONVERT)
    try:
        res = subprocess.run(
            [BLENDER, "--background", "--factory-startup",
             "--python", script, "--", OUT] + pairs,
            capture_output=True, text=True)
    finally:
        os.remove(script)

    done = [l for l in res.stdout.splitlines() if l.startswith("KONVERTERT")]
    for l in done:
        print(l)
    if not done:
        print(res.stdout[-3000:])
        print(res.stderr[-3000:])
        sys.exit("Ingen filer ble konvertert")
    print("Ferdig: %d filer i %s" % (len(done), OUT))


if __name__ == "__main__":
    main()
