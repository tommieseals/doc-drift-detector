"""
Reporter - Generate drift reports in various formats.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, TextIO
from dataclasses import dataclass

from .comparator import ComparisonResult, DriftIssue, DriftSeverity, DriftType


@dataclass
class ReportConfig:
    """Configuration for report generation."""
    include_suggestions: bool = True
    include_details: bool = True
    min_severity: DriftSeverity = DriftSeverity.INFO
    group_by_file: bool = True
    show_stats: bool = True
    max_issues: Optional[int] = None


class MarkdownReporter:
    """Generate Markdown drift reports."""
    
    SEVERITY_ICONS = {
        DriftSeverity.CRITICAL: "🔴",
        DriftSeverity.WARNING: "🟡",
        DriftSeverity.INFO: "🔵",
    }
    
    def __init__(self, config: Optional[ReportConfig] = None):
        self.config = config or ReportConfig()
    
    def generate(self, result: ComparisonResult, 
                 title: str = "Documentation Drift Report") -> str:
        """Generate a Markdown report."""
        lines = []
        
        # Header
        lines.append(f"# {title}")
        lines.append("")
        lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        lines.append("")
        
        # Summary
        summary = result.to_dict()['summary']
        lines.append("## Summary")
        lines.append("")
        lines.append(f"| Severity | Count |")
        lines.append("|----------|-------|")
        lines.append(f"| 🔴 Critical | {summary['critical']} |")
        lines.append(f"| 🟡 Warning | {summary['warning']} |")
        lines.append(f"| 🔵 Info | {summary['info']} |")
        lines.append(f"| **Total** | **{summary['total']}** |")
        lines.append("")
        
        # Stats
        if self.config.show_stats and result.stats:
            lines.append("### Coverage Stats")
            lines.append("")
            lines.append(f"- Total functions: {result.stats.get('total_functions', 0)}")
            lines.append(f"- Total classes: {result.stats.get('total_classes', 0)}")
            lines.append(f"- Documented items: {result.stats.get('total_documented', 0)}")
            lines.append(f"- Matched: {result.stats.get('matched', 0)}")
            lines.append(f"- Undocumented: {result.stats.get('undocumented', 0)}")
            lines.append("")
        
        # Filter issues
        issues = self._filter_issues(result.issues)
        
        if not issues:
            lines.append("## ✅ No Issues Found")
            lines.append("")
            lines.append("Code and documentation are in sync!")
            return "\n".join(lines)
        
        # Issues
        lines.append("## Issues")
        lines.append("")
        
        if self.config.group_by_file:
            grouped = self._group_by_file(issues)
            for filepath, file_issues in sorted(grouped.items()):
                lines.append(f"### 📁 `{filepath}`")
                lines.append("")
                for issue in file_issues:
                    lines.extend(self._format_issue(issue))
                lines.append("")
        else:
            # Group by severity
            for severity in [DriftSeverity.CRITICAL, DriftSeverity.WARNING, DriftSeverity.INFO]:
                severity_issues = [i for i in issues if i.severity == severity]
                if severity_issues:
                    icon = self.SEVERITY_ICONS[severity]
                    lines.append(f"### {icon} {severity.value.title()}")
                    lines.append("")
                    for issue in severity_issues:
                        lines.extend(self._format_issue(issue))
                    lines.append("")
        
        return "\n".join(lines)
    
    def _filter_issues(self, issues: List[DriftIssue]) -> List[DriftIssue]:
        """Filter issues based on configuration."""
        severity_order = {
            DriftSeverity.CRITICAL: 0,
            DriftSeverity.WARNING: 1,
            DriftSeverity.INFO: 2,
        }
        min_order = severity_order[self.config.min_severity]
        
        filtered = [i for i in issues if severity_order[i.severity] <= min_order]
        
        if self.config.max_issues:
            filtered = filtered[:self.config.max_issues]
        
        return filtered
    
    def _group_by_file(self, issues: List[DriftIssue]) -> Dict[str, List[DriftIssue]]:
        """Group issues by file path."""
        grouped: Dict[str, List[DriftIssue]] = {}
        
        for issue in issues:
            filepath = issue.code_location or issue.doc_location or "unknown"
            if filepath not in grouped:
                grouped[filepath] = []
            grouped[filepath].append(issue)
        
        return grouped
    
    def _format_issue(self, issue: DriftIssue) -> List[str]:
        """Format a single issue as Markdown lines."""
        lines = []
        icon = self.SEVERITY_ICONS[issue.severity]
        
        lines.append(f"- {icon} **{issue.item_name}**: {issue.message}")
        
        location_parts = []
        if issue.code_location and issue.code_line:
            location_parts.append(f"Code: `{issue.code_location}:{issue.code_line}`")
        if issue.doc_location and issue.doc_line:
            location_parts.append(f"Doc: `{issue.doc_location}:{issue.doc_line}`")
        
        if location_parts:
            lines.append(f"  - Location: {', '.join(location_parts)}")
        
        if self.config.include_suggestions and issue.suggestion:
            lines.append(f"  - 💡 *{issue.suggestion}*")
        
        return lines


class JSONReporter:
    """Generate JSON drift reports."""
    
    def __init__(self, config: Optional[ReportConfig] = None):
        self.config = config or ReportConfig()
    
    def generate(self, result: ComparisonResult) -> str:
        """Generate a JSON report."""
        report = {
            'generated_at': datetime.now().isoformat(),
            'summary': result.to_dict()['summary'],
            'stats': result.stats,
            'issues': [i.to_dict() for i in result.issues],
        }
        
        return json.dumps(report, indent=2)


class GithubActionsReporter:
    """Generate GitHub Actions annotations."""
    
    SEVERITY_MAP = {
        DriftSeverity.CRITICAL: "error",
        DriftSeverity.WARNING: "warning",
        DriftSeverity.INFO: "notice",
    }
    
    def generate(self, result: ComparisonResult) -> str:
        """Generate GitHub Actions workflow commands."""
        lines = []
        
        for issue in result.issues:
            level = self.SEVERITY_MAP[issue.severity]
            file = issue.code_location or issue.doc_location or ""
            line = issue.code_line or issue.doc_line or 1
            
            # GitHub Actions annotation format
            message = issue.message.replace('\n', '%0A')
            lines.append(f"::{level} file={file},line={line}::{message}")
        
        # Summary
        summary = result.to_dict()['summary']
        lines.append("")
        lines.append(f"::group::Documentation Drift Summary")
        lines.append(f"Total issues: {summary['total']}")
        lines.append(f"Critical: {summary['critical']}")
        lines.append(f"Warnings: {summary['warning']}")
        lines.append(f"Info: {summary['info']}")
        lines.append("::endgroup::")
        
        return "\n".join(lines)


class PRCommentReporter:
    """Generate PR comment body for GitHub/GitLab."""
    
    SEVERITY_ICONS = {
        DriftSeverity.CRITICAL: "❌",
        DriftSeverity.WARNING: "⚠️",
        DriftSeverity.INFO: "ℹ️",
    }
    
    def generate(self, result: ComparisonResult, 
                 repo: str = "",
                 commit_sha: str = "") -> str:
        """Generate a PR comment body."""
        lines = []
        
        summary = result.to_dict()['summary']
        
        # Header with status
        if summary['critical'] > 0:
            lines.append("## ❌ Documentation Drift Detected")
        elif summary['warning'] > 0:
            lines.append("## ⚠️ Documentation Drift Warnings")
        else:
            lines.append("## ✅ Documentation Up to Date")
        
        lines.append("")
        
        # Quick stats
        lines.append("<details>")
        lines.append("<summary>📊 Summary</summary>")
        lines.append("")
        lines.append("| Category | Count |")
        lines.append("|----------|-------|")
        lines.append(f"| ❌ Critical | {summary['critical']} |")
        lines.append(f"| ⚠️ Warning | {summary['warning']} |")
        lines.append(f"| ℹ️ Info | {summary['info']} |")
        lines.append("")
        lines.append("</details>")
        lines.append("")
        
        if not result.issues:
            lines.append("No documentation drift detected. Great job! 🎉")
            return "\n".join(lines)
        
        # Critical issues (always show)
        critical = [i for i in result.issues if i.severity == DriftSeverity.CRITICAL]
        if critical:
            lines.append("### ❌ Critical Issues")
            lines.append("")
            for issue in critical[:10]:  # Limit to 10
                lines.append(self._format_issue_compact(issue, repo, commit_sha))
            if len(critical) > 10:
                lines.append(f"*...and {len(critical) - 10} more*")
            lines.append("")
        
        # Warnings (collapsible)
        warnings = [i for i in result.issues if i.severity == DriftSeverity.WARNING]
        if warnings:
            lines.append("<details>")
            lines.append(f"<summary>⚠️ Warnings ({len(warnings)})</summary>")
            lines.append("")
            for issue in warnings[:20]:  # Limit to 20
                lines.append(self._format_issue_compact(issue, repo, commit_sha))
            if len(warnings) > 20:
                lines.append(f"*...and {len(warnings) - 20} more*")
            lines.append("")
            lines.append("</details>")
            lines.append("")
        
        # Footer
        lines.append("---")
        lines.append("*Generated by [doc-drift-detector](https://github.com/tommieseals/doc-drift-detector)*")
        
        return "\n".join(lines)
    
    def _format_issue_compact(self, issue: DriftIssue, 
                               repo: str, commit_sha: str) -> str:
        """Format an issue in compact form with optional links."""
        icon = self.SEVERITY_ICONS[issue.severity]
        
        # Create file link if we have repo info
        file_ref = ""
        if issue.code_location and repo and commit_sha:
            file_ref = f" ([code]({repo}/blob/{commit_sha}/{issue.code_location}#L{issue.code_line or 1}))"
        elif issue.code_location:
            file_ref = f" (`{issue.code_location}:{issue.code_line or 1}`)"
        
        return f"- {icon} **{issue.item_name}**: {issue.message}{file_ref}"


class Reporter:
    """Main reporter that dispatches to format-specific reporters."""
    
    def __init__(self, config: Optional[ReportConfig] = None):
        self.config = config or ReportConfig()
        self.markdown = MarkdownReporter(self.config)
        self.json = JSONReporter(self.config)
        self.github = GithubActionsReporter()
        self.pr_comment = PRCommentReporter()
    
    def generate(self, result: ComparisonResult, 
                 format: str = "markdown",
                 **kwargs) -> str:
        """Generate a report in the specified format."""
        if format == "markdown":
            return self.markdown.generate(result, **kwargs)
        elif format == "json":
            return self.json.generate(result)
        elif format == "github":
            return self.github.generate(result)
        elif format == "pr":
            return self.pr_comment.generate(result, **kwargs)
        else:
            raise ValueError(f"Unknown format: {format}")
    
    def write(self, result: ComparisonResult, 
              output: Path,
              format: Optional[str] = None) -> None:
        """Write report to a file."""
        # Infer format from extension if not specified
        if format is None:
            if output.suffix == '.json':
                format = 'json'
            else:
                format = 'markdown'
        
        content = self.generate(result, format)
        output.write_text(content)


if __name__ == '__main__':
    # Demo with sample data
    from .comparator import ComparisonResult, DriftIssue, DriftSeverity, DriftType
    
    # Create sample result
    result = ComparisonResult()
    result.issues = [
        DriftIssue(
            drift_type=DriftType.UNDOCUMENTED_FUNCTION,
            severity=DriftSeverity.WARNING,
            message="Function 'parse_config' is not documented",
            code_location="src/config.py",
            code_line=42,
            item_name="parse_config",
            suggestion="Add documentation for parse_config() in docs/api.md",
        ),
        DriftIssue(
            drift_type=DriftType.MISSING_FROM_CODE,
            severity=DriftSeverity.CRITICAL,
            message="Documented function 'old_parser' not found in code",
            doc_location="docs/api.md",
            doc_line=15,
            item_name="old_parser",
            suggestion="Remove documentation or restore the function",
        ),
    ]
    result.stats = {
        'total_functions': 25,
        'total_classes': 5,
        'total_documented': 20,
        'matched': 18,
        'undocumented': 7,
    }
    
    reporter = Reporter()
    print(reporter.generate(result, "markdown"))
