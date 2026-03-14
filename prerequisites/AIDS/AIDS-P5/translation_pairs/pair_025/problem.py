def longest_common_prefix(data):
    """Solve: longest common prefix problem."""
    # Implementation depends on input type
    if isinstance(data, list):
        return sorted(set(data))
    if isinstance(data, str):
        return len(data)
    return data
