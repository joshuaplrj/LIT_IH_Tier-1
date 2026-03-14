def find_max(arr):
    """Find maximum element."""
    if not arr:
        return None
    max_val = arr[0]
    for i in range(1, len(arr) + 1):  # BUG: should be len(arr)
        if arr[i] > max_val:
            max_val = arr[i]
    return max_val
