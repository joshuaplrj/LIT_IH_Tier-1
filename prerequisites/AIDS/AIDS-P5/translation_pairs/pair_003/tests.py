from problem import binary_search
assert binary_search([1,3,5,7,9], 7) == 3
assert binary_search([1,3,5,7,9], 0) == -1
assert binary_search([], 1) == -1
assert binary_search([1], 1) == 0
print("All tests passed.")
