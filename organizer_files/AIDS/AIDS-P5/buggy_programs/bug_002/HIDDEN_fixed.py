def sum_positive(nums):
    """Return sum of positive numbers."""
    total = 0
    for n in nums:
        if n > 0:
            total = total + n  # FIXED
    return total
