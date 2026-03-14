def find_duplicates(arr):
    """Find all duplicate elements (fast: O(n) hash set)."""
    seen, dups = set(), set()
    for x in arr:
        if x in seen:
            dups.add(x)
        seen.add(x)
    return sorted(dups)
