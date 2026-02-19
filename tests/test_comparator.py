"""Tests for comparator."""

import pytest

from src.parser import ParseResult, FunctionSignature, ClassSignature, Parameter
from src.doc_parser import DocParseResult, DocumentedItem, DocFormat
from src.comparator import Comparator, DriftSeverity, DriftType


def make_function(name: str, params: list = None, docstring: str = None,
                  filepath: str = "test.py", line: int = 1) -> FunctionSignature:
    """Helper to create function signatures."""
    return FunctionSignature(
        name=name,
        filepath=filepath,
        line_number=line,
        parameters=[Parameter(name=p) for p in (params or [])],
        docstring=docstring,
    )


def make_doc_item(name: str, params: list = None, 
                  filepath: str = "test.md", line: int = 1) -> DocumentedItem:
    """Helper to create documented items."""
    return DocumentedItem(
        name=name,
        filepath=filepath,
        line_number=line,
        doc_type='function',
        parameters=[{'name': p} for p in (params or [])],
    )


class TestComparator:
    """Tests for drift comparison."""
    
    def test_no_drift(self):
        """Test when code and docs are in sync."""
        code_results = [ParseResult(
            filepath="test.py",
            language="python",
            functions=[make_function("foo", ["a", "b"], docstring="Does foo")],
        )]
        
        doc_results = [DocParseResult(
            filepath="test.md",
            format=DocFormat.MARKDOWN,
            items=[make_doc_item("foo", ["a", "b"])],
        )]
        
        comparator = Comparator()
        result = comparator.compare(code_results, doc_results)
        
        # Should have no critical issues
        critical = result.filter_by_severity(DriftSeverity.CRITICAL)
        assert len(critical) == 0
    
    def test_undocumented_function(self):
        """Test detection of undocumented functions."""
        code_results = [ParseResult(
            filepath="test.py",
            language="python",
            functions=[
                make_function("documented_func", docstring="Has docs"),
                make_function("undocumented_func"),  # No docstring
            ],
        )]
        
        doc_results = [DocParseResult(
            filepath="test.md",
            format=DocFormat.MARKDOWN,
            items=[make_doc_item("documented_func")],
        )]
        
        comparator = Comparator({'require_docstrings': True})
        result = comparator.compare(code_results, doc_results)
        
        undoc_issues = [i for i in result.issues 
                       if i.drift_type == DriftType.UNDOCUMENTED_FUNCTION]
        assert len(undoc_issues) == 1
        assert undoc_issues[0].item_name == "undocumented_func"
    
    def test_missing_from_code(self):
        """Test detection of documented items missing from code."""
        code_results = [ParseResult(
            filepath="test.py",
            language="python",
            functions=[make_function("real_func", docstring="Exists")],
        )]
        
        doc_results = [DocParseResult(
            filepath="test.md",
            format=DocFormat.MARKDOWN,
            items=[
                make_doc_item("real_func"),
                make_doc_item("ghost_func"),  # Doesn't exist in code
            ],
        )]
        
        comparator = Comparator()
        result = comparator.compare(code_results, doc_results)
        
        missing = [i for i in result.issues 
                  if i.drift_type == DriftType.MISSING_FROM_CODE]
        assert len(missing) == 1
        assert missing[0].item_name == "ghost_func"
        assert missing[0].severity == DriftSeverity.CRITICAL
    
    def test_parameter_mismatch(self):
        """Test detection of parameter mismatches."""
        code_results = [ParseResult(
            filepath="test.py",
            language="python",
            functions=[make_function("func", ["a", "b", "c"], docstring="Has params")],
        )]
        
        doc_results = [DocParseResult(
            filepath="test.md",
            format=DocFormat.MARKDOWN,
            items=[make_doc_item("func", ["a", "old_param"])],  # b, c missing; old_param extra
        )]
        
        comparator = Comparator({'check_parameters': True})
        result = comparator.compare(code_results, doc_results)
        
        param_issues = [i for i in result.issues 
                       if i.drift_type == DriftType.PARAMETER_MISMATCH]
        assert len(param_issues) >= 1
    
    def test_ignore_private_functions(self):
        """Test that private functions can be ignored."""
        code_results = [ParseResult(
            filepath="test.py",
            language="python",
            functions=[
                make_function("_private_func"),
                make_function("__dunder__"),
            ],
        )]
        
        doc_results = [DocParseResult(
            filepath="test.md",
            format=DocFormat.MARKDOWN,
            items=[],
        )]
        
        comparator = Comparator({'ignore_patterns': ['_*', '__*']})
        result = comparator.compare(code_results, doc_results)
        
        # Private functions should be ignored
        undoc = [i for i in result.issues 
                if i.drift_type == DriftType.UNDOCUMENTED_FUNCTION]
        assert len(undoc) == 0
    
    def test_class_matching(self):
        """Test class documentation matching."""
        code_results = [ParseResult(
            filepath="test.py",
            language="python",
            classes=[ClassSignature(
                name="MyClass",
                filepath="test.py",
                line_number=1,
                docstring="A class",
            )],
        )]
        
        doc_results = [DocParseResult(
            filepath="test.md",
            format=DocFormat.MARKDOWN,
            items=[DocumentedItem(
                name="MyClass",
                filepath="test.md",
                line_number=1,
                doc_type="class",
            )],
        )]
        
        comparator = Comparator()
        result = comparator.compare(code_results, doc_results)
        
        class_issues = [i for i in result.issues 
                       if i.drift_type == DriftType.UNDOCUMENTED_CLASS]
        assert len(class_issues) == 0
    
    def test_stats_calculation(self):
        """Test that stats are calculated correctly."""
        code_results = [ParseResult(
            filepath="test.py",
            language="python",
            functions=[
                make_function("func1", docstring="Doc"),
                make_function("func2", docstring="Doc"),
            ],
            classes=[ClassSignature(
                name="Class1",
                filepath="test.py",
                line_number=1,
            )],
        )]
        
        doc_results = [DocParseResult(
            filepath="test.md",
            format=DocFormat.MARKDOWN,
            items=[
                make_doc_item("func1"),
                make_doc_item("func2"),
            ],
        )]
        
        comparator = Comparator()
        result = comparator.compare(code_results, doc_results)
        
        assert result.stats['total_functions'] == 2
        assert result.stats['total_classes'] == 1
        assert result.stats['matched'] == 2
