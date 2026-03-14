def sum_of_squares(n):
    """Sum of squares 1^2+2^2+...+n^2 (slow: loop)."""
    total = 0
    for i in range(1, n + 1):
        total += i * i
    return total
