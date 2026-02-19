"""Tests for code parser."""

import tempfile
from pathlib import Path
import pytest

from src.parser import CodeParser, PythonParser, JavaScriptParser


class TestPythonParser:
    """Tests for Python code parsing."""
    
    def test_parse_simple_function(self):
        code = '''
def hello(name: str) -> str:
    """Say hello to someone."""
    return f"Hello, {name}!"
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            
            parser = PythonParser()
            result = parser.parse_file(Path(f.name))
            
            assert len(result.functions) == 1
            func = result.functions[0]
            assert func.name == 'hello'
            assert func.docstring == 'Say hello to someone.'
            assert func.return_type == 'str'
            assert len(func.parameters) == 1
            assert func.parameters[0].name == 'name'
            assert func.parameters[0].type_hint == 'str'
    
    def test_parse_class_with_methods(self):
        code = '''
class Calculator:
    """A simple calculator."""
    
    def add(self, a: int, b: int) -> int:
        """Add two numbers."""
        return a + b
    
    def subtract(self, a: int, b: int) -> int:
        """Subtract b from a."""
        return a - b
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            
            parser = PythonParser()
            result = parser.parse_file(Path(f.name))
            
            assert len(result.classes) == 1
            cls = result.classes[0]
            assert cls.name == 'Calculator'
            assert cls.docstring == 'A simple calculator.'
            assert len(cls.methods) == 2
            
            add_method = next(m for m in cls.methods if m.name == 'add')
            assert add_method.full_name == 'Calculator.add'
    
    def test_parse_async_function(self):
        code = '''
async def fetch_data(url: str) -> dict:
    """Fetch data from URL."""
    pass
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            
            parser = PythonParser()
            result = parser.parse_file(Path(f.name))
            
            assert len(result.functions) == 1
            func = result.functions[0]
            assert func.is_async
    
    def test_parse_decorated_function(self):
        code = '''
@deprecated
@api_endpoint('/users')
def get_users():
    """Get all users."""
    pass
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            
            parser = PythonParser()
            result = parser.parse_file(Path(f.name))
            
            func = result.functions[0]
            assert 'deprecated' in func.decorators
            assert len(func.decorators) == 2


class TestJavaScriptParser:
    """Tests for JavaScript code parsing."""
    
    def test_parse_function(self):
        code = '''
/**
 * Say hello to someone.
 * @param {string} name - The name
 * @returns {string} Greeting
 */
function hello(name) {
    return `Hello, ${name}!`;
}
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(code)
            f.flush()
            
            parser = JavaScriptParser()
            result = parser.parse_file(Path(f.name))
            
            assert len(result.functions) >= 1
            func = next(f for f in result.functions if f.name == 'hello')
            assert func.name == 'hello'
            assert func.docstring is not None
    
    def test_parse_arrow_function(self):
        code = '''
const add = (a, b) => {
    return a + b;
};
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(code)
            f.flush()
            
            parser = JavaScriptParser()
            result = parser.parse_file(Path(f.name))
            
            assert any(f.name == 'add' for f in result.functions)
    
    def test_parse_class(self):
        code = '''
/**
 * A calculator class.
 */
class Calculator extends BaseCalc {
    add(a, b) {
        return a + b;
    }
}
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(code)
            f.flush()
            
            parser = JavaScriptParser()
            result = parser.parse_file(Path(f.name))
            
            assert len(result.classes) == 1
            cls = result.classes[0]
            assert cls.name == 'Calculator'
            assert 'BaseCalc' in cls.bases
    
    def test_parse_exports(self):
        code = '''
export function publicFunc() {}
export const helper = () => {};
export class Widget {}
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(code)
            f.flush()
            
            parser = JavaScriptParser()
            result = parser.parse_file(Path(f.name))
            
            assert 'publicFunc' in result.exports
            assert 'helper' in result.exports
            assert 'Widget' in result.exports


class TestCodeParser:
    """Tests for main CodeParser."""
    
    def test_language_detection(self):
        parser = CodeParser()
        
        assert parser.LANGUAGE_MAP['.py'] == 'python'
        assert parser.LANGUAGE_MAP['.js'] == 'javascript'
        assert parser.LANGUAGE_MAP['.ts'] == 'typescript'
    
    def test_parse_directory(self, tmp_path):
        # Create test files
        py_file = tmp_path / "test.py"
        py_file.write_text("def foo(): pass")
        
        js_file = tmp_path / "test.js"
        js_file.write_text("function bar() {}")
        
        parser = CodeParser()
        results = parser.parse_directory(tmp_path)
        
        assert len(results) == 2
        
        py_result = next(r for r in results if r.language == 'python')
        assert any(f.name == 'foo' for f in py_result.functions)
    
    def test_exclude_patterns(self, tmp_path):
        # Create files in node_modules (should be excluded)
        nm_dir = tmp_path / "node_modules"
        nm_dir.mkdir()
        (nm_dir / "lib.js").write_text("function hidden() {}")
        
        # Create regular file
        (tmp_path / "main.js").write_text("function visible() {}")
        
        parser = CodeParser()
        results = parser.parse_directory(tmp_path)
        
        # Should only have main.js
        assert len(results) == 1
        assert 'node_modules' not in results[0].filepath
