"""
Code Security Validation for Sandbox Execution
===============================================

Provides AST-based static analysis to validate code before execution.
This is a defense-in-depth layer - subprocess isolation is the primary security boundary.

Security Strategy:
1. Block dangerous patterns via regex (imports, dunders, builtins)
2. AST validation for structural analysis
3. Subprocess isolation provides OS-level containment
"""

import ast
import re
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of code validation."""
    is_safe: bool
    errors: List[str]
    warnings: List[str]

    @classmethod
    def safe(cls) -> 'ValidationResult':
        return cls(is_safe=True, errors=[], warnings=[])

    @classmethod
    def unsafe(cls, errors: List[str], warnings: Optional[List[str]] = None) -> 'ValidationResult':
        return cls(is_safe=False, errors=errors, warnings=warnings or [])


class CodeValidator:
    """
    Validates Python code for safe sandbox execution.

    This validator blocks:
    - Import statements (no external modules)
    - Dunder access (__name__, __class__, etc.)
    - Dangerous builtins (exec, eval, open, etc.)
    - Attribute introspection (getattr, setattr, etc.)
    """

    # Patterns that are always forbidden
    FORBIDDEN_PATTERNS = [
        (r'\bimport\b', "Import statements are not allowed"),
        (r'\b__[a-zA-Z_]+__\b', "Dunder attributes (__name__, __class__, etc.) are not allowed"),
        (r'\bopen\s*\(', "File operations (open) are not allowed"),
        (r'\bexec\s*\(', "exec() is not allowed"),
        (r'\beval\s*\(', "eval() is not allowed"),
        (r'\bcompile\s*\(', "compile() is not allowed"),
        (r'\bglobals\s*\(', "globals() is not allowed"),
        (r'\blocals\s*\(', "locals() is not allowed"),
        (r'\bgetattr\s*\(', "getattr() is not allowed"),
        (r'\bsetattr\s*\(', "setattr() is not allowed"),
        (r'\bdelattr\s*\(', "delattr() is not allowed"),
        (r'\bhasattr\s*\(', "hasattr() is not allowed"),
        (r'\bvars\s*\(', "vars() is not allowed"),
        (r'\bdir\s*\(', "dir() is not allowed"),
        (r'\bbreakpoint\s*\(', "breakpoint() is not allowed"),
        (r'\binput\s*\(', "input() is not allowed"),
        (r'\b__builtins__\b', "Access to __builtins__ is not allowed"),
        (r'\bos\s*\.', "os module access is not allowed"),
        (r'\bsys\s*\.', "sys module access is not allowed"),
        (r'\bsubprocess\s*\.', "subprocess module access is not allowed"),
    ]

    # Functions blocked from sandbox execution
    BLOCKED_FUNCTIONS = {
        'exec', 'eval', 'compile', 'open',
        'getattr', 'setattr', 'delattr', 'hasattr',
        'globals', 'locals', 'vars', 'dir',
        'breakpoint', 'input', '__import__',
    }

    # Allowed builtins that will be available in sandbox
    ALLOWED_BUILTINS = {
        # Type constructors
        'list', 'dict', 'set', 'tuple', 'str', 'int', 'float', 'bool', 'bytes',
        # Iteration helpers
        'len', 'range', 'enumerate', 'zip', 'map', 'filter', 'reversed',
        # Aggregation
        'min', 'max', 'sum', 'any', 'all', 'sorted',
        # Math
        'abs', 'round', 'pow', 'divmod',
        # Type checking
        'isinstance', 'type',
        # Output
        'print', 'repr', 'str',
        # Boolean
        'True', 'False', 'None',
    }

    def __init__(self, max_code_length: int = 10000):
        """
        Initialize the code validator.

        Args:
            max_code_length: Maximum allowed code length in characters
        """
        self.max_code_length = max_code_length
        self._compiled_patterns = [
            (re.compile(pattern), message)
            for pattern, message in self.FORBIDDEN_PATTERNS
        ]

    def validate(self, code: str) -> ValidationResult:
        """
        Validate code for sandbox execution.

        Args:
            code: Python code to validate

        Returns:
            ValidationResult indicating if code is safe to execute
        """
        errors = []
        warnings = []

        # Check 1: Code length
        if len(code) > self.max_code_length:
            return ValidationResult.unsafe([
                f"Code too long: {len(code)} chars (max {self.max_code_length})"
            ])

        # Check 2: Empty code
        if not code or not code.strip():
            return ValidationResult.unsafe(["Empty code provided"])

        # Check 3: Forbidden patterns (regex-based)
        for pattern, message in self._compiled_patterns:
            if pattern.search(code):
                errors.append(message)

        if errors:
            return ValidationResult.unsafe(errors)

        # Check 4: AST-based validation
        try:
            tree = ast.parse(code)
            ast_errors = self._validate_ast(tree)
            if ast_errors:
                return ValidationResult.unsafe(ast_errors)
        except SyntaxError as e:
            return ValidationResult.unsafe([f"Syntax error: {e.msg} at line {e.lineno}"])

        # Check 5: Verify 'result' assignment exists
        if not self._has_result_assignment(tree):
            warnings.append("Code should assign to 'result' variable to return data")

        return ValidationResult(is_safe=True, errors=[], warnings=warnings)

    def _validate_ast(self, tree: ast.AST) -> List[str]:
        """
        Validate AST for dangerous constructs.

        Args:
            tree: Parsed AST

        Returns:
            List of error messages (empty if safe)
        """
        errors = []

        for node in ast.walk(tree):
            match node:
                case ast.Import() | ast.ImportFrom():
                    errors.append("Import statements are not allowed")

                case ast.Call(func=ast.Name(id=func_name)) if func_name in self.BLOCKED_FUNCTIONS:
                    errors.append(f"Function '{func_name}' is not allowed")

                case ast.Attribute(attr=attr) if attr.startswith('__') and attr.endswith('__'):
                    errors.append(f"Dunder attribute access '{attr}' is not allowed")

                case ast.Lambda(body=body):
                    errors.extend(self._validate_ast(body))

        return errors

    def _has_result_assignment(self, tree: ast.AST) -> bool:
        """
        Check if code assigns to 'result' variable.

        Args:
            tree: Parsed AST

        Returns:
            True if 'result' is assigned
        """
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == 'result':
                        return True
            elif isinstance(node, ast.AnnAssign):
                if isinstance(node.target, ast.Name) and node.target.id == 'result':
                    return True
        return False

    def get_allowed_builtins_list(self) -> List[str]:
        """Return list of allowed builtin names."""
        return sorted(self.ALLOWED_BUILTINS)
