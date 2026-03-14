from slow import find_duplicates as slow
from fast import find_duplicates as fast
tests = [[1,2,3,2,4,1], [5,5,5], [1,2,3], []]
for t in tests:
    assert slow(t) == fast(t), f"Mismatch for {t}"
print("All tests passed.")
