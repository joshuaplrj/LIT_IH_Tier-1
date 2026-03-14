def fib(n, _memo={}):
    """Nth Fibonacci (fast: memoized O(n))."""
    if n <= 1: return n
    if n in _memo: return _memo[n]
    _memo[n] = fib(n - 1) + fib(n - 2)
    return _memo[n]
