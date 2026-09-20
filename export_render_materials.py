# -*- coding: utf-8 -*-
"""Lager Render-arbeidsbenkens materialobjekter fra MatCap-materialene.

Render-arbeidsbenken leser ikke ShapeMaterial. Den ser etter en lenke
obj.Material til et App::MaterialObjectPython, og leser en ordbok derfra
som maa inneholde noekkelen Render.Type. Det er en annen beholder enn
FreeCADs nye materialsystem, selv om parameternavnene er de samme.

Dette skriptet bygger broen: det leser Disney-verdiene fra objektets
ShapeMaterial og legger dem i det formatet Render-benken forventer.

Kjoeres fra FreeCADs Python-konsoll, med dokumentet aapent:

    exec(open("<denne fila>").read())
    export_render_materials()

Objektene legges bare til naar du ber om det. Et dokument du bare
modellerer i skal slippe aa baere dem.
"""

import FreeCAD

DISNEY_UUID = "f8723572-4470-4c39-a749-6d3b71358a5b"


def _les_farge(verdi):
    if verdi is None:
        return None
    if isinstance(verdi, (tuple, list)):
        return tuple(float(c) for c in verdi[:3])
    deler = str(verdi).strip().strip("()").replace(",", " ").split()
    if len(deler) < 3:
        return None
    try:
        return tuple(float(d) for d in deler[:3])
    except ValueError:
        return None


def disney_values(obj):
    """Henter BaseColor, Metallic og Roughness fra objektets materiale."""
    mat = getattr(obj, "ShapeMaterial", None)
    if mat is None:
        return None
    try:
        if not mat.hasAppearanceModel(DISNEY_UUID):
            return None
        base = _les_farge(mat.getAppearanceValue("Render.Disney.BaseColor"))
        met = float(mat.getAppearanceValue("Render.Disney.Metallic"))
        rgh = float(mat.getAppearanceValue("Render.Disney.Roughness"))
    except Exception:
        return None
    if base is None:
        return None
    return mat.Name, base, met, rgh


def render_dict(navn, base, metallisk, ruhet):
    """Ordboken Render-benken leser.

    Render.Type er noekkelen som avgjoer alt. Uten den faller benken
    tilbake til en diffus standardfarge, uansett hva som ellers staar
    i ordboken.
    """
    return {
        "Name": navn,
        "Render.Type": "Disney",
        "Render.Disney.BaseColor": "(%.4f, %.4f, %.4f)" % base,
        "Render.Disney.Metallic": "%.4f" % metallisk,
        "Render.Disney.Roughness": "%.4f" % ruhet,
        "Render.Disney.Specular": "0.5",
        "Render.Disney.SpecularTint": "0.0",
        "Render.Disney.Anisotropic": "0.0",
        "Render.Disney.Sheen": "0.0",
        "Render.Disney.SheenTint": "0.0",
        "Render.Disney.ClearCoat": "0.0",
        "Render.Disney.ClearCoatGloss": "0.0",
        "Render.Disney.Subsurface": "0.0",
    }


def export_render_materials(doc=None):
    """Bygger eller oppdaterer Render-materialer for hele dokumentet."""
    doc = doc or FreeCAD.ActiveDocument
    if doc is None:
        print("ingen aktivt dokument")
        return 0

    laget = 0
    for obj in list(doc.Objects):
        if obj.TypeId.startswith("App::") or not hasattr(obj, "Shape"):
            continue
        verdier = disney_values(obj)
        if verdier is None:
            continue
        navn, base, met, rgh = verdier

        # Gjenbruk materialobjektet hvis det finnes fra foer, slik at
        # gjentatte kjoeringer ikke fyller dokumentet med duplikater.
        intern = "RenderMat_" + navn.replace("MatCap_", "")
        mo = doc.getObject(intern)
        if mo is None:
            mo = doc.addObject("App::MaterialObjectPython", intern)
            laget += 1
        mo.Label = navn
        mo.Material = render_dict(navn, base, met, rgh)

        if "Material" not in obj.PropertiesList:
            obj.addProperty("App::PropertyLink", "Material", "Render",
                            "Materiale for Render-arbeidsbenken")
        obj.Material = mo
        print("%-22s -> %s  metallic %.2f, roughness %.2f"
              % (obj.Label, navn, met, rgh))

    doc.recompute()
    print("ferdig, %d nye materialobjekt(er)" % laget)
    return laget
