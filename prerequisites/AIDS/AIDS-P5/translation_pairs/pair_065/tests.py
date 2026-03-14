from problem import excel_column_number
# Basic smoke test
result = excel_column_number([3,1,2,1])
assert result is not None, "Function returned None"
print("Smoke test passed for excel_column_number.")
