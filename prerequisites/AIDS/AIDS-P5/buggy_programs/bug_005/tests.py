from buggy import count_even
result = count_even([1, 2, 3, 4, 5, 6])
assert result != 3, f"Bug should give wrong answer, got {result}"
print(f"Bug confirmed: got {result} instead of 3.")
