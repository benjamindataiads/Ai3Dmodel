import os
import asyncio
import tempfile
from dataclasses import dataclass
from typing import Any

from app.config import settings


@dataclass
class ExecutionResult:
    success: bool
    bounding_box: dict[str, float] | None = None
    error: str | None = None


class CadService:
    """Service for executing CadQuery code in a sandboxed environment."""
    
    def __init__(self):
        self.timeout = 30  # seconds
    
    async def execute_code(self, code: str) -> ExecutionResult:
        """Execute CadQuery code and return the bounding box."""
        # Create execution script that captures the result
        execution_script = f'''
import sys
import json

# Execute the user code with extended library support
try:
    import cadquery as cq
    import math
    import numpy as np
    
    # CadQuery extension libraries (imported on demand based on code)
    # cq-warehouse: fasteners, bearings, threads
    # cq_gears: gear generation
    # cq-gridfinity: gridfinity bins
    # cq-kit: utilities
    
    # User code
{self._indent_code(code, 4)}
    
    # Get bounding box - handle both Workplane and Shape objects
    if hasattr(result, 'val'):
        shape = result.val()
    elif hasattr(result, 'wrapped'):
        shape = result.wrapped
    elif hasattr(result, 'BoundingBox'):
        shape = result
    else:
        # Try to get shape from build() if it's a library object
        if hasattr(result, 'build'):
            built = result.build()
            shape = built.val() if hasattr(built, 'val') else built
        else:
            shape = result
    
    bbox = shape.BoundingBox()
    output = {{
        "success": True,
        "bounding_box": {{
            "x": round(bbox.xlen, 3),
            "y": round(bbox.ylen, 3),
            "z": round(bbox.zlen, 3)
        }}
    }}
    print(json.dumps(output))
except Exception as e:
    import traceback
    output = {{
        "success": False,
        "error": str(e),
        "traceback": traceback.format_exc()
    }}
    print(json.dumps(output))
'''
        
        return await self._run_sandboxed(execution_script)
    
    async def generate_stl(self, code: str, part_id: str) -> str:
        """Generate STL file from CadQuery code."""
        os.makedirs(settings.temp_dir, exist_ok=True)
        stl_path = os.path.join(settings.temp_dir, f"{part_id}.stl")
        
        execution_script = f'''
import sys
import json

try:
    import cadquery as cq
    from cadquery import exporters
    import math
    import numpy as np
    
    # User code
{self._indent_code(code, 4)}
    
    # Handle different result types from libraries
    export_shape = result
    if hasattr(result, 'build'):
        # Library objects like cq_gears.SpurGear need to call build()
        export_shape = result.build()
    
    # Export to STL
    exporters.export(export_shape, "{stl_path}")
    
    output = {{"success": True, "path": "{stl_path}"}}
    print(json.dumps(output))
except Exception as e:
    import traceback
    output = {{"success": False, "error": str(e), "traceback": traceback.format_exc()}}
    print(json.dumps(output))
'''
        
        result = await self._run_sandboxed(execution_script)
        
        if not result.success:
            raise Exception(result.error or "Failed to generate STL")
        
        return stl_path
    
    async def _run_sandboxed(self, script: str) -> ExecutionResult:
        """Run script in subprocess with timeout."""
        import json
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(script)
            script_path = f.name
        
        try:
            process = await asyncio.create_subprocess_exec(
                'python', script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                return ExecutionResult(
                    success=False,
                    error=f"Execution timed out after {self.timeout} seconds"
                )
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                return ExecutionResult(success=False, error=error_msg)
            
            try:
                output = json.loads(stdout.decode())
                if output.get("success"):
                    return ExecutionResult(
                        success=True,
                        bounding_box=output.get("bounding_box")
                    )
                else:
                    return ExecutionResult(
                        success=False,
                        error=output.get("error", "Unknown error")
                    )
            except json.JSONDecodeError:
                return ExecutionResult(
                    success=False,
                    error=f"Invalid output: {stdout.decode()}"
                )
        finally:
            os.unlink(script_path)
    
    def _indent_code(self, code: str, spaces: int) -> str:
        """Indent code block."""
        indent = ' ' * spaces
        lines = code.split('\n')
        return '\n'.join(indent + line for line in lines)


cad_service = CadService()
