"""
Code Parser - Extract function/class signatures from Python and JavaScript files.
Uses AST for Python and regex-based parsing for JavaScript.
"""

import ast
import re
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any


@dataclass
class Parameter:
    """Function parameter with optional type annotation."""
    name: str
    type_hint: Optional[str] = None
    default: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FunctionSignature:
    """Represents a function or method signature."""
    name: str
    filepath: str
    line_number: int
    parameters: List[Parameter] = field(default_factory=list)
    return_type: Optional[str] = None
    docstring: Optional[str] = None
    is_async: bool = False
    is_method: bool = False
    class_name: Optional[str] = None
    decorators: List[str] = field(default_factory=list)
    
    @property
    def full_name(self) -> str:
        if self.class_name:
            return f"{self.class_name}.{self.name}"
        return self.name
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['full_name'] = self.full_name
        return d


@dataclass
class ClassSignature:
    """Represents a class definition."""
    name: str
    filepath: str
    line_number: int
    bases: List[str] = field(default_factory=list)
    docstring: Optional[str] = None
    methods: List[FunctionSignature] = field(default_factory=list)
    decorators: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        d = {
            'name': self.name,
            'filepath': self.filepath,
            'line_number': self.line_number,
            'bases': self.bases,
            'docstring': self.docstring,
            'decorators': self.decorators,
            'methods': [m.to_dict() for m in self.methods]
        }
        return d


@dataclass
class ParseResult:
    """Result of parsing a code file."""
    filepath: str
    language: str
    functions: List[FunctionSignature] = field(default_factory=list)
    classes: List[ClassSignature] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'filepath': self.filepath,
            'language': self.language,
            'functions': [f.to_dict() for f in self.functions],
            'classes': [c.to_dict() for c in self.classes],
            'exports': self.exports,
            'errors': self.errors
        }


class PythonParser:
    """Parse Python files using the AST module."""
    
    def parse_file(self, filepath: Path) -> ParseResult:
        result = ParseResult(filepath=str(filepath), language='python')
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                source = f.read()
            tree = ast.parse(source)
        except SyntaxError as e:
            result.errors.append(f"Syntax error: {e}")
            return result
        except Exception as e:
            result.errors.append(f"Parse error: {e}")
            return result
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                if self._is_top_level(tree, node):
                    func = self._parse_function(node, str(filepath))
                    result.functions.append(func)
            
            elif isinstance(node, ast.ClassDef):
                cls = self._parse_class(node, str(filepath))
                result.classes.append(cls)
        
        return result
    
    def _is_top_level(self, tree: ast.Module, target: ast.AST) -> bool:
        """Check if a function is at module level."""
        for node in ast.iter_child_nodes(tree):
            if node is target:
                return True
        return False
    
    def _parse_function(self, node: ast.FunctionDef, filepath: str, 
                        class_name: Optional[str] = None) -> FunctionSignature:
        params = []
        for arg in node.args.args:
            param = Parameter(
                name=arg.arg,
                type_hint=ast.unparse(arg.annotation) if arg.annotation else None
            )
            params.append(param)
        
        defaults = node.args.defaults
        if defaults:
            offset = len(params) - len(defaults)
            for i, default in enumerate(defaults):
                params[offset + i].default = ast.unparse(default)
        
        return FunctionSignature(
            name=node.name,
            filepath=filepath,
            line_number=node.lineno,
            parameters=params,
            return_type=ast.unparse(node.returns) if node.returns else None,
            docstring=ast.get_docstring(node),
            is_async=isinstance(node, ast.AsyncFunctionDef),
            is_method=class_name is not None,
            class_name=class_name,
            decorators=[ast.unparse(d) for d in node.decorator_list]
        )
    
    def _parse_class(self, node: ast.ClassDef, filepath: str) -> ClassSignature:
        methods = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method = self._parse_function(item, filepath, class_name=node.name)
                methods.append(method)
        
        return ClassSignature(
            name=node.name,
            filepath=filepath,
            line_number=node.lineno,
            bases=[ast.unparse(base) for base in node.bases],
            docstring=ast.get_docstring(node),
            methods=methods,
            decorators=[ast.unparse(d) for d in node.decorator_list]
        )


class JavaScriptParser:
    """Parse JavaScript/TypeScript files using regex patterns."""
    
    FUNCTION_PATTERNS = [
        re.compile(r'^(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)(?:\s*:\s*([^{]+))?', re.MULTILINE),
        re.compile(r'^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(([^)]*)\)(?:\s*:\s*([^=]+))?\s*=>', re.MULTILINE),
        re.compile(r'^\s+(?:async\s+)?(\w+)\s*\(([^)]*)\)(?:\s*:\s*([^{]+))?\s*\{', re.MULTILINE),
    ]
    
    CLASS_PATTERN = re.compile(r'^(?:export\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?', re.MULTILINE)
    JSDOC_PATTERN = re.compile(r'/\*\*\s*([\s\S]*?)\s*\*/', re.MULTILINE)
    
    def parse_file(self, filepath: Path) -> ParseResult:
        result = ParseResult(filepath=str(filepath), language='javascript')
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                source = f.read()
        except Exception as e:
            result.errors.append(f"Read error: {e}")
            return result
        
        jsdocs = {}
        for match in self.JSDOC_PATTERN.finditer(source):
            end_line = source[:match.end()].count('\n') + 1
            jsdocs[end_line] = match.group(1).strip()
        
        for pattern in self.FUNCTION_PATTERNS:
            for match in pattern.finditer(source):
                line_num = source[:match.start()].count('\n') + 1
                name = match.group(1)
                params_str = match.group(2).strip()
                return_type = match.group(3).strip() if match.lastindex >= 3 and match.group(3) else None
                
                params = self._parse_params(params_str)
                docstring = jsdocs.get(line_num - 1) or jsdocs.get(line_num)
                
                func = FunctionSignature(
                    name=name,
                    filepath=str(filepath),
                    line_number=line_num,
                    parameters=params,
                    return_type=return_type,
                    docstring=docstring,
                    is_async='async' in source[max(0, match.start()-20):match.start()]
                )
                
                if not any(f.name == func.name and f.line_number == func.line_number 
                          for f in result.functions):
                    result.functions.append(func)
        
        for match in self.CLASS_PATTERN.finditer(source):
            line_num = source[:match.start()].count('\n') + 1
            name = match.group(1)
            base = match.group(2) if match.lastindex >= 2 else None
            docstring = jsdocs.get(line_num - 1)
            
            cls = ClassSignature(
                name=name,
                filepath=str(filepath),
                line_number=line_num,
                bases=[base] if base else [],
                docstring=docstring
            )
            result.classes.append(cls)
        
        export_pattern = re.compile(r'export\s+(?:default\s+)?(?:const|let|var|function|class)\s+(\w+)')
        for match in export_pattern.finditer(source):
            result.exports.append(match.group(1))
        
        return result
    
    def _parse_params(self, params_str: str) -> List[Parameter]:
        if not params_str:
            return []
        
        params = []
        depth = 0
        current = []
        for char in params_str:
            if char in '([{':
                depth += 1
            elif char in ')]}':
                depth -= 1
            elif char == ',' and depth == 0:
                params.append(''.join(current).strip())
                current = []
                continue
            current.append(char)
        if current:
            params.append(''.join(current).strip())
        
        result = []
        for param in params:
            if not param:
                continue
            if ':' in param:
                parts = param.split(':', 1)
                name = parts[0].strip()
                type_hint = parts[1].strip() if len(parts) > 1 else None
            else:
                name = param
                type_hint = None
            
            default = None
            if '=' in name:
                name, default = name.split('=', 1)
                name = name.strip()
                default = default.strip()
            
            result.append(Parameter(name=name, type_hint=type_hint, default=default))
        
        return result


class CodeParser:
    """Main parser that dispatches to language-specific parsers."""
    
    LANGUAGE_MAP = {
        '.py': 'python',
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.mjs': 'javascript',
    }
    
    def __init__(self):
        self.python_parser = PythonParser()
        self.js_parser = JavaScriptParser()
    
    def parse_file(self, filepath: Path) -> Optional[ParseResult]:
        suffix = filepath.suffix.lower()
        language = self.LANGUAGE_MAP.get(suffix)
        
        if language == 'python':
            return self.python_parser.parse_file(filepath)
        elif language in ('javascript', 'typescript'):
            return self.js_parser.parse_file(filepath)
        
        return None
    
    def parse_directory(self, directory: Path, 
                        exclude_patterns: Optional[List[str]] = None) -> List[ParseResult]:
        results = []
        exclude_patterns = exclude_patterns or ['node_modules', '__pycache__', '.git', 'venv', '.venv']
        
        for filepath in directory.rglob('*'):
            if filepath.is_file():
                if any(pattern in str(filepath) for pattern in exclude_patterns):
                    continue
                
                result = self.parse_file(filepath)
                if result:
                    results.append(result)
        
        return results
    
    def to_json(self, results: List[ParseResult]) -> str:
        return json.dumps([r.to_dict() for r in results], indent=2)


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python parser.py <file_or_directory>")
        sys.exit(1)
    
    path = Path(sys.argv[1])
    parser = CodeParser()
    
    if path.is_file():
        result = parser.parse_file(path)
        if result:
            print(json.dumps(result.to_dict(), indent=2))
    else:
        results = parser.parse_directory(path)
        print(parser.to_json(results))
