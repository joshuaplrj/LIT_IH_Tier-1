from buggy import calculate_area
result = calculate_area(4, 5)
assert result != 20, f"Bug should give wrong answer, got {result}"
print(f"Bug confirmed: got {result} instead of 20.")
