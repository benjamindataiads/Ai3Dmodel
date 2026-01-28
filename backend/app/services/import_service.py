"""Service for importing 3D files (STL, OBJ, 3MF)."""
import io
import struct
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import BinaryIO


@dataclass
class ImportResult:
    success: bool
    vertices: list[list[float]] | None = None
    faces: list[list[int]] | None = None
    bounding_box: dict | None = None
    error: str | None = None


def _calculate_bounding_box(vertices: list[list[float]]) -> dict:
    """Calculate bounding box from vertices."""
    if not vertices:
        return {"min_x": 0, "min_y": 0, "min_z": 0, "max_x": 0, "max_y": 0, "max_z": 0}
    
    xs = [v[0] for v in vertices]
    ys = [v[1] for v in vertices]
    zs = [v[2] for v in vertices]
    
    return {
        "min_x": min(xs),
        "min_y": min(ys),
        "min_z": min(zs),
        "max_x": max(xs),
        "max_y": max(ys),
        "max_z": max(zs),
    }


def parse_stl_ascii(content: str) -> ImportResult:
    """Parse ASCII STL file."""
    vertices = []
    faces = []
    vertex_map = {}
    
    lines = content.strip().split('\n')
    current_face = []
    
    for line in lines:
        line = line.strip().lower()
        if line.startswith('vertex'):
            parts = line.split()
            if len(parts) >= 4:
                vertex = [float(parts[1]), float(parts[2]), float(parts[3])]
                vertex_key = tuple(vertex)
                
                if vertex_key not in vertex_map:
                    vertex_map[vertex_key] = len(vertices)
                    vertices.append(vertex)
                
                current_face.append(vertex_map[vertex_key])
        elif line.startswith('endfacet'):
            if len(current_face) == 3:
                faces.append(current_face)
            current_face = []
    
    if not vertices:
        return ImportResult(success=False, error="No vertices found in STL file")
    
    return ImportResult(
        success=True,
        vertices=vertices,
        faces=faces,
        bounding_box=_calculate_bounding_box(vertices),
    )


def parse_stl_binary(data: bytes) -> ImportResult:
    """Parse binary STL file."""
    if len(data) < 84:
        return ImportResult(success=False, error="Invalid binary STL file (too small)")
    
    # Skip 80-byte header
    num_triangles = struct.unpack('<I', data[80:84])[0]
    
    vertices = []
    faces = []
    vertex_map = {}
    
    offset = 84
    for _ in range(num_triangles):
        if offset + 50 > len(data):
            break
        
        # Skip normal vector (12 bytes)
        offset += 12
        
        face = []
        for _ in range(3):
            x, y, z = struct.unpack('<fff', data[offset:offset + 12])
            vertex = [x, y, z]
            vertex_key = (round(x, 6), round(y, 6), round(z, 6))
            
            if vertex_key not in vertex_map:
                vertex_map[vertex_key] = len(vertices)
                vertices.append(vertex)
            
            face.append(vertex_map[vertex_key])
            offset += 12
        
        faces.append(face)
        offset += 2  # Skip attribute byte count
    
    if not vertices:
        return ImportResult(success=False, error="No vertices found in binary STL file")
    
    return ImportResult(
        success=True,
        vertices=vertices,
        faces=faces,
        bounding_box=_calculate_bounding_box(vertices),
    )


def parse_stl(file: BinaryIO, filename: str) -> ImportResult:
    """Parse STL file (auto-detect ASCII vs binary)."""
    try:
        data = file.read()
        
        # Try to detect if ASCII or binary
        try:
            text = data.decode('utf-8', errors='strict')
            if text.strip().lower().startswith('solid') and 'vertex' in text.lower():
                return parse_stl_ascii(text)
        except:
            pass
        
        # Assume binary
        return parse_stl_binary(data)
    except Exception as e:
        return ImportResult(success=False, error=f"Failed to parse STL: {str(e)}")


def parse_obj(file: BinaryIO, filename: str) -> ImportResult:
    """Parse OBJ file."""
    try:
        content = file.read().decode('utf-8', errors='replace')
        
        vertices = []
        faces = []
        
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            parts = line.split()
            if not parts:
                continue
            
            if parts[0] == 'v' and len(parts) >= 4:
                vertices.append([float(parts[1]), float(parts[2]), float(parts[3])])
            elif parts[0] == 'f' and len(parts) >= 4:
                # OBJ faces are 1-indexed
                face = []
                for p in parts[1:4]:  # Only take first 3 vertices (triangulate)
                    idx = p.split('/')[0]
                    face.append(int(idx) - 1)
                faces.append(face)
        
        if not vertices:
            return ImportResult(success=False, error="No vertices found in OBJ file")
        
        return ImportResult(
            success=True,
            vertices=vertices,
            faces=faces,
            bounding_box=_calculate_bounding_box(vertices),
        )
    except Exception as e:
        return ImportResult(success=False, error=f"Failed to parse OBJ: {str(e)}")


def parse_3mf(file: BinaryIO, filename: str) -> ImportResult:
    """Parse 3MF file (ZIP containing XML mesh data)."""
    try:
        data = file.read()
        
        with zipfile.ZipFile(io.BytesIO(data), 'r') as zf:
            # Find the model file
            model_file = None
            for name in zf.namelist():
                if name.endswith('.model') or '3D/3dmodel.model' in name:
                    model_file = name
                    break
            
            if not model_file:
                # Try common paths
                for path in ['3D/3dmodel.model', '3dmodel.model']:
                    if path in zf.namelist():
                        model_file = path
                        break
            
            if not model_file:
                return ImportResult(success=False, error="No model file found in 3MF archive")
            
            model_content = zf.read(model_file).decode('utf-8')
            
            # Parse XML
            root = ET.fromstring(model_content)
            ns = {'m': 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
            
            vertices = []
            faces = []
            
            # Find mesh elements
            for mesh in root.findall('.//m:mesh', ns):
                # Get vertices
                vertices_elem = mesh.find('m:vertices', ns)
                if vertices_elem is not None:
                    for vertex in vertices_elem.findall('m:vertex', ns):
                        x = float(vertex.get('x', 0))
                        y = float(vertex.get('y', 0))
                        z = float(vertex.get('z', 0))
                        vertices.append([x, y, z])
                
                # Get triangles
                triangles_elem = mesh.find('m:triangles', ns)
                if triangles_elem is not None:
                    for triangle in triangles_elem.findall('m:triangle', ns):
                        v1 = int(triangle.get('v1', 0))
                        v2 = int(triangle.get('v2', 0))
                        v3 = int(triangle.get('v3', 0))
                        faces.append([v1, v2, v3])
            
            if not vertices:
                return ImportResult(success=False, error="No vertices found in 3MF file")
            
            return ImportResult(
                success=True,
                vertices=vertices,
                faces=faces,
                bounding_box=_calculate_bounding_box(vertices),
            )
    except Exception as e:
        return ImportResult(success=False, error=f"Failed to parse 3MF: {str(e)}")


def import_file(file: BinaryIO, filename: str) -> ImportResult:
    """Import a 3D file based on its extension."""
    filename_lower = filename.lower()
    
    if filename_lower.endswith('.stl'):
        return parse_stl(file, filename)
    elif filename_lower.endswith('.obj'):
        return parse_obj(file, filename)
    elif filename_lower.endswith('.3mf'):
        return parse_3mf(file, filename)
    else:
        return ImportResult(
            success=False,
            error=f"Unsupported file format. Supported: STL, OBJ, 3MF"
        )


# Singleton instance
import_service = type('ImportService', (), {
    'import_file': staticmethod(import_file),
})()
