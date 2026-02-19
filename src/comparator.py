"""
Comparator - Find mismatches between code and documentation.
"""

import json
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Set, Tuple
from enum import Enum
from pathlib import Path

from .parser import ParseResult, FunctionSignature, ClassSignature, Parameter
from .doc_parser import DocParseResult, DocumentedItem


class DriftSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class DriftType(Enum):
    UNDOCUMENTED_FUNCTION = "undocumented_function"
    UNDOCUMENTED_CLASS = "undocumented_class"
    MISSING_FROM_CODE = "missing_from_code"
    SIGNATURE_MISMATCH = "signature_mismatch"
    PARAMETER_MISMATCH = "parameter_mismatch"
    RETURN_TYPE_MISMATCH = "return_type_mismatch"
    DEPRECATED_STILL_DOCUMENTED = "deprecated_still_documented"
    MISSING_DEPRECATION_NOTICE = "missing_deprecation_notice"
    DOCSTRING_MISSING = "docstring_missing"
    STALE_EXAMPLE = "stale_example"


@dataclass
class DriftIssue:
    """A single documentation drift issue."""
    drift_type: DriftType
    severity: DriftSeverity
    message: str
    code_location: Optional[str] = None
    code_line: Optional[int] = None
    doc_location: Optional[str] = None
    doc_line: Optional[int] = None
    item_name: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    suggestion: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'drift_type': self.drift_type.value,
            'severity': self.severity.value,
            'message': self.message,
            'code_location': self.code_location,
            'code_line': self.code_line,
            'doc_location': self.doc_location,
            'doc_line': self.doc_line,
            'item_name': self.item_name,
            'details': self.details,
            'suggestion': self.suggestion,
        }


@dataclass
class ComparisonResult:
    """Result of comparing code to documentation."""
    issues: List[DriftIssue] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=dict)
    
    def add_issue(self, issue: DriftIssue) -> None:
        self.issues.append(issue)
    
    @property
    def has_critical(self) -> bool:
        return any(i.severity == DriftSeverity.CRITICAL for i in self.issues)
    
    @property
    def has_warnings(self) -> bool:
        return any(i.severity == DriftSeverity.WARNING for i in self.issues)
    
    def filter_by_severity(self, severity: DriftSeverity) -> List[DriftIssue]:
        return [i for i in self.issues if i.severity == severity]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'issues': [i.to_dict() for i in self.issues],
            'stats': self.stats,
            'summary': {
                'total': len(self.issues),
                'critical': len(self.filter_by_severity(DriftSeverity.CRITICAL)),
                'warning': len(self.filter_by_severity(DriftSeverity.WARNING)),
                'info': len(self.filter_by_severity(DriftSeverity.INFO)),
            }
        }


class Comparator:
    """Compare code signatures with documentation."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.ignore_patterns = self.config.get('ignore_patterns', [
            '__init__', '__str__', '__repr__', '__eq__', '__hash__',
            '_*',  # Private methods
        ])
        self.require_docstrings = self.config.get('require_docstrings', True)
        self.check_parameters = self.config.get('check_parameters', True)
        self.check_return_types = self.config.get('check_return_types', True)
    
    def compare(self, code_results: List[ParseResult], 
                doc_results: List[DocParseResult]) -> ComparisonResult:
        """Compare code parsing results with documentation parsing results."""
        result = ComparisonResult()
        
        # Build indexes
        code_functions = self._index_functions(code_results)
        code_classes = self._index_classes(code_results)
        doc_items = self._index_doc_items(doc_results)
        
        # Track what we've matched
        matched_docs = set()
        
        # Check each code function
        for name, func in code_functions.items():
            if self._should_ignore(name):
                continue
            
            doc_item = self._find_doc_item(name, doc_items)
            
            if doc_item:
                matched_docs.add(doc_item.name)
                # Check for mismatches
                self._check_function_drift(func, doc_item, result)
            else:
                # Undocumented function
                if not func.docstring and self.require_docstrings:
                    result.add_issue(DriftIssue(
                        drift_type=DriftType.UNDOCUMENTED_FUNCTION,
                        severity=self._get_severity_for_undocumented(func),
                        message=f"Function '{name}' is not documented",
                        code_location=func.filepath,
                        code_line=func.line_number,
                        item_name=name,
                        suggestion=f"Add documentation for {name}() in your docs",
                    ))
        
        # Check each code class
        for name, cls in code_classes.items():
            if self._should_ignore(name):
                continue
            
            doc_item = self._find_doc_item(name, doc_items)
            
            if doc_item:
                matched_docs.add(doc_item.name)
                self._check_class_drift(cls, doc_item, result)
            else:
                if not cls.docstring and self.require_docstrings:
                    result.add_issue(DriftIssue(
                        drift_type=DriftType.UNDOCUMENTED_CLASS,
                        severity=DriftSeverity.WARNING,
                        message=f"Class '{name}' is not documented",
                        code_location=cls.filepath,
                        code_line=cls.line_number,
                        item_name=name,
                        suggestion=f"Add documentation for class {name}",
                    ))
        
        # Check for documented items missing from code
        for name, doc_item in doc_items.items():
            if name not in matched_docs:
                # Check if it's in code at all
                if name not in code_functions and name not in code_classes:
                    if not self._is_external_reference(doc_item):
                        result.add_issue(DriftIssue(
                            drift_type=DriftType.MISSING_FROM_CODE,
                            severity=DriftSeverity.CRITICAL,
                            message=f"Documented item '{name}' not found in code",
                            doc_location=doc_item.filepath,
                            doc_line=doc_item.line_number,
                            item_name=name,
                            suggestion=f"Remove or update documentation for '{name}' - it may have been renamed or deleted",
                        ))
        
        # Calculate stats
        result.stats = {
            'total_functions': len(code_functions),
            'total_classes': len(code_classes),
            'total_documented': len(doc_items),
            'matched': len(matched_docs),
            'undocumented': len(code_functions) + len(code_classes) - len(matched_docs),
        }
        
        return result
    
    def _index_functions(self, results: List[ParseResult]) -> Dict[str, FunctionSignature]:
        """Create an index of all functions by name."""
        index = {}
        for result in results:
            for func in result.functions:
                index[func.full_name] = func
                if func.class_name:
                    index[func.name] = func  # Also index by short name
            
            for cls in result.classes:
                for method in cls.methods:
                    index[method.full_name] = method
        
        return index
    
    def _index_classes(self, results: List[ParseResult]) -> Dict[str, ClassSignature]:
        """Create an index of all classes by name."""
        index = {}
        for result in results:
            for cls in result.classes:
                index[cls.name] = cls
        return index
    
    def _index_doc_items(self, results: List[DocParseResult]) -> Dict[str, DocumentedItem]:
        """Create an index of all documented items by name."""
        index = {}
        for result in results:
            for item in result.items:
                index[item.name] = item
        return index
    
    def _find_doc_item(self, name: str, doc_items: Dict[str, DocumentedItem]) -> Optional[DocumentedItem]:
        """Find documentation for a code item."""
        # Direct match
        if name in doc_items:
            return doc_items[name]
        
        # Try without class prefix
        if '.' in name:
            short_name = name.split('.')[-1]
            if short_name in doc_items:
                return doc_items[short_name]
        
        # Case-insensitive match
        name_lower = name.lower()
        for doc_name, item in doc_items.items():
            if doc_name.lower() == name_lower:
                return item
        
        return None
    
    def _should_ignore(self, name: str) -> bool:
        """Check if a name should be ignored based on patterns."""
        for pattern in self.ignore_patterns:
            if pattern.endswith('*'):
                if name.startswith(pattern[:-1]):
                    return True
            elif pattern.startswith('*'):
                if name.endswith(pattern[1:]):
                    return True
            elif name == pattern:
                return True
        return False
    
    def _get_severity_for_undocumented(self, func: FunctionSignature) -> DriftSeverity:
        """Determine severity for undocumented function."""
        # Public APIs are more critical
        if not func.name.startswith('_'):
            # Check for @api decorator or similar
            if any('api' in d.lower() or 'public' in d.lower() for d in func.decorators):
                return DriftSeverity.CRITICAL
            return DriftSeverity.WARNING
        return DriftSeverity.INFO
    
    def _check_function_drift(self, func: FunctionSignature, 
                               doc_item: DocumentedItem, 
                               result: ComparisonResult) -> None:
        """Check for drift between a function and its documentation."""
        
        # Check parameter count
        if self.check_parameters and doc_item.parameters:
            doc_param_names = {p['name'] for p in doc_item.parameters}
            code_param_names = {p.name for p in func.parameters if p.name != 'self'}
            
            # Missing from docs
            missing_in_docs = code_param_names - doc_param_names
            if missing_in_docs:
                result.add_issue(DriftIssue(
                    drift_type=DriftType.PARAMETER_MISMATCH,
                    severity=DriftSeverity.WARNING,
                    message=f"Parameters {missing_in_docs} not documented for '{func.full_name}'",
                    code_location=func.filepath,
                    code_line=func.line_number,
                    doc_location=doc_item.filepath,
                    doc_line=doc_item.line_number,
                    item_name=func.full_name,
                    details={'missing_params': list(missing_in_docs)},
                    suggestion=f"Add documentation for parameters: {', '.join(missing_in_docs)}",
                ))
            
            # Extra in docs (removed from code)
            extra_in_docs = doc_param_names - code_param_names
            if extra_in_docs:
                result.add_issue(DriftIssue(
                    drift_type=DriftType.PARAMETER_MISMATCH,
                    severity=DriftSeverity.CRITICAL,
                    message=f"Documented parameters {extra_in_docs} don't exist in '{func.full_name}'",
                    code_location=func.filepath,
                    code_line=func.line_number,
                    doc_location=doc_item.filepath,
                    doc_line=doc_item.line_number,
                    item_name=func.full_name,
                    details={'extra_params': list(extra_in_docs)},
                    suggestion=f"Remove documentation for deleted parameters: {', '.join(extra_in_docs)}",
                ))
        
        # Check deprecation status
        if doc_item.deprecated:
            # Check if code has deprecation decorator
            has_deprecation = any('deprecat' in d.lower() for d in func.decorators)
            if not has_deprecation:
                result.add_issue(DriftIssue(
                    drift_type=DriftType.MISSING_DEPRECATION_NOTICE,
                    severity=DriftSeverity.INFO,
                    message=f"'{func.full_name}' is marked deprecated in docs but not in code",
                    code_location=func.filepath,
                    code_line=func.line_number,
                    item_name=func.full_name,
                    suggestion="Add @deprecated decorator to the function",
                ))
    
    def _check_class_drift(self, cls: ClassSignature, 
                            doc_item: DocumentedItem, 
                            result: ComparisonResult) -> None:
        """Check for drift between a class and its documentation."""
        # Similar checks as functions
        if doc_item.deprecated:
            has_deprecation = any('deprecat' in d.lower() for d in cls.decorators)
            if not has_deprecation:
                result.add_issue(DriftIssue(
                    drift_type=DriftType.MISSING_DEPRECATION_NOTICE,
                    severity=DriftSeverity.INFO,
                    message=f"Class '{cls.name}' is marked deprecated in docs but not in code",
                    code_location=cls.filepath,
                    code_line=cls.line_number,
                    item_name=cls.name,
                ))
    
    def _is_external_reference(self, doc_item: DocumentedItem) -> bool:
        """Check if a documented item is an external reference (not expected in code)."""
        # API endpoints are typically not direct code references
        if doc_item.doc_type == 'api_endpoint':
            return True
        
        # Check description for hints
        if doc_item.description:
            external_hints = ['external', 'third-party', 'library', 'package']
            return any(hint in doc_item.description.lower() for hint in external_hints)
        
        return False


def compare_paths(code_path: Path, doc_path: Path, 
                  config: Optional[Dict[str, Any]] = None) -> ComparisonResult:
    """Convenience function to compare code and doc directories."""
    from .parser import CodeParser
    from .doc_parser import DocParser
    
    code_parser = CodeParser()
    doc_parser = DocParser()
    comparator = Comparator(config)
    
    code_results = code_parser.parse_directory(code_path)
    doc_results = doc_parser.parse_directory(doc_path)
    
    return comparator.compare(code_results, doc_results)


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python comparator.py <code_dir> <docs_dir>")
        sys.exit(1)
    
    code_path = Path(sys.argv[1])
    doc_path = Path(sys.argv[2])
    
    result = compare_paths(code_path, doc_path)
    print(json.dumps(result.to_dict(), indent=2))
