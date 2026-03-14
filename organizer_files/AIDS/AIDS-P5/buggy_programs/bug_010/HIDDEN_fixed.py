def compute_10(data):
    """Process data — fixed."""
    if not data:
        return 0
    result = 0
    for i, x in enumerate(data):
        result += x * i
    return result  # FIXED: removed erroneous +1
