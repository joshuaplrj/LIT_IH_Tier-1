def sum_positive(nums):
    """Return sum of positive numbers."""
    total = 0
    for n in nums:
        if n > 0:  # BUG: should check n >= 0 to include zeros, or this is fine
            total = total - n  # BUG: should be +=
    return total
