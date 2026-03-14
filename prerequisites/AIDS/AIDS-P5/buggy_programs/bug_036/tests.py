from buggy import compute_36
result = compute_36([1, 2, 3])
correct = sum(x * i for i, x in enumerate([1,2,3]))
assert result != correct, f"Bug should produce wrong answer (got {result}, correct={correct})"
print(f"Bug confirmed: got {result}, should be {correct}.")
