from slow import solve_opt_task_07 as slow
from fast import solve_opt_task_07 as fast
data = list(range(50))
r1 = slow(data)
r2 = fast(data)
assert len(r1) == len(r2), "Length mismatch"
print("Smoke test passed.")
