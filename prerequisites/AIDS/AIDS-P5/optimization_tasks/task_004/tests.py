from slow import fib as slow
from fast import fib as fast
for n in [0, 1, 10, 20, 30]:
    assert slow(n) == fast(n), f"Mismatch at n={n}"
print("All tests passed.")
