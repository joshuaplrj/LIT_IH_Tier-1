def count_primes(n):
    """Count primes < n (slow: trial division for each number)."""
    def is_prime(x):
        if x < 2: return False
        for i in range(2, int(x**0.5) + 1):
            if x % i == 0: return False
        return True
    return sum(1 for i in range(n) if is_prime(i))
