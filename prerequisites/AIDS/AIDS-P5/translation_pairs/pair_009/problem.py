def count_words(text):
    """Count frequency of each word (case-insensitive)."""
    counts = {}
    for word in text.lower().split():
        word = word.strip(".,!?;:")
        counts[word] = counts.get(word, 0) + 1
    return counts
