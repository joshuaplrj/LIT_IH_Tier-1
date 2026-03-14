from problem import queue_from_stacks
# Basic smoke test
result = queue_from_stacks([3,1,2,1])
assert result is not None, "Function returned None"
print("Smoke test passed for queue_from_stacks.")
