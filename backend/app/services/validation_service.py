"""
Code validation and correction service for CadQuery code.
Catches common errors before execution and attempts auto-correction.
"""
import re
import ast
from dataclasses import dataclass


@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[str]
    warnings: list[str]
    corrected_code: str | None = None


class CodeValidator:
    """Validates and corrects CadQuery code before execution."""
    
    # Common errors and their fixes
    CORRECTIONS = [
        # Wrong method names
        (r'\.add\(', '.union('),
        (r'\.subtract\(', '.cut('),
        # Common typos
        (r'\.fillett\(', '.fillet('),
        (r'\.champher\(', '.chamfer('),
        (r'\.exturde\(', '.extrude('),
        # Wrong import statements
        (r'from cadquery import \*', 'import cadquery as cq'),
        (r'import CadQuery', 'import cadquery as cq'),
    ]
    
    # Dangerous patterns that could indicate hallucinated methods
    INVALID_METHODS = [
        'addSolid', 'createBox', 'makeBox', 'createCylinder', 'makeCyl',
        'addShape', 'appendShape', 'combineWith', 'subtractFrom',
        'moveBy', 'scaleBy', 'rotateBy', 'mirrorBy',
    ]
    
    def validate(self, code: str) -> ValidationResult:
        """Validate CadQuery code and return results with potential corrections."""
        errors = []
        warnings = []
        corrected_code = code
        
        # Check for import statement
        if 'import cadquery' not in code and 'from cadquery' not in code:
            errors.append("Missing CadQuery import statement")
            corrected_code = "import cadquery as cq\n\n" + corrected_code
        
        # Check for result variable
        if not self._has_result_variable(code):
            errors.append("Code does not define 'result' variable")
        
        # Check for syntax errors
        syntax_error = self._check_syntax(code)
        if syntax_error:
            errors.append(f"Syntax error: {syntax_error}")
        
        # Check for invalid/hallucinated methods
        for method in self.INVALID_METHODS:
            if f'.{method}(' in code:
                errors.append(f"Invalid method '{method}' - this does not exist in CadQuery")
        
        # Apply auto-corrections
        for pattern, replacement in self.CORRECTIONS:
            if re.search(pattern, corrected_code):
                warnings.append(f"Auto-corrected: {pattern} → {replacement}")
                corrected_code = re.sub(pattern, replacement, corrected_code)
        
        # Check for common anti-patterns
        antipattern_warnings = self._check_antipatterns(code)
        warnings.extend(antipattern_warnings)
        
        # Check for problematic fillet patterns on cylinders
        fillet_errors = self._check_cylinder_fillet(code)
        errors.extend(fillet_errors)
        
        # Check fillet/shell ordering
        order_warning = self._check_fillet_shell_order(code)
        if order_warning:
            warnings.append(order_warning)
        
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            corrected_code=corrected_code if corrected_code != code else None
        )
    
    def _has_result_variable(self, code: str) -> bool:
        """Check if code defines a 'result' variable."""
        # Simple check for result assignment
        patterns = [
            r'^result\s*=',      # result = ...
            r'\nresult\s*=',     # newline result = ...
        ]
        for pattern in patterns:
            if re.search(pattern, code, re.MULTILINE):
                return True
        return False
    
    def _check_syntax(self, code: str) -> str | None:
        """Check for Python syntax errors."""
        try:
            ast.parse(code)
            return None
        except SyntaxError as e:
            return f"Line {e.lineno}: {e.msg}"
    
    def _check_antipatterns(self, code: str) -> list[str]:
        """Check for common anti-patterns that might cause issues."""
        warnings = []
        
        # Check for very large fillet values
        fillet_match = re.search(r'\.fillet\((\d+(?:\.\d+)?)\)', code)
        if fillet_match:
            fillet_value = float(fillet_match.group(1))
            if fillet_value > 10:
                warnings.append(f"Large fillet radius ({fillet_value}mm) may cause errors - consider reducing")
        
        # Check for loft usage (often problematic)
        if '.loft(' in code:
            warnings.append("loft() can be unreliable - ensure sections are compatible")
        
        # Check for sweep usage
        if '.sweep(' in code:
            warnings.append("sweep() can fail on complex paths - test carefully")
        
        # Check for shell without face selection
        if re.search(r'\.shell\([^)]+\)\s*$', code, re.MULTILINE):
            shell_match = re.search(r'\.shell\(([^)]+)\)', code)
            if shell_match and '.faces(' not in code[:code.find('.shell(')]:
                warnings.append("shell() without face selection may give unexpected results")
        
        return warnings
    
    def _check_cylinder_fillet(self, code: str) -> list[str]:
        """Check for fillet on cylinder edges (common error)."""
        errors = []
        
        # Pattern: .cylinder(...) followed by .edges("|Z").fillet(...)
        if '.cylinder(' in code and '.edges("|Z")' in code:
            # Check if fillet/chamfer follows edges("|Z") selection
            pattern = r'\.edges\("\|Z"\)\s*\.(?:fillet|chamfer)\('
            if re.search(pattern, code):
                errors.append(
                    "Cannot use .edges(\"|Z\") on cylinders - they have no vertical edges. "
                    "Use .edges(\">Z\") or .edges(\"<Z\") for top/bottom edges instead."
                )
        
        return errors
    
    def _check_fillet_shell_order(self, code: str) -> str | None:
        """Check if fillet is applied after shell (usually wrong)."""
        # Find positions of shell and fillet
        shell_pos = code.find('.shell(')
        fillet_pos = code.rfind('.fillet(')  # Last fillet
        
        if shell_pos != -1 and fillet_pos != -1:
            if fillet_pos > shell_pos:
                return "fillet() applied after shell() - this often fails. Consider applying fillet before shell."
        
        return None
    
    def get_error_fix_suggestions(self, error_message: str) -> list[str]:
        """Return suggestions to fix common CadQuery errors."""
        suggestions = []
        error_lower = error_message.lower()
        
        if "brep_api: command not done" in error_lower:
            suggestions = [
                "Simplify the geometry - avoid complex loft/sweep operations",
                "Build shapes separately and combine with .union()",
                "Check that boolean operations (cut/union) involve intersecting shapes",
                "Reduce fillet/chamfer radii",
                "For organic shapes, use simple primitives (spheres, cylinders, boxes) combined",
            ]
        
        elif "no suitable edges" in error_lower or "fillet" in error_lower:
            suggestions = [
                "Check edge selector - .edges(\"|Z\") doesn't work on cylinders",
                "Reduce fillet radius - must be smaller than wall thickness",
                "Apply fillet BEFORE shell, not after",
                "Try .edges(\">Z or <Z\") for top/bottom edges",
                "Consider removing fillet entirely for reliability",
            ]
        
        elif "shell" in error_lower:
            suggestions = [
                "Reduce shell thickness - must be less than smallest dimension / 2",
                "Select a face to remove: .faces(\">Z\").shell(-thickness)",
                "Apply fillets BEFORE shell operation",
                "Simplify the base shape first",
            ]
        
        elif "syntax" in error_lower:
            suggestions = [
                "Check parentheses matching",
                "Verify method chaining syntax",
                "Check for missing commas in function arguments",
            ]
        
        elif "attribute" in error_lower or "has no attribute" in error_lower:
            suggestions = [
                "Verify the method name exists in CadQuery",
                "Check CadQuery documentation for correct method",
                "Ensure you're calling methods on the right object type",
            ]
        
        return suggestions


# Singleton instance
code_validator = CodeValidator()
