#!/usr/bin/env python3
"""Skriver MatCap-materialene som FreeCAD-materialkort.

Hvorfor kort og ikke bare egenskaper paa objektet: et materiale satt
direkte paa ShapeMaterial overlever ikke lagring. FreeCAD lagrer bare en
UUID-referanse, og finner den ingen match i et bibliotek, faller
materialet tilbake til Default naar fila aapnes igjen. Det er maalt, ikke
antatt.

Kortene faar Disney-modellen, som er Principled BSDF under et annet navn.
Da kan bade MatCap, PbrView og Render-arbeidsbenken lese det samme
materialet.

Kjoer:  python3 make_material_cards.py
"""

import os
import uuid as uuidlib

# Fast navnerom, saa UUID-ene blir de samme hver gang skriptet kjoeres.
# Endrer de seg, mister alle lagrede dokumenter materialet sitt.
NAVNEROM = uuidlib.UUID("6f2a1c74-9b3e-5d81-a4f6-2e7c9b5d31a0")

BASIC_RENDERING = "f006c7e4-35b7-43d5-bbf9-c5d572309e6e"
RENDER_DISNEY = "f8723572-4470-4c39-a749-6d3b71358a5b"

# navn: (grunnfarge, metallverdi, ruhet)
# Tallene er de samme som matcap-teksturene ble generert fra.
MATERIALER = {
    "metal_steel":  ((0.70, 0.72, 0.75), 1.00, 0.30),
    "metal_dark":   ((0.44, 0.45, 0.48), 1.00, 0.22),
    "clay_light":   ((0.80, 0.78, 0.75), 0.00, 0.90),
    "clay_warm":    ((0.78, 0.68, 0.58), 0.00, 0.90),
    "plast_grey":   ((0.74, 0.75, 0.77), 0.05, 0.55),
    "plast_cream":  ((0.91, 0.87, 0.78), 0.00, 0.65),
    # Fra Blender. Ingen oppskrift aa hente tall fra, lest av teksturen.
    "bl_metal_full":  ((0.72, 0.70, 0.71), 1.00, 0.18),
    "bl_clay_studio": ((0.82, 0.82, 0.82), 0.00, 0.85),
    # Trinnvise. Ingen fysisk ekvivalent; gjengis som matt maling.
    "toon_paper": ((0.88, 0.87, 0.84), 0.00, 0.80),
    "toon_sky":   ((0.62, 0.72, 0.84), 0.00, 0.80),
    "toon_clay":  ((0.80, 0.60, 0.46), 0.00, 0.80),
}


def material_uuid(navn):
    return str(uuidlib.uuid5(NAVNEROM, navn))


def farge(c, a=1.0):
    return "(%.4f, %.4f, %.4f, %.4f)" % (c[0], c[1], c[2], a)


def kort(navn, base, metallisk, ruhet):
    # Shininess i den gamle modellen er omtrent det motsatte av ruhet.
    # Den brukes av FreeCADs egen visning, saa den boer stemme omtrent.
    shininess = max(0.0, min(1.0, 1.0 - ruhet))
    spekulaer = base if metallisk > 0.5 else (0.9, 0.9, 0.9)
    return """# Skrevet av make_material_cards.py i freecad-matcap
General:
  UUID: "%s"
  Author: "Christian Leon"
  License: "MIT"
  Name: "MatCap %s"
  Description: "Matcap-materiale %s. Samme tall som teksturen ble laget fra."
AppearanceModels:
  BasicRendering:
    UUID: '%s'
    AmbientColor: "%s"
    DiffuseColor: "%s"
    EmissiveColor: "(0.0000, 0.0000, 0.0000, 1.0)"
    Shininess: "%.4f"
    SpecularColor: "%s"
    Transparency: "0.0"
  RenderDisney:
    UUID: '%s'
    Render.Disney.BaseColor: "%s"
    Render.Disney.Metallic: "%.4f"
    Render.Disney.Roughness: "%.4f"
    Render.Disney.Specular: "0.5"
    Render.Disney.SpecularTint: "0.0"
    Render.Disney.Anisotropic: "0.0"
    Render.Disney.Sheen: "0.0"
    Render.Disney.SheenTint: "0.0"
    Render.Disney.ClearCoat: "0.0"
    Render.Disney.ClearCoatGloss: "0.0"
    Render.Disney.Subsurface: "0.0"
""" % (material_uuid(navn), navn, navn,
       BASIC_RENDERING,
       farge(tuple(c * 0.35 for c in base)),
       farge(base),
       shininess,
       farge(spekulaer),
       RENDER_DISNEY,
       farge(base), metallisk, ruhet)


def user_material_dir():
    """Brukerens materialmappe. FreeCAD 1.1 versjonerer den."""
    base = os.path.expanduser("~/Library/Application Support/FreeCAD")
    for versjon in ("v1-1", ""):
        sti = os.path.join(base, versjon, "Material") if versjon \
            else os.path.join(base, "Material")
        if os.path.isdir(sti):
            return sti
    return os.path.join(base, "Material")


def main():
    mappe = os.path.join(user_material_dir(), "MatCap")
    os.makedirs(mappe, exist_ok=True)
    for navn, (base, met, rgh) in sorted(MATERIALER.items()):
        sti = os.path.join(mappe, "MatCap_%s.FCMat" % navn)
        with open(sti, "w") as fh:
            fh.write(kort(navn, base, met, rgh))
        print("skrev", os.path.basename(sti), material_uuid(navn))
    print("\n%d kort i %s" % (len(MATERIALER), mappe))
    print("Start FreeCAD paa nytt, eller kall MaterialManager().refresh()")


if __name__ == "__main__":
    main()
