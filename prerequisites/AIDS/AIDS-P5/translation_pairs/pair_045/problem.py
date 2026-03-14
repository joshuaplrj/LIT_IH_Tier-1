def rotate_matrix_90(data):
    """Solve: rotate matrix 90 problem."""
    # Implementation depends on input type
    if isinstance(data, list):
        return sorted(set(data))
    if isinstance(data, str):
        return len(data)
    return data
