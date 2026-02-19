# Calculator API

This document describes the calculator module API.

## Functions

### `add(a, b)`

Add two numbers together.

**Parameters:**
- `a` (int) - First number
- `b` (int) - Second number

**Returns:** Sum of a and b

---

### `subtract(a, b)`

Subtract b from a.

**Parameters:**
- `a` (int) - First number  
- `b` (int) - Second number

**Returns:** Difference of a and b

---

### `multiply(a, b)`

Multiply two numbers together.

**Parameters:**
- `a` (int) - First number
- `b` (int) - Second number

> ⚠️ **DRIFT**: Code now has a third parameter `c` that isn't documented here!

**Returns:** Product of a and b

---

### `divide(a, b)`

Divide a by b.

**Parameters:**
- `a` (int) - Numerator
- `b` (int) - Denominator

**Returns:** Result of division

**Raises:** `ZeroDivisionError` if b is zero

---

### `old_square_root(x)` 

*DEPRECATED*

Calculate the square root of a number.

**Parameters:**
- `x` (float) - Number to calculate root of

> ⚠️ **DRIFT**: This function was removed from the code but is still documented!

---

## Classes

### `Calculator`

A calculator class for basic arithmetic.

#### Constructor

```python
Calculator()
```

> ⚠️ **DRIFT**: Constructor now takes `precision` parameter!

#### Methods

##### `add(a, b)`

Add two numbers with precision rounding.

**Parameters:**
- `a` (float) - First number
- `b` (float) - Second number

**Returns:** Rounded sum

---

## Missing Documentation

The following items exist in code but aren't documented here:

- `power(base, exponent)` - NEW function
- `modulo(a, b)` - NEW function
- `Calculator.clear_history()` - NEW method
- `Calculator.history` - NEW attribute
