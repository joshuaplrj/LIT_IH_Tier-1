from slow import count_primes as slow
from fast import count_primes as fast
for n in [10, 100, 1000]:
    assert slow(n) == fast(n), f"Mismatch at n={n}"
print("All tests passed.")
