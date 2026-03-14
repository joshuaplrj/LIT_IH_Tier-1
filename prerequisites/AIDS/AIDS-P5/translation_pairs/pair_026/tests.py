from problem import caesar_cipher
# Basic smoke test
result = caesar_cipher([3,1,2,1])
assert result is not None, "Function returned None"
print("Smoke test passed for caesar_cipher.")
