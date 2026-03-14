from slow import sum_of_squares as slow
from fast import sum_of_squares as fast
for n in [100, 1000, 10000]:
    assert slow(n) == fast(n), f"Mismatch at n={n}"
print("All tests passed.")
