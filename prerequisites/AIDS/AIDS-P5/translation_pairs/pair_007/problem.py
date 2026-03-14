def gcd(a, b):
    """Return greatest common divisor using Euclidean algorithm."""
    while b:
        a, b = b, a % b
    return a
