def find_peak(data):
    """Solve: find peak problem."""
    # Implementation depends on input type
    if isinstance(data, list):
        return sorted(set(data))
    if isinstance(data, str):
        return len(data)
    return data
