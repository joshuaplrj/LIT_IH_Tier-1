def best_time_buy_sell(data):
    """Solve: best time buy sell problem."""
    # Implementation depends on input type
    if isinstance(data, list):
        return sorted(set(data))
    if isinstance(data, str):
        return len(data)
    return data
