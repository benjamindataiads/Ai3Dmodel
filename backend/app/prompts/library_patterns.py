"""
Pre-built patterns and library knowledge for CadQuery extensions.
These patterns are injected into prompts when relevant features are detected.
"""

# Keywords that trigger library suggestions
LIBRARY_TRIGGERS = {
    "fastener": ["screw", "bolt", "nut", "washer", "fastener", "vis", "écrou", "boulon", "rondelle"],
    "thread": ["thread", "threading", "threaded", "filetage", "fileté", "taraudage"],
    "gear": ["gear", "cog", "engrenage", "pignon", "crémaillère", "rack"],
    "bearing": ["bearing", "roulement", "palier"],
    "gridfinity": ["gridfinity", "bin", "organizer", "rangement", "casier"],
    "chain": ["chain", "chaîne", "maillon"],
}


CQ_WAREHOUSE_PATTERNS = '''
## CQ-WAREHOUSE - Fasteners, Bearings, Threads

cq-warehouse fournit des composants mécaniques paramétriques pré-construits.

### Import
```python
import cadquery as cq
from cq_warehouse.fastener import SocketHeadCapScrew, HexNut, Washer
from cq_warehouse.bearing import SingleRowDeepGrooveBallBearing
from cq_warehouse.thread import IsoThread
from cq_warehouse.chain import Chain
```

### Fasteners (Vis, Écrous, Rondelles)
```python
import cadquery as cq
from cq_warehouse.fastener import SocketHeadCapScrew, HexNut, CounterSunkScrew

# Vis à tête cylindrique M5x20
screw = SocketHeadCapScrew(size="M5-0.8", length=20, fastener_type="iso4762")

# Écrou hexagonal M5
nut = HexNut(size="M5-0.8", fastener_type="iso4032")

# Vis à tête fraisée M4x15
countersunk = CounterSunkScrew(size="M4-0.7", length=15, fastener_type="iso10642")

# Pour créer les trous correspondants dans une pièce:
plate = (
    cq.Workplane("XY")
    .box(50, 50, 10)
    .faces(">Z")
    .workplane()
    .clearanceHole(fastener=screw, fit="Normal", counterSunk=False)
)
result = plate
```

### Threads (Filetages)
```python
import cadquery as cq
from cq_warehouse.thread import IsoThread

# Filetage externe M10 de 20mm de long
external_thread = IsoThread(
    major_diameter=10,
    pitch=1.5,
    length=20,
    external=True
)

# Filetage interne (taraudage) M10
internal_thread = IsoThread(
    major_diameter=10,
    pitch=1.5,
    length=15,
    external=False
)

# Ajouter un filetage à un cylindre
base = cq.Workplane("XY").cylinder(20, 5)
result = base.union(external_thread.cq_object.translate((0, 0, 20)))
```

### Bearings (Roulements)
```python
import cadquery as cq
from cq_warehouse.bearing import SingleRowDeepGrooveBallBearing

# Roulement 608 (skateboard bearing: 8mm bore, 22mm OD, 7mm width)
bearing = SingleRowDeepGrooveBallBearing(size="M8-22-7", bearing_type="SKT")

# Créer un logement pour roulement
housing = (
    cq.Workplane("XY")
    .cylinder(15, bearing.bearing_dict["d2"] / 2 + 3)
    .faces(">Z")
    .workplane()
    .hole(bearing.bearing_dict["d2"])  # Diamètre extérieur du roulement
)
result = housing
```

### Sizes fastener standards disponibles
- **ISO 4762**: Vis CHC (Socket Head Cap Screw) - M2 à M24
- **ISO 4032**: Écrou hexagonal - M2 à M24
- **ISO 10642**: Vis fraisée (Countersunk) - M3 à M20
- **ISO 7380**: Vis à tête bombée - M3 à M12
'''


CQ_GEARS_PATTERNS = '''
## CQ_GEARS - Engrenages Paramétriques

cq_gears permet de créer des engrenages involutes, hélicoïdaux et coniques.

### Import
```python
import cadquery as cq
from cq_gears import SpurGear, HerringboneGear, BevelGear, RingGear
```

### Engrenage droit (Spur Gear)
```python
import cadquery as cq
from cq_gears import SpurGear

# Engrenage droit 20 dents, module 2, épaisseur 10mm
gear = SpurGear(
    module=2.0,          # Module (taille des dents)
    teeth_number=20,     # Nombre de dents
    width=10.0,          # Épaisseur
    bore_d=8.0           # Diamètre de l'alésage central
)
result = gear.build()
```

### Engrenage hélicoïdal (Herringbone)
```python
import cadquery as cq
from cq_gears import HerringboneGear

# Engrenage chevron (double hélice)
gear = HerringboneGear(
    module=2.0,
    teeth_number=30,
    width=15.0,
    helix_angle=25.0,    # Angle d'hélice en degrés
    bore_d=10.0
)
result = gear.build()
```

### Couronne dentée (Ring Gear / Internal Gear)
```python
import cadquery as cq
from cq_gears import RingGear

# Couronne dentée interne
ring = RingGear(
    module=2.0,
    teeth_number=40,
    width=10.0,
    rim_width=5.0        # Épaisseur de la couronne
)
result = ring.build()
```

### Pignon conique (Bevel Gear)
```python
import cadquery as cq
from cq_gears import BevelGear

# Engrenage conique
bevel = BevelGear(
    module=2.0,
    teeth_number=20,
    face_width=10.0,
    cone_angle=45.0,
    bore_d=6.0
)
result = bevel.build()
```

### Couple pignon/engrenage
```python
import cadquery as cq
from cq_gears import SpurGear

# Ratio 1:3 - Pignon 15 dents, engrenage 45 dents
module = 1.5

pinion = SpurGear(module=module, teeth_number=15, width=8.0, bore_d=5.0)
gear = SpurGear(module=module, teeth_number=45, width=8.0, bore_d=10.0)

# Distance entre axes = module * (z1 + z2) / 2
center_distance = module * (15 + 45) / 2  # = 45mm

pinion_part = pinion.build()
gear_part = gear.build().translate((center_distance, 0, 0))

result = pinion_part.union(gear_part)
```
'''


CQ_GRIDFINITY_PATTERNS = '''
## CQ-GRIDFINITY - Système de Rangement Modulaire

cq-gridfinity permet de créer des bacs et plaques de base Gridfinity.

### Import
```python
import cadquery as cq
from cq_gridfinity import GridfinityBox, GridfinityBaseplate
```

### Bac Gridfinity simple
```python
import cadquery as cq
from cq_gridfinity import GridfinityBox

# Bac 2x3 unités, 4 unités de haut (environ 28mm)
box = GridfinityBox(
    length_u=2,          # Largeur en unités (42mm par unité)
    width_u=3,           # Profondeur en unités
    height_u=4,          # Hauteur en unités (7mm par unité)
    wall_thickness=1.2,  # Épaisseur des parois
    with_label=True,     # Emplacement pour étiquette
    with_scoop=True      # Rampe pour accès facile
)
result = box.build()
```

### Bac avec compartiments
```python
import cadquery as cq
from cq_gridfinity import GridfinityBox

# Bac 3x2 avec séparations
box = GridfinityBox(
    length_u=3,
    width_u=2,
    height_u=3,
    wall_thickness=1.2,
    divisions_x=3,       # 3 compartiments en X
    divisions_y=2,       # 2 compartiments en Y
)
result = box.build()
```

### Plaque de base (Baseplate)
```python
import cadquery as cq
from cq_gridfinity import GridfinityBaseplate

# Plaque 4x4 unités
baseplate = GridfinityBaseplate(
    length_u=4,
    width_u=4,
    with_magnets=True,   # Trous pour aimants 6x2mm
    magnet_diameter=6.0,
    magnet_depth=2.4
)
result = baseplate.build()
```

### Dimensions Gridfinity standard
- 1 unité = 42mm x 42mm
- Hauteur: 7mm par unité (1u = 7mm, 2u = 14mm, etc.)
- Clearance standard entre bac et base: 0.5mm
- Trous aimants: 6mm diamètre, 2-2.4mm profondeur
'''


CQ_KIT_PATTERNS = '''
## CQ-KIT - Utilitaires et Helpers

cq-kit fournit des fonctions utilitaires pour simplifier les opérations CadQuery courantes.

### Import
```python
import cadquery as cq
from cqkit import (
    rounded_box,
    extrude_text,
    export_stl_with_tolerance,
    array_along_curve,
    fillet_edges_by_length
)
```

### Boîte arrondie optimisée
```python
import cadquery as cq
from cqkit import rounded_box

# Boîte avec tous les bords arrondis de manière fiable
result = rounded_box(
    length=100,
    width=60,
    height=30,
    fillet_radius=3.0
)
```

### Texte en relief
```python
import cadquery as cq
from cqkit import extrude_text

# Texte extrudé sur une surface
base = cq.Workplane("XY").box(80, 30, 5)
text = extrude_text(
    text="Hello",
    font_size=12,
    depth=2.0,
    font="Arial"
)

result = base.union(text.translate((0, 0, 5)))
```

### Pattern le long d'une courbe
```python
import cadquery as cq
from cqkit import array_along_curve

# Répéter un élément le long d'une courbe
element = cq.Workplane("XY").sphere(3)
curve = cq.Edge.makeSpline([
    (0, 0, 0),
    (50, 20, 0),
    (100, 0, 0)
])

result = array_along_curve(element, curve, count=10)
```
'''


LIBRARY_ENHANCEMENT_PROMPT = '''
## BIBLIOTHÈQUES CADQUERY DISPONIBLES

Tu as accès à plusieurs bibliothèques CadQuery étendues. Utilise-les quand approprié:

{library_sections}

## RÈGLES D'UTILISATION DES BIBLIOTHÈQUES

1. **Importer uniquement ce qui est nécessaire**: N'importe que les modules utilisés
2. **Préférer les composants pré-construits**: Utilise les bibliothèques plutôt que de recréer des vis, engrenages, etc.
3. **Combiner avec CadQuery natif**: Ces bibliothèques retournent des objets CadQuery standard
4. **Toujours produire `result`**: Le code doit toujours définir une variable `result`

## QUAND UTILISER CHAQUE BIBLIOTHÈQUE

- **Vis, écrous, rondelles, filetages** → cq-warehouse
- **Engrenages, pignons, crémaillères** → cq_gears  
- **Rangement modulaire, bacs** → cq-gridfinity
- **Utilitaires, texte, patterns** → cq-kit
'''


def get_relevant_patterns(prompt: str) -> str:
    """Detect keywords in prompt and return relevant library patterns."""
    prompt_lower = prompt.lower()
    patterns = []
    
    # Check for fastener/thread keywords
    for keyword in LIBRARY_TRIGGERS["fastener"] + LIBRARY_TRIGGERS["thread"]:
        if keyword in prompt_lower:
            patterns.append(CQ_WAREHOUSE_PATTERNS)
            break
    
    # Check for gear keywords
    for keyword in LIBRARY_TRIGGERS["gear"]:
        if keyword in prompt_lower:
            patterns.append(CQ_GEARS_PATTERNS)
            break
    
    # Check for bearing keywords (also in cq-warehouse)
    for keyword in LIBRARY_TRIGGERS["bearing"]:
        if keyword in prompt_lower:
            if CQ_WAREHOUSE_PATTERNS not in patterns:
                patterns.append(CQ_WAREHOUSE_PATTERNS)
            break
    
    # Check for gridfinity keywords
    for keyword in LIBRARY_TRIGGERS["gridfinity"]:
        if keyword in prompt_lower:
            patterns.append(CQ_GRIDFINITY_PATTERNS)
            break
    
    # Check for chain keywords
    for keyword in LIBRARY_TRIGGERS["chain"]:
        if keyword in prompt_lower:
            if CQ_WAREHOUSE_PATTERNS not in patterns:
                patterns.append(CQ_WAREHOUSE_PATTERNS)
            break
    
    if not patterns:
        return ""
    
    library_sections = "\n\n".join(patterns)
    return LIBRARY_ENHANCEMENT_PROMPT.format(library_sections=library_sections)


def get_all_patterns() -> str:
    """Return all library patterns for comprehensive generation."""
    all_patterns = "\n\n".join([
        CQ_WAREHOUSE_PATTERNS,
        CQ_GEARS_PATTERNS,
        CQ_GRIDFINITY_PATTERNS,
        CQ_KIT_PATTERNS
    ])
    return LIBRARY_ENHANCEMENT_PROMPT.format(library_sections=all_patterns)
