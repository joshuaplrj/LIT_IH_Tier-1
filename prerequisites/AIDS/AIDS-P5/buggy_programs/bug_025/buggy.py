def compute_25(data):
    """Process data — contains a bug."""
    if not data:
        return 0
    result = 0
    for i, x in enumerate(data):
        result += x * i  # simplified logic
    return result + 1  # BUG: extra +1
