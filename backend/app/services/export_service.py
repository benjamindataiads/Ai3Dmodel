import os
import asyncio
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from typing import Any

from app.config import settings
from app.services.cad_service import cad_service


class ExportService:
    """Service for exporting CAD models to STL and 3MF formats."""
    
    async def export_stl(self, code: str, part_id: str, name: str) -> str:
        """Export CadQuery code to STL file."""
        return await cad_service.generate_stl(code, part_id)
    
    async def export_3mf(self, code: str, part_id: str, name: str) -> str:
        """Export CadQuery code to 3MF file (Bambu Studio compatible)."""
        os.makedirs(settings.temp_dir, exist_ok=True)
        
        # First generate STL
        stl_path = await cad_service.generate_stl(code, part_id)
        
        # Convert STL to 3MF
        threemf_path = os.path.join(settings.temp_dir, f"{part_id}.3mf")
        await self._stl_to_3mf(stl_path, threemf_path, name)
        
        return threemf_path
    
    async def export_project_3mf(
        self,
        parts: list[tuple[str, str]],  # [(code, name), ...]
        project_id: str,
        project_name: str,
    ) -> str:
        """Export multiple parts to a single 3MF file."""
        os.makedirs(settings.temp_dir, exist_ok=True)
        
        # Generate STLs for all parts
        stl_files = []
        for i, (code, name) in enumerate(parts):
            part_id = f"{project_id}_{i}"
            stl_path = await cad_service.generate_stl(code, part_id)
            stl_files.append((stl_path, name))
        
        # Create combined 3MF
        threemf_path = os.path.join(settings.temp_dir, f"{project_id}.3mf")
        await self._multiple_stl_to_3mf(stl_files, threemf_path, project_name)
        
        return threemf_path
    
    async def _stl_to_3mf(self, stl_path: str, threemf_path: str, name: str) -> None:
        """Convert single STL to 3MF format."""
        await self._multiple_stl_to_3mf([(stl_path, name)], threemf_path, name)
    
    async def _multiple_stl_to_3mf(
        self,
        stl_files: list[tuple[str, str]],
        threemf_path: str,
        project_name: str,
    ) -> None:
        """Convert multiple STLs to a single 3MF file."""
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._create_3mf_sync,
            stl_files,
            threemf_path,
            project_name,
        )
    
    def _create_3mf_sync(
        self,
        stl_files: list[tuple[str, str]],
        threemf_path: str,
        project_name: str,
    ) -> None:
        """Synchronously create 3MF file from STL files."""
        # 3MF is essentially a ZIP file with XML content
        with zipfile.ZipFile(threemf_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Create [Content_Types].xml
            content_types = self._create_content_types()
            zf.writestr('[Content_Types].xml', content_types)
            
            # Create _rels/.rels
            rels = self._create_rels()
            zf.writestr('_rels/.rels', rels)
            
            # Create 3D/3dmodel.model with all meshes
            model_xml = self._create_model_xml(stl_files, project_name)
            zf.writestr('3D/3dmodel.model', model_xml)
    
    def _create_content_types(self) -> str:
        """Create [Content_Types].xml for 3MF."""
        root = ET.Element('Types')
        root.set('xmlns', 'http://schemas.openxmlformats.org/package/2006/content-types')
        
        ET.SubElement(root, 'Default', {
            'Extension': 'rels',
            'ContentType': 'application/vnd.openxmlformats-package.relationships+xml'
        })
        ET.SubElement(root, 'Default', {
            'Extension': 'model',
            'ContentType': 'application/vnd.ms-package.3dmanufacturing-3dmodel+xml'
        })
        
        return ET.tostring(root, encoding='unicode', xml_declaration=True)
    
    def _create_rels(self) -> str:
        """Create _rels/.rels for 3MF."""
        root = ET.Element('Relationships')
        root.set('xmlns', 'http://schemas.openxmlformats.org/package/2006/relationships')
        
        ET.SubElement(root, 'Relationship', {
            'Target': '/3D/3dmodel.model',
            'Id': 'rel0',
            'Type': 'http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel'
        })
        
        return ET.tostring(root, encoding='unicode', xml_declaration=True)
    
    def _create_model_xml(
        self,
        stl_files: list[tuple[str, str]],
        project_name: str,
    ) -> str:
        """Create 3D/3dmodel.model XML with meshes from STL files."""
        ns = 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
        
        root = ET.Element('model')
        root.set('xmlns', ns)
        root.set('unit', 'millimeter')
        
        # Metadata
        metadata = ET.SubElement(root, 'metadata', {'name': 'Title'})
        metadata.text = project_name
        
        # Resources
        resources = ET.SubElement(root, 'resources')
        
        # Build
        build = ET.SubElement(root, 'build')
        
        for i, (stl_path, name) in enumerate(stl_files):
            object_id = str(i + 1)
            
            # Parse STL and create mesh
            vertices, triangles = self._parse_stl(stl_path)
            
            # Object
            obj = ET.SubElement(resources, 'object', {
                'id': object_id,
                'type': 'model',
                'name': name,
            })
            
            mesh = ET.SubElement(obj, 'mesh')
            
            # Vertices
            vertices_elem = ET.SubElement(mesh, 'vertices')
            for v in vertices:
                ET.SubElement(vertices_elem, 'vertex', {
                    'x': str(v[0]),
                    'y': str(v[1]),
                    'z': str(v[2]),
                })
            
            # Triangles
            triangles_elem = ET.SubElement(mesh, 'triangles')
            for t in triangles:
                ET.SubElement(triangles_elem, 'triangle', {
                    'v1': str(t[0]),
                    'v2': str(t[1]),
                    'v3': str(t[2]),
                })
            
            # Add to build
            ET.SubElement(build, 'item', {'objectid': object_id})
        
        return ET.tostring(root, encoding='unicode', xml_declaration=True)
    
    def _parse_stl(self, stl_path: str) -> tuple[list[tuple[float, float, float]], list[tuple[int, int, int]]]:
        """Parse binary or ASCII STL file and return vertices and triangles."""
        with open(stl_path, 'rb') as f:
            header = f.read(80)
            
            # Check if binary STL
            f.seek(80)
            num_triangles_bytes = f.read(4)
            
            if len(num_triangles_bytes) < 4:
                # ASCII STL
                return self._parse_ascii_stl(stl_path)
            
            import struct
            num_triangles = struct.unpack('<I', num_triangles_bytes)[0]
            
            # Check file size to confirm binary
            f.seek(0, 2)
            file_size = f.tell()
            expected_size = 84 + num_triangles * 50
            
            if file_size == expected_size:
                return self._parse_binary_stl(stl_path, num_triangles)
            else:
                return self._parse_ascii_stl(stl_path)
    
    def _parse_binary_stl(
        self,
        stl_path: str,
        num_triangles: int,
    ) -> tuple[list[tuple[float, float, float]], list[tuple[int, int, int]]]:
        """Parse binary STL file."""
        import struct
        
        vertices = []
        triangles = []
        vertex_map = {}
        
        with open(stl_path, 'rb') as f:
            f.seek(84)  # Skip header and triangle count
            
            for _ in range(num_triangles):
                # Skip normal (12 bytes)
                f.read(12)
                
                tri_indices = []
                for _ in range(3):
                    x, y, z = struct.unpack('<fff', f.read(12))
                    vertex = (round(x, 6), round(y, 6), round(z, 6))
                    
                    if vertex not in vertex_map:
                        vertex_map[vertex] = len(vertices)
                        vertices.append(vertex)
                    
                    tri_indices.append(vertex_map[vertex])
                
                triangles.append(tuple(tri_indices))
                
                # Skip attribute byte count
                f.read(2)
        
        return vertices, triangles
    
    def _parse_ascii_stl(
        self,
        stl_path: str,
    ) -> tuple[list[tuple[float, float, float]], list[tuple[int, int, int]]]:
        """Parse ASCII STL file."""
        vertices = []
        triangles = []
        vertex_map = {}
        
        with open(stl_path, 'r') as f:
            current_triangle = []
            
            for line in f:
                line = line.strip()
                
                if line.startswith('vertex'):
                    parts = line.split()
                    x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                    vertex = (round(x, 6), round(y, 6), round(z, 6))
                    
                    if vertex not in vertex_map:
                        vertex_map[vertex] = len(vertices)
                        vertices.append(vertex)
                    
                    current_triangle.append(vertex_map[vertex])
                
                elif line.startswith('endfacet'):
                    if len(current_triangle) == 3:
                        triangles.append(tuple(current_triangle))
                    current_triangle = []
        
        return vertices, triangles


export_service = ExportService()
