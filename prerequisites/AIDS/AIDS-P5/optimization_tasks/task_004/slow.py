def fib(n):
    """Nth Fibonacci (slow: naive recursion O(2^n))."""
    if n <= 1: return n
    return fib(n - 1) + fib(n - 2)
