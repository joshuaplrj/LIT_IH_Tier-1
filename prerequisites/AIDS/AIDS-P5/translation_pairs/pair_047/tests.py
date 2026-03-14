from problem import valid_sudoku_row
# Basic smoke test
result = valid_sudoku_row([3,1,2,1])
assert result is not None, "Function returned None"
print("Smoke test passed for valid_sudoku_row.")
