"""
Sample calculator module with intentional documentation drift.
"""


def add(a: int, b: int) -> int:
    """Add two numbers together.
    
    Args:
        a: First number
        b: Second number
        
    Returns:
        Sum of a and b
    """
    return a + b


def subtract(a: int, b: int) -> int:
    """Subtract b from a.
    
    Args:
        a: First number
        b: Second number
        
    Returns:
        Difference of a and b
    """
    return a - b


def multiply(a: int, b: int, c: int = 1) -> int:
    """Multiply numbers together.
    
    NEW: Added optional third parameter 'c' - DOCS NOT UPDATED!
    
    Args:
        a: First number
        b: Second number
        c: Optional multiplier (default 1)
        
    Returns:
        Product
    """
    return a * b * c


def divide(a: int, b: int) -> float:
    """Divide a by b.
    
    Args:
        a: Numerator
        b: Denominator
        
    Returns:
        Result of division
        
    Raises:
        ZeroDivisionError: If b is zero
    """
    return a / b


# NEW FUNCTION - Not documented yet!
def power(base: int, exponent: int) -> int:
    """Raise base to the power of exponent."""
    return base ** exponent


# NEW FUNCTION - Also not documented!
def modulo(a: int, b: int) -> int:
    """Get remainder of a divided by b."""
    return a % b


class Calculator:
    """A calculator class.
    
    Provides basic arithmetic operations.
    """
    
    def __init__(self, precision: int = 2):
        """Initialize calculator.
        
        Args:
            precision: Decimal precision for results
        """
        self.precision = precision
        self.history = []  # NEW: history tracking - not documented!
    
    def add(self, a: float, b: float) -> float:
        """Add two numbers."""
        result = round(a + b, self.precision)
        self.history.append(('add', a, b, result))
        return result
    
    def clear_history(self):
        """Clear calculation history.
        
        NEW METHOD - Not in docs!
        """
        self.history = []


# REMOVED: This function was deleted but still documented!
# def old_square_root(x: float) -> float:
#     """Calculate square root."""
#     return x ** 0.5
