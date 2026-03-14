def is_palindrome(s):
    """Return True if s is a palindrome (ignore case, alphanumeric only)."""
    filtered = [c.lower() for c in s if c.isalnum()]
    return filtered == filtered[::-1]
