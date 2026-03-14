def find_duplicates(arr):
    """Find all duplicate elements (slow: O(n^2) nested loops)."""
    dups = []
    for i in range(len(arr)):
        for j in range(i + 1, len(arr)):
            if arr[i] == arr[j] and arr[i] not in dups:
                dups.append(arr[i])
    return sorted(dups)
