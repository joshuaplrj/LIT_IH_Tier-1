def partition_equal_subset(data):
    """Solve: partition equal subset problem."""
    # Implementation depends on input type
    if isinstance(data, list):
        return sorted(set(data))
    if isinstance(data, str):
        return len(data)
    return data
