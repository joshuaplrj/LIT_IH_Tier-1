from buggy import sum_positive
result = sum_positive([1, 2, 3, -1])
assert result != 6, "Bug should produce wrong answer"
print(f"Bug confirmed: got {result} instead of 6.")
