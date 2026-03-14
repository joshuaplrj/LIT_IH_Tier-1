def solve_opt_task_12(data):
    """Fast O(n) implementation using hash map."""
    if not data: return []
    target = sum(data)
    seen = {}
    for i, x in enumerate(data):
        if target - x in seen:
            return [(seen[target-x], i)]
        seen[x] = i
    return []
