import ast
import re
from typing import Any


class ParameterService:
    """Service for extracting and injecting parameters from CadQuery code."""
    
    # Patterns for common dimension variable names
    DIMENSION_PATTERNS = [
        r'^(length|width|height|depth|thickness|diameter|radius)$',
        r'^(x|y|z)_?(size|dim|length|width)?$',
        r'^(hole|slot|groove)_?(diameter|radius|width|depth|size)?$',
        r'^(wall|edge|corner|fillet|chamfer|bevel)_?(thickness|radius|size)?$',
        r'^(margin|offset|spacing|gap|clearance)$',
        r'^(inner|outer)_?(diameter|radius|width|height)?$',
        # Match anything ending with dimension-related suffixes
        r'.*(length|width|height|depth|thickness|diameter|radius|size|mm|cm)$',
        # Match anything starting with dimension-related prefixes
        r'^(min|max|total|base|top|bottom|left|right|front|back)_',
    ]
    
    def extract_parameters(self, code: str) -> list[dict[str, Any]]:
        """Extract numeric parameters from the beginning of CadQuery code."""
        parameters = []
        
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return parameters
        
        for node in ast.iter_child_nodes(tree):
            # Stop at first non-assignment (usually the CadQuery chain)
            if not isinstance(node, ast.Assign):
                # Allow import statements
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    continue
                # Allow comments (Expr with Constant string)
                if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
                    continue
                break
            
            # Check if this is a simple numeric assignment
            if len(node.targets) != 1:
                continue
            
            target = node.targets[0]
            if not isinstance(target, ast.Name):
                continue
            
            name = target.id
            value = node.value
            
            # Extract numeric value
            if isinstance(value, ast.Constant) and isinstance(value.value, (int, float)):
                if self._is_dimension_parameter(name):
                    parameters.append({
                        "name": name,
                        "value": float(value.value),
                        "unit": "mm",
                        "line": node.lineno,
                    })
            elif isinstance(value, ast.UnaryOp) and isinstance(value.op, ast.USub):
                # Handle negative numbers
                if isinstance(value.operand, ast.Constant) and isinstance(value.operand.value, (int, float)):
                    if self._is_dimension_parameter(name):
                        parameters.append({
                            "name": name,
                            "value": -float(value.operand.value),
                            "unit": "mm",
                            "line": node.lineno,
                        })
        
        return parameters
    
    def _is_dimension_parameter(self, name: str) -> bool:
        """Check if a variable name looks like a dimension parameter."""
        name_lower = name.lower()
        
        # Skip common non-dimension variables
        skip_names = {'result', 'cq', 'workplane', 'shape', 'model', 'part', 'i', 'j', 'n', 'count'}
        if name_lower in skip_names:
            return False
        
        # Check against patterns
        for pattern in self.DIMENSION_PATTERNS:
            if re.match(pattern, name_lower, re.IGNORECASE):
                return True
        
        # If it's a simple name and numeric, likely a dimension
        if name_lower.isalpha() and len(name_lower) <= 20:
            return True
        
        return False
    
    def validate_parameters(self, parameters: dict[str, float]) -> tuple[bool, str | None]:
        """Validate parameter values to prevent common errors."""
        for name, value in parameters.items():
            # Check for zero or negative values in dimension parameters
            if value <= 0:
                return False, f"Le paramètre '{name}' doit être supérieur à 0 (valeur actuelle: {value})"
            
            # Check for very small values that could cause precision issues
            if value < 0.01:
                return False, f"Le paramètre '{name}' est trop petit (minimum 0.01mm)"
            
            # Check for unreasonably large values
            if value > 10000:
                return False, f"Le paramètre '{name}' est trop grand (maximum 10000mm)"
        
        return True, None

    def inject_parameters(self, code: str, new_values: dict[str, float]) -> str:
        """Inject new parameter values into the code."""
        lines = code.split('\n')
        
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return code
        
        # Map line numbers to new values
        replacements = {}
        
        for node in ast.iter_child_nodes(tree):
            if not isinstance(node, ast.Assign):
                if isinstance(node, (ast.Import, ast.ImportFrom, ast.Expr)):
                    continue
                break
            
            if len(node.targets) != 1:
                continue
            
            target = node.targets[0]
            if not isinstance(target, ast.Name):
                continue
            
            name = target.id
            
            if name in new_values:
                # Get the line and replace the value
                line_idx = node.lineno - 1  # 0-indexed
                old_line = lines[line_idx]
                
                # Create new line with updated value
                new_value = new_values[name]
                # Format as integer if whole number, otherwise float
                if new_value == int(new_value):
                    value_str = str(int(new_value))
                else:
                    value_str = str(new_value)
                
                # Replace the value in the assignment
                # Pattern: name = value or name=value
                new_line = re.sub(
                    rf'^(\s*{re.escape(name)}\s*=\s*)[\d\.\-]+',
                    rf'\g<1>{value_str}',
                    old_line
                )
                replacements[line_idx] = new_line
        
        # Apply replacements
        for line_idx, new_line in replacements.items():
            lines[line_idx] = new_line
        
        return '\n'.join(lines)


parameter_service = ParameterService()
