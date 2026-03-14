from problem import valid_ip_v4
# Basic smoke test
result = valid_ip_v4([3,1,2,1])
assert result is not None, "Function returned None"
print("Smoke test passed for valid_ip_v4.")
