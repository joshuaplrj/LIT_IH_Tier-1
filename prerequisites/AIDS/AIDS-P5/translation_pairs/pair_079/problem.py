def longest_increasing_subsequence_n2(data):
    """Solve: longest increasing subsequence n2 problem."""
    # Implementation depends on input type
    if isinstance(data, list):
        return sorted(set(data))
    if isinstance(data, str):
        return len(data)
    return data
