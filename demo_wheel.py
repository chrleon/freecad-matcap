# -*- coding: utf-8 -*-
"""Bygger et riflet ratt som testobjekt for MatCap.

Ekte CAD-geometri, ikke mesh: analytiske flater og skarpe kanter, slik at
shaderen har noe å jobbe med. Målene er tatt fra M4-rattet, Ø30 x 8,6 mm.

Kjør i FreeCAD:
    exec(open("/Users/ch/dev/freecad/matcap/demo_wheel.py").read())
"""

import math
import time

import FreeCAD
import Part
from FreeCAD import Vector, Rotation, Placement

# ------------------------------------------------------------ parametre

R = 15.0          # ytre radius
H = 8.6           # høyde
N_LOBES = 10      # antall kuler rundt kanten
SCALLOP_R = 1.9   # radius på hakkene mellom dem
RIM_W = 1.9       # bredde på den hevede kanten
RECESS = 1.7      # hvor dypt midtpartiet ligger
N_SPOKES = 5
POCKET_R = 4.5    # radius på lommene mellom eikene
POCKET_D = 8.4    # avstand fra senter til lommesenter
HUB_R = 4.1
BORE_R = 2.05     # klaring for M4
CBORE_R = 3.6     # senkning på toppen
CBORE_D = 2.3
KNURL_DEPTH = 0.35
KNURL_ANGLE = 35.0
FILLET = 0.45


def knurl_tools():
    """Sporene i riflingen, som en liste med tynne kasser.

    Riflingen sitter på annenhver kule. Hvert spor er en tynn kasse lagt i
    tangentplanet, vippet 35 grader, og speilet så vi får rutemønster.
    """
    tools = []
    step = 360.0 / N_LOBES
    length = 14.0
    thick = 0.42
    depth = 1.2

    for lobe in range(0, N_LOBES, 2):
        theta = lobe * step
        for sign in (1.0, -1.0):
            for k in range(-7, 8):
                box = Part.makeBox(depth, thick, length,
                                   Vector(-depth / 2.0, -thick / 2.0,
                                          -length / 2.0))
                # vipp sporet i tangentplanet
                box.rotate(Vector(0, 0, 0), Vector(1, 0, 0),
                           sign * KNURL_ANGLE)
                # flytt ut til overflaten, forskjøvet langs kanten
                box.translate(Vector(R + depth / 2.0 - KNURL_DEPTH,
                                     k * 1.15, H / 2.0))
                box.rotate(Vector(0, 0, 0), Vector(0, 0, 1), theta)
                tools.append(box)
    return tools


def build():
    t0 = time.time()

    # 1. grunnskive
    solid = Part.makeCylinder(R, H)

    # 2. hakk mellom kulene
    cuts = []
    for i in range(N_LOBES):
        a = math.radians((i + 0.5) * 360.0 / N_LOBES)
        d = R + SCALLOP_R * 0.42
        c = Part.makeCylinder(SCALLOP_R, H + 2,
                              Vector(d * math.cos(a), d * math.sin(a), -1))
        cuts.append(c)
    solid = solid.cut(Part.makeCompound(cuts))
    print("  hakk ferdig  %.1fs" % (time.time() - t0))

    # 3. senket midtparti, slik at kanten står igjen som en ring
    solid = solid.cut(Part.makeCylinder(R - RIM_W, RECESS + 1,
                                        Vector(0, 0, H - RECESS)))

    # 4. lommer mellom eikene, gjennomgående
    pockets = []
    for i in range(N_SPOKES):
        a = math.radians(i * 360.0 / N_SPOKES)
        pockets.append(Part.makeCylinder(
            POCKET_R, H + 2,
            Vector(POCKET_D * math.cos(a), POCKET_D * math.sin(a), -1)))
    solid = solid.cut(Part.makeCompound(pockets))

    # 5. nav, lagt tilbake i midten så det står høyere enn eikene
    solid = solid.fuse(Part.makeCylinder(HUB_R, H - RECESS * 0.35))
    solid = solid.removeSplitter()
    print("  lommer og nav ferdig  %.1fs" % (time.time() - t0))

    # 6. gjennomgående hull med senkning
    solid = solid.cut(Part.makeCylinder(BORE_R, H + 2, Vector(0, 0, -1)))
    cone = Part.makeCone(CBORE_R, BORE_R, CBORE_D,
                         Vector(0, 0, H - RECESS * 0.35 - CBORE_D))
    solid = solid.cut(cone)

    # 7. avrunding, før riflingen. Skarpe kanter ser billig ut i en matcap,
    #    og det er nettopp i avrundingene materialet viser seg frem.
    #    Rekkefølgen er ikke tilfeldig: riflingen lager hundrevis av korte
    #    kanter som møtes i spisse vinkler, og OCC gir opp hele filleten
    #    hvis den må forholde seg til dem.
    solid = fillet_safely(solid)
    print("  avrunding ferdig  %.1fs" % (time.time() - t0))

    # 8. rifling til slutt
    solid = solid.cut(Part.makeCompound(knurl_tools()))
    print("  rifling ferdig  %.1fs" % (time.time() - t0))
    return solid


def edge_key(edge):
    c = edge.CenterOfMass
    return (round(edge.Length, 3), round(c.x, 3), round(c.y, 3),
            round(c.z, 3))


def grew(before, after, tol=0.01):
    return (after.XMin < before.XMin - tol or after.XMax > before.XMax + tol
            or after.YMin < before.YMin - tol or after.YMax > before.YMax + tol
            or after.ZMin < before.ZMin - tol or after.ZMax > before.ZMax + tol)


def fillet_safely(shape, budget=90.0):
    """Avrunder kantene én om gangen, og hopper over dem som feiler.

    En samlet fillet på alt gir ingenting her: møtes to flater tangentielt,
    som der hakkene tangerer ytterkanten, gir OCC opp hele operasjonen. Tar
    vi én kant av gangen, mister vi bare de problematiske.
    """
    t0 = time.time()
    tried = set()
    done = 0
    bb0 = shape.BoundBox
    while time.time() - t0 < budget:
        target = None
        for e in shape.Edges:
            key = edge_key(e)
            if key in tried or e.Length < 2.0:
                continue
            target = (key, e)
            break
        if target is None:
            break
        key, edge = target
        tried.add(key)
        for radius in (FILLET, FILLET / 2.0):
            try:
                out = shape.makeFillet(radius, [edge])
            except Exception:
                continue
            # En fillet på en konkav kant legger på materiale. Der hakkene
            # tangerer ytterkanten gir det en vulst som stikker utenfor
            # både diameteren og topplanet. Vokser omskrevet boks, forkaster
            # vi kanten i stedet for å la modellen bli større enn tegnet.
            if out.isValid() and not grew(bb0, out.BoundBox):
                shape = out
                done += 1
                break
    print("  avrundet %d av %d kanter" % (done, len(tried)))
    return shape


def main(save_as=None):
    """Bygger rattet. Med save_as lagres det til en FCStd-fil.

    Kjør helst med save_as fra freecadcmd, og åpne fila i FreeCAD etterpå.
    Byggingen tar et kvarters titalls sekunder, og kjører den i GUI-tråden
    står programmet låst så lenge.
    """
    doc = FreeCAD.newDocument("MatCapDemo")
    solid = build()
    obj = doc.addObject("Part::Feature", "Ratt")
    obj.Label = "Ratt"
    obj.Shape = solid
    doc.recompute()

    vo = getattr(obj, "ViewObject", None)
    if vo is not None:
        vo.DisplayMode = "Flat Lines"
        # Finere tesselering. Standard er for grov for en matcap: fasettene
        # dukker opp som kanter midt i skyggeovergangene.
        try:
            vo.Deviation = 0.1
            vo.AngularDeflection = 12.0
        except Exception:
            pass

    bb = solid.BoundBox
    print("Ratt: %.1f x %.1f mm, volum %.0f mm3, %d flater"
          % (max(bb.XLength, bb.YLength), bb.ZLength,
             solid.Volume, len(solid.Faces)))

    if save_as:
        doc.saveAs(save_as)
        print("lagret", save_as)
    return obj


if __name__ == "__main__":
    main()
