# -*- coding: utf-8 -*-
"""Måler at overflatemønstrene faktisk har størrelsen de heter.

Metoden: en kube på nøyaktig 10 mm, sett rett forfra, rendret til fil.
Kubens høyde i piksler gir målestokken, og antall lysheteopper nedover en
kolonne gir antall perioder. Da er perioden i millimeter kjent.

Må kjøres i FreeCAD med GUI, siden den rendrer et bilde.

    exec(open("/Users/ch/dev/freecad/matcap/verify_scale.py").read())
"""

import io
import os

import FreeCAD
import FreeCADGui as Gui
import Part
from PySide import QtGui as QtG

CUBE_MM = 10.0
IMAGE_PX = 900
TMP = os.path.join("/tmp", "matcap_verify.png")


def load_macro():
    path = os.path.join(FreeCAD.getUserMacroDir(True), "MatCap.FCMacro")
    ns = {"__file__": path, "__name__": "verify"}
    exec(io.open(path, encoding="utf-8").read(), ns)
    return ns


def make_cube():
    name = "MatCapVerify"
    if name in FreeCAD.listDocuments():
        FreeCAD.closeDocument(name)
    doc = FreeCAD.newDocument(name)
    obj = doc.addObject("Part::Feature", "Kube")
    obj.Shape = Part.makeBox(CUBE_MM, CUBE_MM, CUBE_MM)
    doc.recompute()
    obj.ViewObject.DisplayMode = "Shaded"
    return obj


def measure(ns, obj, finish, scale, amount=0.30):
    ns["apply_to"](obj.ViewObject,
                   os.path.join(ns["MATCAP_DIR"], "print_pla_grey.png"),
                   0.0, None, 1.0, finish, amount, scale)
    view = Gui.activeDocument().activeView()
    view.viewFront()
    view.fitAll()
    view.saveImage(TMP, IMAGE_PX, IMAGE_PX, "Current")

    img = QtG.QImage(TMP)
    w, h = img.width(), img.height()
    background = QtG.QColor(img.pixel(2, 2)).getRgb()[:3]
    mid = w // 2
    rows = [y for y in range(h)
            if QtG.QColor(img.pixel(mid, y)).getRgb()[:3] != background]
    if not rows:
        return None
    top, bottom = min(rows), max(rows)
    px_per_mm = (bottom - top + 1) / CUBE_MM

    # Flere kolonner, og median til slutt. En enkelt kolonne kan treffe et
    # uheldig sted i støyen og gi et tall som ikke er representativt.
    counts = []
    for col in range(mid - 60, mid + 61, 20):
        lum = []
        for y in range(top + 3, bottom - 2):
            r, g, b = QtG.QColor(img.pixel(col, y)).getRgb()[:3]
            lum.append(0.299 * r + 0.587 * g + 0.114 * b)
        peaks = 0
        for i in range(1, len(lum) - 1):
            if (lum[i] > lum[i - 1] and lum[i] >= lum[i + 1]
                    and lum[i] - min(lum[max(0, i - 3):i + 4]) > 1.0):
                peaks += 1
        counts.append(peaks)
    counts.sort()
    n = counts[len(counts) // 2]
    return (CUBE_MM / n if n else 0.0), px_per_mm, n


def main():
    ns = load_macro()
    obj = make_cube()
    print("%-22s %10s %10s %8s" % ("overflate", "nominelt", "målt", "px/mm"))
    for name, mode, amount, scale in ns["FINISHES"]:
        if mode == 0:
            continue
        result = measure(ns, obj, mode, scale, amount)
        if result is None:
            print("%-22s  kunne ikke måles" % name)
            continue
        period, px_per_mm, n = result
        # Under omtrent tre piksler per periode smelter toppene sammen, og
        # målingen blir like upålitelig som bildet selv ser ut.
        flag = "  (under oppløsningen)" if px_per_mm / (1.0 / scale) < 3.0 \
            else ""
        print("%-22s %8.3f mm %8.3f mm %8.1f%s"
              % (name, 1.0 / scale, period, px_per_mm, flag))


if __name__ == "__main__":
    main()
