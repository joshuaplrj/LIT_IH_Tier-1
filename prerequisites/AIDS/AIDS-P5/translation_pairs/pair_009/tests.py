from problem import count_words
r = count_words("hello world hello")
assert r["hello"] == 2
assert r["world"] == 1
r2 = count_words("The the THE")
assert r2["the"] == 3
print("All tests passed.")
