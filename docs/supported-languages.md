# Supported Languages

doc-drift-detector parses code to extract function and class signatures for comparison with documentation.

## Python

**Parser:** AST (Abstract Syntax Tree)

**File Extensions:** `.py`

### What's Detected

✅ **Functions**
- Name, parameters, return type
- Default values
- Type hints (PEP 484)
- Docstrings
- Decorators
- Async functions

✅ **Classes**
- Name, base classes
- Docstrings
- Methods (including special methods)
- Class decorators

### Example

```python
@api_endpoint
async def create_user(
    name: str,
    email: str,
    role: str = "user"
) -> User:
    """Create a new user.
    
    Args:
        name: User's full name
        email: User's email address
        role: User role (default: "user")
        
    Returns:
        The created User object
    """
    ...
```

**Extracted:**
- Name: `create_user`
- Parameters: `name: str`, `email: str`, `role: str = "user"`
- Return type: `User`
- Decorators: `['api_endpoint']`
- Async: `True`
- Docstring: ✓

---

## JavaScript / TypeScript

**Parser:** Regex-based

**File Extensions:** `.js`, `.jsx`, `.ts`, `.tsx`, `.mjs`

### What's Detected

✅ **Functions**
- Regular functions: `function name(params)`
- Arrow functions: `const name = (params) =>`
- Async functions
- JSDoc comments
- TypeScript type annotations

✅ **Classes**
- Class declarations
- Extends/inheritance
- JSDoc comments

✅ **Exports**
- Named exports
- Default exports

### Example

```javascript
/**
 * Create a new user account.
 * @param {string} name - User's name
 * @param {string} email - User's email
 * @returns {Promise<User>} The created user
 */
export async function createUser(name, email) {
    // ...
}

/**
 * User management class.
 */
export class UserManager extends BaseManager {
    /**
     * Delete a user by ID.
     * @param {string} id - User ID
     */
    async deleteUser(id) {
        // ...
    }
}
```

**Extracted:**
- Functions: `createUser`
- Classes: `UserManager` (extends `BaseManager`)
- Exports: `createUser`, `UserManager`

### Limitations

The regex-based parser handles most common patterns but may miss:
- Computed property names
- Complex destructuring in parameters
- Deeply nested function definitions
- Some edge cases with template literals

For complex JavaScript codebases, consider:
1. Using JSDoc consistently
2. Using TypeScript for better type extraction
3. Contributing improvements to the parser!

---

## Documentation Formats

### Markdown

**File Extensions:** `.md`, `.markdown`

**Detected Patterns:**
- Function headers: `## \`function_name(params)\``
- API endpoints: `## GET /api/endpoint`
- Code blocks with function definitions
- Parameter lists
- Deprecation markers
- Version annotations

### reStructuredText (RST)

**File Extensions:** `.rst`

**Detected Patterns:**
- Function directives: `.. function:: name`
- Class directives: `.. class:: Name`
- Method directives: `.. method:: name`
- Python-specific directives: `.. py:function::`
- Version directives: `.. versionadded::`
- Deprecation directives: `.. deprecated::`

---

## Adding New Languages

To add support for a new language:

1. **Create a parser class** in `src/parser.py`:

```python
class RubyParser:
    """Parse Ruby files."""
    
    def parse_file(self, filepath: Path) -> ParseResult:
        # Your parsing logic
        ...
```

2. **Register in `CodeParser.LANGUAGE_MAP`**:

```python
LANGUAGE_MAP = {
    '.rb': 'ruby',
    # ...
}
```

3. **Add to dispatch in `CodeParser.parse_file`**:

```python
elif language == 'ruby':
    return self.ruby_parser.parse_file(filepath)
```

4. **Write tests** in `tests/test_parser.py`

5. **Update this document!**

### Recommended Approach

- Use AST parsing when available (more reliable)
- Fall back to regex for languages without good AST libraries
- Test with real-world code samples
- Handle edge cases gracefully (return empty results rather than crash)

---

## Future Language Support

Planned:
- [ ] Go
- [ ] Rust  
- [ ] Java
- [ ] C#
- [ ] Ruby
- [ ] PHP

Want to contribute? Check our [CONTRIBUTING.md](../CONTRIBUTING.md)!
