from problem import run_length_encode
# Basic smoke test
result = run_length_encode([3,1,2,1])
assert result is not None, "Function returned None"
print("Smoke test passed for run_length_encode.")
