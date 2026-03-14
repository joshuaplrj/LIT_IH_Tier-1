def solve_opt_task_22(data):
    """Slow implementation using nested loops."""
    result = []
    for i in range(len(data)):
        for j in range(i, len(data)):
            if data[i] + data[j] == sum(data):
                result.append((i, j))
    return result[:1] if result else []
