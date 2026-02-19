"""
Documentation Parser - Extract documented functions/classes from Markdown, RST, and docstrings.
"""

import re
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Set
from enum import Enum


class DocFormat(Enum):
    MARKDOWN = "markdown"
    RST = "rst"
    UNKNOWN = "unknown"


@dataclass
class DocumentedItem:
    """A documented function, class, or API endpoint."""
    name: str
    filepath: str
    line_number: int
    doc_type: str  # 'function', 'class', 'method', 'api_endpoint'
    description: Optional[str] = None
    parameters: List[Dict[str, str]] = field(default_factory=list)
    return_type: Optional[str] = None
    examples: List[str] = field(default_factory=list)
    deprecated: bool = False
    since_version: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'filepath': self.filepath,
            'line_number': self.line_number,
            'doc_type': self.doc_type,
            'description': self.description,
            'parameters': self.parameters,
            'return_type': self.return_type,
            'examples': self.examples,
            'deprecated': self.deprecated,
            'since_version': self.since_version,
        }


@dataclass
class DocParseResult:
    """Result of parsing a documentation file."""
    filepath: str
    format: DocFormat
    items: List[DocumentedItem] = field(default_factory=list)
    sections: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'filepath': self.filepath,
            'format': self.format.value,
            'items': [item.to_dict() for item in self.items],
            'sections': self.sections,
            'errors': self.errors,
        }


class MarkdownParser:
    """Parse Markdown documentation files."""
    
    # Pattern for code blocks with function definitions
    CODE_BLOCK_PATTERN = re.compile(r'```(\w+)?\n([\s\S]*?)```', re.MULTILINE)
    
    # Pattern for function documentation headers
    FUNC_HEADER_PATTERN = re.compile(r'^#{1,4}\s+`?(\w+(?:\.\w+)?)\s*\(([^)]*)\)`?', re.MULTILINE)
    
    # Pattern for API endpoint documentation
    API_PATTERN = re.compile(r'^#{1,4}\s+(GET|POST|PUT|DELETE|PATCH)\s+`?([/\w{}:-]+)`?', re.MULTILINE)
    
    # Pattern for deprecated markers
    DEPRECATED_PATTERN = re.compile(r'\*?\*?(?:DEPRECATED|Deprecated)\*?\*?', re.IGNORECASE)
    
    # Pattern for @since version
    SINCE_PATTERN = re.compile(r'@since\s+v?([\d.]+)')
    
    # Pattern for section headers
    SECTION_PATTERN = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
    
    def parse_file(self, filepath: Path) -> DocParseResult:
        result = DocParseResult(filepath=str(filepath), format=DocFormat.MARKDOWN)
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            result.errors.append(f"Read error: {e}")
            return result
        
        lines = content.split('\n')
        
        # Extract sections
        for match in self.SECTION_PATTERN.finditer(content):
            result.sections.append(match.group(2).strip())
        
        # Parse function documentation
        for match in self.FUNC_HEADER_PATTERN.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            name = match.group(1)
            params_str = match.group(2)
            
            # Get description from following lines
            description = self._extract_description(lines, line_num)
            
            # Parse parameters from description
            params = self._extract_params_from_section(content, match.end())
            
            # Check for deprecation
            section_content = content[match.start():match.start()+500]
            deprecated = bool(self.DEPRECATED_PATTERN.search(section_content))
            
            # Check for version
            since_match = self.SINCE_PATTERN.search(section_content)
            since_version = since_match.group(1) if since_match else None
            
            item = DocumentedItem(
                name=name,
                filepath=str(filepath),
                line_number=line_num,
                doc_type='function',
                description=description,
                parameters=params,
                deprecated=deprecated,
                since_version=since_version,
            )
            result.items.append(item)
        
        # Parse API endpoints
        for match in self.API_PATTERN.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            method = match.group(1)
            endpoint = match.group(2)
            
            description = self._extract_description(lines, line_num)
            
            item = DocumentedItem(
                name=f"{method} {endpoint}",
                filepath=str(filepath),
                line_number=line_num,
                doc_type='api_endpoint',
                description=description,
            )
            result.items.append(item)
        
        # Parse code blocks for documented examples
        for match in self.CODE_BLOCK_PATTERN.finditer(content):
            lang = match.group(1) or 'text'
            code = match.group(2)
            
            # Look for function definitions in code examples
            self._extract_from_code_block(code, lang, result, 
                                          content[:match.start()].count('\n') + 1,
                                          str(filepath))
        
        return result
    
    def _extract_description(self, lines: List[str], start_line: int) -> Optional[str]:
        """Extract description from lines following a header."""
        description_lines = []
        for i in range(start_line, min(start_line + 10, len(lines))):
            line = lines[i].strip()
            if line.startswith('#'):
                break
            if line and not line.startswith('```'):
                description_lines.append(line)
            elif description_lines:
                break
        
        return ' '.join(description_lines) if description_lines else None
    
    def _extract_params_from_section(self, content: str, start_pos: int) -> List[Dict[str, str]]:
        """Extract parameter documentation from a section."""
        params = []
        
        # Look for parameter lists
        param_pattern = re.compile(r'[-*]\s+`?(\w+)`?\s*(?:\(([^)]+)\))?\s*[-:]\s*(.+)')
        
        # Find the next section or end
        next_section = re.search(r'\n#{1,6}\s', content[start_pos:])
        section_end = start_pos + next_section.start() if next_section else len(content)
        section_content = content[start_pos:section_end]
        
        for match in param_pattern.finditer(section_content):
            params.append({
                'name': match.group(1),
                'type': match.group(2) or '',
                'description': match.group(3).strip(),
            })
        
        return params
    
    def _extract_from_code_block(self, code: str, lang: str, result: DocParseResult,
                                  line_num: int, filepath: str) -> None:
        """Extract function signatures from code blocks."""
        if lang in ('python', 'py'):
            # Python function pattern
            pattern = re.compile(r'def\s+(\w+)\s*\(([^)]*)\)')
            for match in pattern.finditer(code):
                name = match.group(1)
                if not any(item.name == name for item in result.items):
                    result.items.append(DocumentedItem(
                        name=name,
                        filepath=filepath,
                        line_number=line_num,
                        doc_type='function',
                        description='Documented in code example',
                    ))
        
        elif lang in ('javascript', 'js', 'typescript', 'ts'):
            # JavaScript function pattern
            pattern = re.compile(r'(?:function\s+(\w+)|const\s+(\w+)\s*=)')
            for match in pattern.finditer(code):
                name = match.group(1) or match.group(2)
                if name and not any(item.name == name for item in result.items):
                    result.items.append(DocumentedItem(
                        name=name,
                        filepath=filepath,
                        line_number=line_num,
                        doc_type='function',
                        description='Documented in code example',
                    ))


class RSTParser:
    """Parse reStructuredText documentation files."""
    
    # Pattern for function/class directives
    DIRECTIVE_PATTERN = re.compile(r'^\.\.\s+(function|class|method|py:function|py:class|py:method)::\s+(.+)$', re.MULTILINE)
    
    # Pattern for deprecated directive
    DEPRECATED_PATTERN = re.compile(r'^\.\.\s+deprecated::', re.MULTILINE)
    
    # Pattern for version added
    VERSION_PATTERN = re.compile(r'^\.\.\s+versionadded::\s+(.+)$', re.MULTILINE)
    
    # Pattern for section headers (underlined)
    SECTION_PATTERN = re.compile(r'^(.+)\n([=\-~^]+)$', re.MULTILINE)
    
    def parse_file(self, filepath: Path) -> DocParseResult:
        result = DocParseResult(filepath=str(filepath), format=DocFormat.RST)
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            result.errors.append(f"Read error: {e}")
            return result
        
        lines = content.split('\n')
        
        # Extract sections
        for match in self.SECTION_PATTERN.finditer(content):
            title = match.group(1).strip()
            if len(match.group(2)) >= len(title):
                result.sections.append(title)
        
        # Parse directives
        for match in self.DIRECTIVE_PATTERN.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            directive_type = match.group(1).replace('py:', '')
            signature = match.group(2).strip()
            
            # Extract name from signature
            name_match = re.match(r'(\w+(?:\.\w+)?)', signature)
            name = name_match.group(1) if name_match else signature
            
            # Get description from indented block
            description = self._extract_indented_block(lines, line_num)
            
            # Check for deprecation in following lines
            section_content = content[match.start():match.start()+500]
            deprecated = bool(self.DEPRECATED_PATTERN.search(section_content))
            
            # Check for version
            version_match = self.VERSION_PATTERN.search(section_content)
            since_version = version_match.group(1).strip() if version_match else None
            
            item = DocumentedItem(
                name=name,
                filepath=str(filepath),
                line_number=line_num,
                doc_type=directive_type,
                description=description,
                deprecated=deprecated,
                since_version=since_version,
            )
            result.items.append(item)
        
        return result
    
    def _extract_indented_block(self, lines: List[str], start_line: int) -> Optional[str]:
        """Extract the indented description block."""
        description_lines = []
        
        for i in range(start_line, min(start_line + 20, len(lines))):
            line = lines[i]
            if line.startswith('   ') or line.startswith('\t'):
                text = line.strip()
                if text and not text.startswith(':'):
                    description_lines.append(text)
            elif description_lines and not line.strip():
                continue
            elif description_lines:
                break
        
        return ' '.join(description_lines) if description_lines else None


class DocParser:
    """Main documentation parser that dispatches to format-specific parsers."""
    
    FORMAT_MAP = {
        '.md': DocFormat.MARKDOWN,
        '.markdown': DocFormat.MARKDOWN,
        '.rst': DocFormat.RST,
        '.txt': DocFormat.UNKNOWN,
    }
    
    def __init__(self):
        self.markdown_parser = MarkdownParser()
        self.rst_parser = RSTParser()
    
    def parse_file(self, filepath: Path) -> Optional[DocParseResult]:
        suffix = filepath.suffix.lower()
        format = self.FORMAT_MAP.get(suffix, DocFormat.UNKNOWN)
        
        if format == DocFormat.MARKDOWN:
            return self.markdown_parser.parse_file(filepath)
        elif format == DocFormat.RST:
            return self.rst_parser.parse_file(filepath)
        
        return None
    
    def parse_directory(self, directory: Path,
                        exclude_patterns: Optional[List[str]] = None) -> List[DocParseResult]:
        results = []
        exclude_patterns = exclude_patterns or ['node_modules', '__pycache__', '.git', 'venv']
        
        for filepath in directory.rglob('*'):
            if filepath.is_file():
                if any(pattern in str(filepath) for pattern in exclude_patterns):
                    continue
                
                result = self.parse_file(filepath)
                if result:
                    results.append(result)
        
        return results
    
    def get_all_documented_names(self, results: List[DocParseResult]) -> Set[str]:
        """Get all documented item names from parse results."""
        names = set()
        for result in results:
            for item in result.items:
                names.add(item.name)
                # Also add without class prefix
                if '.' in item.name:
                    names.add(item.name.split('.')[-1])
        return names
    
    def to_json(self, results: List[DocParseResult]) -> str:
        return json.dumps([r.to_dict() for r in results], indent=2)


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python doc_parser.py <file_or_directory>")
        sys.exit(1)
    
    path = Path(sys.argv[1])
    parser = DocParser()
    
    if path.is_file():
        result = parser.parse_file(path)
        if result:
            print(json.dumps(result.to_dict(), indent=2))
    else:
        results = parser.parse_directory(path)
        print(parser.to_json(results))
