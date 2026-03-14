from slow import lcs as slow
from fast import lcs as fast
pairs = [("ABCBDAB","BDCAB"), ("ABC","AC"), ("","ABC"), ("AAA","AA")]
for a, b in pairs:
    assert slow(a,b) == fast(a,b), f"Mismatch for ({a},{b})"
print("All tests passed.")
