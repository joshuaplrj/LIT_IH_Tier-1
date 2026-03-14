def count_even(nums):
    """Count even numbers in list."""
    count = 0
    for n in nums:
        if n % 2 == 1:  # BUG: should be == 0 for even
            count += 1
    return count
