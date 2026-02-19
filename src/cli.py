#!/usr/bin/env python3
"""
doc-drift-detector CLI - Detect documentation drift from the command line.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, List

from .parser import CodeParser
from .doc_parser import DocParser
from .comparator import Comparator, DriftSeverity
from .reporter import Reporter, ReportConfig


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="doc-drift",
        description="Detect when code and documentation drift out of sync.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic scan
  doc-drift ./src ./docs

  # Generate JSON report
  doc-drift ./src ./docs --format json -o report.json

  # Only show warnings and critical
  doc-drift ./src ./docs --min-severity warning

  # GitHub Actions output
  doc-drift ./src ./docs --format github

  # Fail CI on critical issues
  doc-drift ./src ./docs --fail-on critical
        """
    )
    
    parser.add_argument(
        "code_path",
        type=Path,
        help="Path to source code directory"
    )
    
    parser.add_argument(
        "docs_path", 
        type=Path,
        help="Path to documentation directory"
    )
    
    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Output file (defaults to stdout)"
    )
    
    parser.add_argument(
        "-f", "--format",
        choices=["markdown", "json", "github", "pr"],
        default="markdown",
        help="Output format (default: markdown)"
    )
    
    parser.add_argument(
        "--min-severity",
        choices=["info", "warning", "critical"],
        default="info",
        help="Minimum severity level to report (default: info)"
    )
    
    parser.add_argument(
        "--fail-on",
        choices=["info", "warning", "critical", "none"],
        default="none",
        help="Exit with error code 1 if issues at this level or higher"
    )
    
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Patterns to exclude (can be used multiple times)"
    )
    
    parser.add_argument(
        "--no-suggestions",
        action="store_true",
        help="Don't include fix suggestions"
    )
    
    parser.add_argument(
        "--no-docstrings",
        action="store_true",
        help="Don't require docstrings in code"
    )
    
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to configuration file (.drift.json)"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    return parser.parse_args(args)


def load_config(config_path: Optional[Path]) -> dict:
    """Load configuration from file if provided."""
    if config_path and config_path.exists():
        with open(config_path) as f:
            return json.load(f)
    
    # Check for default config file
    default_path = Path(".drift.json")
    if default_path.exists():
        with open(default_path) as f:
            return json.load(f)
    
    return {}


def main(args: Optional[List[str]] = None) -> int:
    """Main entry point."""
    parsed = parse_args(args)
    
    # Load config
    config = load_config(parsed.config)
    
    # Merge CLI args with config
    exclude_patterns = config.get("exclude", []) + parsed.exclude
    if not exclude_patterns:
        exclude_patterns = ["node_modules", "__pycache__", ".git", "venv", ".venv", "dist", "build"]
    
    # Validate paths
    if not parsed.code_path.exists():
        print(f"Error: Code path does not exist: {parsed.code_path}", file=sys.stderr)
        return 1
    
    if not parsed.docs_path.exists():
        print(f"Error: Docs path does not exist: {parsed.docs_path}", file=sys.stderr)
        return 1
    
    if parsed.verbose:
        print(f"Scanning code: {parsed.code_path}", file=sys.stderr)
        print(f"Scanning docs: {parsed.docs_path}", file=sys.stderr)
    
    # Parse code
    code_parser = CodeParser()
    code_results = code_parser.parse_directory(parsed.code_path, exclude_patterns)
    
    if parsed.verbose:
        total_funcs = sum(len(r.functions) for r in code_results)
        total_classes = sum(len(r.classes) for r in code_results)
        print(f"Found {total_funcs} functions and {total_classes} classes", file=sys.stderr)
    
    # Parse docs
    doc_parser = DocParser()
    doc_results = doc_parser.parse_directory(parsed.docs_path, exclude_patterns)
    
    if parsed.verbose:
        total_items = sum(len(r.items) for r in doc_results)
        print(f"Found {total_items} documented items", file=sys.stderr)
    
    # Compare
    comparator_config = {
        "ignore_patterns": config.get("ignore_patterns", []),
        "require_docstrings": not parsed.no_docstrings,
    }
    comparator = Comparator(comparator_config)
    result = comparator.compare(code_results, doc_results)
    
    # Generate report
    severity_map = {
        "info": DriftSeverity.INFO,
        "warning": DriftSeverity.WARNING,
        "critical": DriftSeverity.CRITICAL,
    }
    
    report_config = ReportConfig(
        include_suggestions=not parsed.no_suggestions,
        min_severity=severity_map[parsed.min_severity],
    )
    
    reporter = Reporter(report_config)
    report = reporter.generate(result, parsed.format)
    
    # Output
    if parsed.output:
        parsed.output.write_text(report)
        if parsed.verbose:
            print(f"Report written to: {parsed.output}", file=sys.stderr)
    else:
        print(report)
    
    # Determine exit code
    if parsed.fail_on != "none":
        fail_severity = severity_map[parsed.fail_on]
        fail_order = {DriftSeverity.CRITICAL: 0, DriftSeverity.WARNING: 1, DriftSeverity.INFO: 2}
        
        for issue in result.issues:
            if fail_order[issue.severity] <= fail_order[fail_severity]:
                if parsed.verbose:
                    print(f"Failing due to {issue.severity.value} issue", file=sys.stderr)
                return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
