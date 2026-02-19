# 📚 doc-drift-detector

> Detect when code and documentation drift out of sync

[![CI](https://github.com/tommieseals/doc-drift-detector/workflows/CI/badge.svg)](https://github.com/tommieseals/doc-drift-detector/actions)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Documentation goes stale. Code evolves faster than docs. **doc-drift-detector** catches the drift before your users do.

## 🎯 What It Detects

- ❌ **Undocumented functions** - New code without docs
- ❌ **Ghost documentation** - Docs for code that no longer exists  
- ❌ **Parameter mismatches** - Documented params that changed
- ❌ **Missing deprecation notices** - Deprecated in docs but not code
- ❌ **Stale examples** - Code examples that won't work anymore

## 🚀 Quick Start

### Installation

```bash
pip install doc-drift-detector
```

Or clone and install locally:

```bash
git clone https://github.com/tommieseals/doc-drift-detector.git
cd doc-drift-detector
pip install -e .
```

### Basic Usage

```bash
# Scan your project
doc-drift ./src ./docs

# Generate a report file
doc-drift ./src ./docs -o drift-report.md

# JSON output for CI
doc-drift ./src ./docs --format json

# Fail CI on critical issues
doc-drift ./src ./docs --fail-on critical
```

## 📖 Example Output

```markdown
## Summary

| Severity | Count |
|----------|-------|
| 🔴 Critical | 2 |
| 🟡 Warning | 5 |
| 🔵 Info | 3 |
| **Total** | **10** |

## Issues

### 📁 `src/api.py`

- 🔴 **create_user**: Parameters `email, role` not documented
  - Location: Code: `src/api.py:45`, Doc: `docs/api.md:23`
  - 💡 *Add documentation for parameters: email, role*

- 🟡 **old_endpoint**: Documented function not found in code
  - Location: Doc: `docs/api.md:89`
  - 💡 *Remove or update documentation for 'old_endpoint'*
```

## 🔧 Configuration

Create a `.drift.json` in your project root:

```json
{
  "exclude": [
    "tests/",
    "examples/",
    "*_test.py"
  ],
  "ignore_patterns": [
    "__init__",
    "_internal_*",
    "test_*"
  ],
  "require_docstrings": true,
  "check_parameters": true,
  "severity_overrides": {
    "UNDOCUMENTED_FUNCTION": "warning",
    "MISSING_FROM_CODE": "critical"
  }
}
```

## 🤖 GitHub Action

Add to your workflow:

```yaml
name: Documentation Check

on: [push, pull_request]

jobs:
  doc-drift:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Check documentation drift
        uses: tommieseals/doc-drift-detector@v1
        with:
          code-path: './src'
          docs-path: './docs'
          fail-on: 'critical'
```

Or run directly:

```yaml
- name: Setup Python
  uses: actions/setup-python@v5
  with:
    python-version: '3.11'

- name: Install doc-drift-detector
  run: pip install doc-drift-detector

- name: Check for drift
  run: doc-drift ./src ./docs --format github --fail-on warning
```

## 📋 CLI Reference

```
usage: doc-drift [-h] [-o OUTPUT] [-f {markdown,json,github,pr}]
                 [--min-severity {info,warning,critical}]
                 [--fail-on {info,warning,critical,none}]
                 [--exclude EXCLUDE] [--no-suggestions] [--no-docstrings]
                 [--config CONFIG] [--version] [-v]
                 code_path docs_path

Detect when code and documentation drift out of sync.

positional arguments:
  code_path             Path to source code directory
  docs_path             Path to documentation directory

options:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        Output file (defaults to stdout)
  -f, --format {markdown,json,github,pr}
                        Output format (default: markdown)
  --min-severity {info,warning,critical}
                        Minimum severity level to report
  --fail-on {info,warning,critical,none}
                        Exit with error code 1 if issues at this level
  --exclude EXCLUDE     Patterns to exclude (repeatable)
  --no-suggestions      Don't include fix suggestions
  --no-docstrings       Don't require docstrings in code
  --config CONFIG       Path to configuration file
  -v, --verbose         Verbose output
```

## 🔌 Supported Languages

| Language | Parser | Notes |
|----------|--------|-------|
| Python | AST | Full support including type hints |
| JavaScript | Regex | Functions, classes, arrow functions |
| TypeScript | Regex | Same as JS + type annotations |

See [docs/supported-languages.md](docs/supported-languages.md) for details.

## 🔬 How It Works

1. **Parse Code**: Extract function/class signatures using AST (Python) or regex (JS)
2. **Parse Docs**: Extract documented items from Markdown/RST files
3. **Compare**: Match code items with documentation by name
4. **Report**: Generate actionable drift reports

### Optional: Semantic Matching

Enable fuzzy matching with embeddings:

```bash
pip install doc-drift-detector[embeddings]
doc-drift ./src ./docs --semantic
```

Uses local sentence-transformers by default (no API needed).

## 🏗️ Architecture

```
doc-drift-detector/
├── src/
│   ├── parser.py        # Code parsing (Python AST, JS regex)
│   ├── doc_parser.py    # Documentation parsing (MD, RST)
│   ├── comparator.py    # Drift detection logic
│   ├── embeddings.py    # Semantic similarity (optional)
│   ├── reporter.py      # Report generation
│   └── cli.py           # Command-line interface
├── tests/               # Test suite
├── examples/            # Example repos with drift
└── .github/workflows/   # CI configuration
```

## 🧪 Development

```bash
# Clone
git clone https://github.com/tommieseals/doc-drift-detector.git
cd doc-drift-detector

# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src/

# Format
ruff format src/
```

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

---

**Made with ❤️ for developers who care about documentation**

