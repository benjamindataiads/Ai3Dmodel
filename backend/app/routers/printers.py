from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class BuildVolume(BaseModel):
    x: float
    y: float
    z: float


class PrinterPreset(BaseModel):
    id: str
    name: str
    build_volume: BuildVolume
    bed_shape: str


PRINTER_PRESETS: list[PrinterPreset] = [
    PrinterPreset(
        id="bambulab-p1s",
        name="Bambu Lab P1S",
        build_volume=BuildVolume(x=256, y=256, z=256),
        bed_shape="rectangular",
    ),
    PrinterPreset(
        id="bambulab-p2s",
        name="Bambu Lab P2S",
        build_volume=BuildVolume(x=256, y=256, z=256),
        bed_shape="rectangular",
    ),
    PrinterPreset(
        id="bambulab-x1c",
        name="Bambu Lab X1 Carbon",
        build_volume=BuildVolume(x=256, y=256, z=256),
        bed_shape="rectangular",
    ),
    PrinterPreset(
        id="bambulab-a1",
        name="Bambu Lab A1",
        build_volume=BuildVolume(x=256, y=256, z=256),
        bed_shape="rectangular",
    ),
    PrinterPreset(
        id="bambulab-a1-mini",
        name="Bambu Lab A1 Mini",
        build_volume=BuildVolume(x=180, y=180, z=180),
        bed_shape="rectangular",
    ),
    PrinterPreset(
        id="prusa-mk4",
        name="Prusa MK4",
        build_volume=BuildVolume(x=250, y=210, z=220),
        bed_shape="rectangular",
    ),
    PrinterPreset(
        id="prusa-mini",
        name="Prusa Mini+",
        build_volume=BuildVolume(x=180, y=180, z=180),
        bed_shape="rectangular",
    ),
    PrinterPreset(
        id="ender3-v2",
        name="Creality Ender 3 V2",
        build_volume=BuildVolume(x=220, y=220, z=250),
        bed_shape="rectangular",
    ),
    PrinterPreset(
        id="ender3-s1",
        name="Creality Ender 3 S1",
        build_volume=BuildVolume(x=220, y=220, z=270),
        bed_shape="rectangular",
    ),
    PrinterPreset(
        id="voron-0",
        name="Voron 0.2",
        build_volume=BuildVolume(x=120, y=120, z=120),
        bed_shape="rectangular",
    ),
    PrinterPreset(
        id="voron-2",
        name="Voron 2.4 (350mm)",
        build_volume=BuildVolume(x=350, y=350, z=340),
        bed_shape="rectangular",
    ),
    PrinterPreset(
        id="custom",
        name="Personnalisé",
        build_volume=BuildVolume(x=200, y=200, z=200),
        bed_shape="rectangular",
    ),
]


@router.get("/presets", response_model=list[PrinterPreset])
async def get_printer_presets():
    """Get list of predefined printer profiles."""
    return PRINTER_PRESETS
