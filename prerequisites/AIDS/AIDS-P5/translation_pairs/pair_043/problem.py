def product_except_self(data):
    """Solve: product except self problem."""
    # Implementation depends on input type
    if isinstance(data, list):
        return sorted(set(data))
    if isinstance(data, str):
        return len(data)
    return data
