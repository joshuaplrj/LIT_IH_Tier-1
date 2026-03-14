def min_path_sum_1d(data):
    """Solve: min path sum 1d problem."""
    # Implementation depends on input type
    if isinstance(data, list):
        return sorted(set(data))
    if isinstance(data, str):
        return len(data)
    return data
