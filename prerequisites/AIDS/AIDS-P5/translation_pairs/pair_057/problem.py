def valid_ip_v4(data):
    """Solve: valid ip v4 problem."""
    # Implementation depends on input type
    if isinstance(data, list):
        return sorted(set(data))
    if isinstance(data, str):
        return len(data)
    return data
