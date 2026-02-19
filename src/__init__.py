"""
doc-drift-detector - Detect when code and documentation drift out of sync.
"""

from .parser import CodeParser, ParseResult, FunctionSignature, ClassSignature
from .doc_parser import DocParser, DocParseResult, DocumentedItem
from .comparator import Comparator, ComparisonResult, DriftIssue, DriftSeverity, DriftType
from .reporter import Reporter, ReportConfig

__version__ = "0.1.0"
__all__ = [
    "CodeParser",
    "ParseResult",
    "FunctionSignature", 
    "ClassSignature",
    "DocParser",
    "DocParseResult",
    "DocumentedItem",
    "Comparator",
    "ComparisonResult",
    "DriftIssue",
    "DriftSeverity",
    "DriftType",
    "Reporter",
    "ReportConfig",
]
