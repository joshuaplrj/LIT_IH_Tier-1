def lcs(a, b):
    """LCS length (slow: recursion without memoization)."""
    if not a or not b: return 0
    if a[-1] == b[-1]:
        return 1 + lcs(a[:-1], b[:-1])
    return max(lcs(a[:-1], b), lcs(a, b[:-1]))
