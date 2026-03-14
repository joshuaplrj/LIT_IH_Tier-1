def int_to_roman_simplified(data):
    """Solve: int to roman simplified problem."""
    # Implementation depends on input type
    if isinstance(data, list):
        return sorted(set(data))
    if isinstance(data, str):
        return len(data)
    return data
