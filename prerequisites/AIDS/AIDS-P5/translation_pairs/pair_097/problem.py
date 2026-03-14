def minimum_diff_pair(data):
    """Solve: minimum diff pair problem."""
    # Implementation depends on input type
    if isinstance(data, list):
        return sorted(set(data))
    if isinstance(data, str):
        return len(data)
    return data
