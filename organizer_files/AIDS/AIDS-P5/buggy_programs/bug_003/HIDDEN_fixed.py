def first_element(lst):
    """Return first element of list."""
    if not lst:  # FIXED: handle empty list
        return None
    return lst[0]
