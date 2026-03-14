from problem import product_except_self
# Basic smoke test
result = product_except_self([3,1,2,1])
assert result is not None, "Function returned None"
print("Smoke test passed for product_except_self.")
