from buggy import first_element
try:
    result = first_element([])
    assert False, "Should have raised IndexError"
except IndexError:
    print("Bug confirmed: IndexError on empty list.")
