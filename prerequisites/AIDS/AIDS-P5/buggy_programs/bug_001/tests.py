from buggy import find_max
try:
    result = find_max([3, 1, 4, 1, 5, 9, 2])
    assert False, "Should have raised IndexError"
except IndexError:
    print("Bug confirmed: IndexError raised.")
