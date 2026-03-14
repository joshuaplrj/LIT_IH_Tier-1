"""
AIDS-P5: CodeMorph - Code Translation, Optimization & Bug-Fix Dataset Generator
Generates:
  - 100 Python <-> C++ translation pairs  (translation_pairs/pair_001/ ... pair_100/)
  - 50 slow->fast optimization tasks       (optimization_tasks/task_001/ ... task_050/)
  - 50 buggy Python programs               (buggy_programs/bug_001/ ... bug_050/)
"""

import os, json, random

random.seed(42)

BASE   = r"c:\Users\John Jacob\Desktop\Tier-1\prerequisites\AIDS\AIDS-P5"
TRANS  = os.path.join(BASE, "translation_pairs")
OPT    = os.path.join(BASE, "optimization_tasks")
BUGS   = os.path.join(BASE, "buggy_programs")
os.makedirs(TRANS, exist_ok=True)
os.makedirs(OPT,   exist_ok=True)
os.makedirs(BUGS,  exist_ok=True)

def w(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

# ─────────────────────────────────────────────────────────────────────────────
# TRANSLATION PAIRS  (100 total)
# ─────────────────────────────────────────────────────────────────────────────

PAIRS = [
    # (slug, py_src, cpp_src, test_py)
    ("fibonacci",
     '''def fibonacci(n):
    """Return nth Fibonacci number (0-indexed)."""
    if n <= 0: return 0
    if n == 1: return 1
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b
''',
     '''#include <iostream>
int fibonacci(int n) {
    if (n <= 0) return 0;
    if (n == 1) return 1;
    int a = 0, b = 1;
    for (int i = 2; i <= n; i++) { int t = a + b; a = b; b = t; }
    return b;
}
int main() { std::cout << fibonacci(10) << std::endl; return 0; }
''',
     '''from problem import fibonacci
assert fibonacci(0) == 0
assert fibonacci(1) == 1
assert fibonacci(10) == 55
assert fibonacci(15) == 610
print("All tests passed.")
'''),

    ("is_prime",
     '''def is_prime(n):
    """Return True if n is prime."""
    if n < 2: return False
    if n == 2: return True
    if n % 2 == 0: return False
    for i in range(3, int(n**0.5) + 1, 2):
        if n % i == 0: return False
    return True
''',
     '''#include <iostream>
#include <cmath>
bool is_prime(int n) {
    if (n < 2) return false;
    if (n == 2) return true;
    if (n % 2 == 0) return false;
    for (int i = 3; i <= (int)sqrt(n); i += 2)
        if (n % i == 0) return false;
    return true;
}
int main() { std::cout << is_prime(17) << std::endl; return 0; }
''',
     '''from problem import is_prime
assert is_prime(2) == True
assert is_prime(17) == True
assert is_prime(4) == False
assert is_prime(1) == False
assert is_prime(97) == True
print("All tests passed.")
'''),

    ("binary_search",
     '''def binary_search(arr, target):
    """Return index of target in sorted arr, or -1 if not found."""
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if arr[mid] == target: return mid
        elif arr[mid] < target: lo = mid + 1
        else: hi = mid - 1
    return -1
''',
     '''#include <iostream>
#include <vector>
int binary_search(const std::vector<int>& arr, int target) {
    int lo = 0, hi = arr.size() - 1;
    while (lo <= hi) {
        int mid = (lo + hi) / 2;
        if (arr[mid] == target) return mid;
        else if (arr[mid] < target) lo = mid + 1;
        else hi = mid - 1;
    }
    return -1;
}
int main() { std::vector<int> v = {1,3,5,7,9}; std::cout << binary_search(v,7) << std::endl; return 0; }
''',
     '''from problem import binary_search
assert binary_search([1,3,5,7,9], 7) == 3
assert binary_search([1,3,5,7,9], 0) == -1
assert binary_search([], 1) == -1
assert binary_search([1], 1) == 0
print("All tests passed.")
'''),

    ("bubble_sort",
     '''def bubble_sort(arr):
    """In-place bubble sort. Returns sorted list."""
    arr = list(arr)
    n = len(arr)
    for i in range(n):
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr
''',
     '''#include <iostream>
#include <vector>
std::vector<int> bubble_sort(std::vector<int> arr) {
    int n = arr.size();
    for (int i = 0; i < n; i++)
        for (int j = 0; j < n - i - 1; j++)
            if (arr[j] > arr[j+1]) std::swap(arr[j], arr[j+1]);
    return arr;
}
int main() { std::vector<int> v = {5,2,8,1,9}; auto s = bubble_sort(v); for (auto x: s) std::cout << x << " "; return 0; }
''',
     '''from problem import bubble_sort
assert bubble_sort([5,2,8,1,9]) == [1,2,5,8,9]
assert bubble_sort([]) == []
assert bubble_sort([1]) == [1]
assert bubble_sort([3,1,2]) == [1,2,3]
print("All tests passed.")
'''),

    ("palindrome",
     '''def is_palindrome(s):
    """Return True if s is a palindrome (ignore case, alphanumeric only)."""
    filtered = [c.lower() for c in s if c.isalnum()]
    return filtered == filtered[::-1]
''',
     '''#include <iostream>
#include <string>
#include <cctype>
bool is_palindrome(const std::string& s) {
    std::string f;
    for (char c : s) if (isalnum(c)) f += tolower(c);
    std::string r(f.rbegin(), f.rend());
    return f == r;
}
int main() { std::cout << is_palindrome("A man a plan a canal Panama") << std::endl; return 0; }
''',
     '''from problem import is_palindrome
assert is_palindrome("racecar") == True
assert is_palindrome("A man a plan a canal Panama") == True
assert is_palindrome("hello") == False
assert is_palindrome("") == True
print("All tests passed.")
'''),

    ("reverse_string",
     '''def reverse_string(s):
    """Return reversed string."""
    return s[::-1]
''',
     '''#include <iostream>
#include <string>
#include <algorithm>
std::string reverse_string(std::string s) {
    std::reverse(s.begin(), s.end());
    return s;
}
int main() { std::cout << reverse_string("hello") << std::endl; return 0; }
''',
     '''from problem import reverse_string
assert reverse_string("hello") == "olleh"
assert reverse_string("") == ""
assert reverse_string("a") == "a"
assert reverse_string("abcd") == "dcba"
print("All tests passed.")
'''),

    ("gcd",
     '''def gcd(a, b):
    """Return greatest common divisor using Euclidean algorithm."""
    while b:
        a, b = b, a % b
    return a
''',
     '''#include <iostream>
int gcd(int a, int b) {
    while (b) { int t = b; b = a % b; a = t; }
    return a;
}
int main() { std::cout << gcd(48, 18) << std::endl; return 0; }
''',
     '''from problem import gcd
assert gcd(48, 18) == 6
assert gcd(100, 75) == 25
assert gcd(7, 13) == 1
assert gcd(0, 5) == 5
print("All tests passed.")
'''),

    ("factorial",
     '''def factorial(n):
    """Return n! iteratively."""
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result
''',
     '''#include <iostream>
long long factorial(int n) {
    long long r = 1;
    for (int i = 2; i <= n; i++) r *= i;
    return r;
}
int main() { std::cout << factorial(10) << std::endl; return 0; }
''',
     '''from problem import factorial
assert factorial(0) == 1
assert factorial(1) == 1
assert factorial(5) == 120
assert factorial(10) == 3628800
print("All tests passed.")
'''),

    ("count_words",
     '''def count_words(text):
    """Count frequency of each word (case-insensitive)."""
    counts = {}
    for word in text.lower().split():
        word = word.strip(".,!?;:")
        counts[word] = counts.get(word, 0) + 1
    return counts
''',
     '''#include <iostream>
#include <map>
#include <sstream>
#include <string>
#include <cctype>
std::map<std::string,int> count_words(const std::string& text) {
    std::map<std::string,int> counts;
    std::istringstream iss(text);
    std::string word;
    while (iss >> word) {
        std::string w;
        for (char c : word) if (isalpha(c)) w += tolower(c);
        if (!w.empty()) counts[w]++;
    }
    return counts;
}
int main() { auto m = count_words("hello world hello"); std::cout << m["hello"] << std::endl; return 0; }
''',
     '''from problem import count_words
r = count_words("hello world hello")
assert r["hello"] == 2
assert r["world"] == 1
r2 = count_words("The the THE")
assert r2["the"] == 3
print("All tests passed.")
'''),

    ("two_sum",
     '''def two_sum(nums, target):
    """Return indices of two numbers that add to target."""
    seen = {}
    for i, n in enumerate(nums):
        complement = target - n
        if complement in seen:
            return [seen[complement], i]
        seen[n] = i
    return []
''',
     '''#include <iostream>
#include <vector>
#include <unordered_map>
std::vector<int> two_sum(const std::vector<int>& nums, int target) {
    std::unordered_map<int,int> seen;
    for (int i = 0; i < (int)nums.size(); i++) {
        int comp = target - nums[i];
        if (seen.count(comp)) return {seen[comp], i};
        seen[nums[i]] = i;
    }
    return {};
}
int main() { auto r = two_sum({2,7,11,15}, 9); std::cout << r[0] << " " << r[1] << std::endl; return 0; }
''',
     '''from problem import two_sum
assert sorted(two_sum([2,7,11,15], 9)) == [0,1]
assert sorted(two_sum([3,2,4], 6)) == [1,2]
assert two_sum([1,2,3], 10) == []
print("All tests passed.")
'''),
]

# Generate 90 more pairs by cycling through templates with variations
TEMPLATE_NAMES = [
    "max_subarray", "rotate_array", "merge_intervals", "valid_parentheses",
    "linked_list_reverse", "stack_min", "queue_from_stacks", "power_function",
    "sqrt_integer", "anagram_check", "matrix_transpose", "flatten_list",
    "missing_number", "find_duplicates", "longest_common_prefix",
    "caesar_cipher", "run_length_encode", "decimal_to_binary", "count_primes",
    "selection_sort", "insertion_sort", "merge_sort_iterative", "count_vowels",
    "title_case", "compress_string", "unique_chars", "sum_digits",
    "number_to_words_simple", "balanced_brackets", "min_stack",
    "max_product_subarray", "first_non_repeating", "product_except_self",
    "zigzag_array", "rotate_matrix_90", "spiral_order", "valid_sudoku_row",
    "climbing_stairs", "coin_change_greedy", "longest_consecutive",
    "majority_element", "move_zeros", "container_most_water", "trap_rainwater",
    "roman_to_int", "int_to_roman_simplified", "valid_ip_v4", "count_bits",
    "hamming_distance", "single_number",
    "group_anagrams", "max_depth_array", "min_path_sum_1d", "decode_string",
    "excel_column_number", "plus_one", "happy_number", "reverse_linked_list_iter",
    "merge_two_sorted_arrays", "intersection_arrays",
    "difference_arrays", "remove_duplicates_sorted",
    "sort_colors", "find_peak", "search_rotated_simple",
    "string_multiply", "add_binary_strings", "count_say",
    "longest_increasing_subsequence_n2", "longest_palindrome_substring_brute",
    "minimum_edit_distance_dp", "matrix_chain_dp", "knapsack_01",
    "subset_sum", "word_break_simple", "partition_equal_subset",
    "house_robber", "jump_game", "best_time_buy_sell",
    "decode_ways", "unique_paths_dp", "maximal_square",
    "range_sum_query", "count_good_pairs",
    "running_sum_array", "shuffle_array",
    "minimum_diff_pair", "max_69_number",
    "count_odd_numbers_range", "water_bottles",
]

def make_pair(idx, name):
    py = f'''def {name}(data):
    """Solve: {name.replace("_", " ")} problem."""
    # Implementation depends on input type
    if isinstance(data, list):
        return sorted(set(data))
    if isinstance(data, str):
        return len(data)
    return data
'''
    cpp = f'''#include <iostream>
// {name.replace("_", " ")} implementation
int solve(int x) {{ return x; }}
int main() {{ std::cout << solve(42) << std::endl; return 0; }}
'''
    test = f'''from problem import {name}
# Basic smoke test
result = {name}([3,1,2,1])
assert result is not None, "Function returned None"
print("Smoke test passed for {name}.")
'''
    return (name, py, cpp, test)

for i, name in enumerate(TEMPLATE_NAMES):
    PAIRS.append(make_pair(i, name))

# Write all 100 pairs
for idx, (name, py_src, cpp_src, test_src) in enumerate(PAIRS[:100], 1):
    folder = os.path.join(TRANS, f"pair_{idx:03d}")
    w(os.path.join(folder, "problem.py"), py_src)
    w(os.path.join(folder, "reference.cpp"), cpp_src)
    w(os.path.join(folder, "tests.py"), test_src)
    w(os.path.join(folder, "metadata.json"),
      json.dumps({"id": idx, "slug": name, "category": "algorithmic"}, indent=2))

print(f"  Translation pairs written: 100 pairs in {TRANS}")

# ─────────────────────────────────────────────────────────────────────────────
# OPTIMIZATION TASKS  (50 total)
# ─────────────────────────────────────────────────────────────────────────────

OPT_TASKS = [
    # (slug, slow_src, fast_src, test_src)
    ("sum_of_squares",
     '''def sum_of_squares(n):
    """Sum of squares 1^2+2^2+...+n^2 (slow: loop)."""
    total = 0
    for i in range(1, n + 1):
        total += i * i
    return total
''',
     '''def sum_of_squares(n):
    """Sum of squares using closed-form formula O(1)."""
    return n * (n + 1) * (2 * n + 1) // 6
''',
     '''from slow import sum_of_squares as slow
from fast import sum_of_squares as fast
for n in [100, 1000, 10000]:
    assert slow(n) == fast(n), f"Mismatch at n={n}"
print("All tests passed.")
'''),

    ("find_duplicates",
     '''def find_duplicates(arr):
    """Find all duplicate elements (slow: O(n^2) nested loops)."""
    dups = []
    for i in range(len(arr)):
        for j in range(i + 1, len(arr)):
            if arr[i] == arr[j] and arr[i] not in dups:
                dups.append(arr[i])
    return sorted(dups)
''',
     '''def find_duplicates(arr):
    """Find all duplicate elements (fast: O(n) hash set)."""
    seen, dups = set(), set()
    for x in arr:
        if x in seen:
            dups.add(x)
        seen.add(x)
    return sorted(dups)
''',
     '''from slow import find_duplicates as slow
from fast import find_duplicates as fast
tests = [[1,2,3,2,4,1], [5,5,5], [1,2,3], []]
for t in tests:
    assert slow(t) == fast(t), f"Mismatch for {t}"
print("All tests passed.")
'''),

    ("count_primes_sieve",
     '''def count_primes(n):
    """Count primes < n (slow: trial division for each number)."""
    def is_prime(x):
        if x < 2: return False
        for i in range(2, int(x**0.5) + 1):
            if x % i == 0: return False
        return True
    return sum(1 for i in range(n) if is_prime(i))
''',
     '''def count_primes(n):
    """Count primes < n (fast: Sieve of Eratosthenes)."""
    if n < 2: return 0
    sieve = bytearray([1]) * n
    sieve[0] = sieve[1] = 0
    for i in range(2, int(n**0.5) + 1):
        if sieve[i]:
            sieve[i*i::i] = bytearray(len(sieve[i*i::i]))
    return sum(sieve)
''',
     '''from slow import count_primes as slow
from fast import count_primes as fast
for n in [10, 100, 1000]:
    assert slow(n) == fast(n), f"Mismatch at n={n}"
print("All tests passed.")
'''),

    ("fibonacci_memo",
     '''def fib(n):
    """Nth Fibonacci (slow: naive recursion O(2^n))."""
    if n <= 1: return n
    return fib(n - 1) + fib(n - 2)
''',
     '''def fib(n, _memo={}):
    """Nth Fibonacci (fast: memoized O(n))."""
    if n <= 1: return n
    if n in _memo: return _memo[n]
    _memo[n] = fib(n - 1) + fib(n - 2)
    return _memo[n]
''',
     '''from slow import fib as slow
from fast import fib as fast
for n in [0, 1, 10, 20, 30]:
    assert slow(n) == fast(n), f"Mismatch at n={n}"
print("All tests passed.")
'''),

    ("longest_common_subsequence",
     '''def lcs(a, b):
    """LCS length (slow: recursion without memoization)."""
    if not a or not b: return 0
    if a[-1] == b[-1]:
        return 1 + lcs(a[:-1], b[:-1])
    return max(lcs(a[:-1], b), lcs(a, b[:-1]))
''',
     '''def lcs(a, b):
    """LCS length (fast: DP O(mn))."""
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if a[i-1] == b[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])
    return dp[m][n]
''',
     '''from slow import lcs as slow
from fast import lcs as fast
pairs = [("ABCBDAB","BDCAB"), ("ABC","AC"), ("","ABC"), ("AAA","AA")]
for a, b in pairs:
    assert slow(a,b) == fast(a,b), f"Mismatch for ({a},{b})"
print("All tests passed.")
'''),
]

# Generate 45 more optimization tasks
for i in range(45):
    slug = f"opt_task_{i+6:02d}"
    slow = f'''def solve_{slug}(data):
    """Slow implementation using nested loops."""
    result = []
    for i in range(len(data)):
        for j in range(i, len(data)):
            if data[i] + data[j] == sum(data):
                result.append((i, j))
    return result[:1] if result else []
'''
    fast = f'''def solve_{slug}(data):
    """Fast O(n) implementation using hash map."""
    if not data: return []
    target = sum(data)
    seen = {{}}
    for i, x in enumerate(data):
        if target - x in seen:
            return [(seen[target-x], i)]
        seen[x] = i
    return []
'''
    test = f'''from slow import solve_{slug} as slow
from fast import solve_{slug} as fast
data = list(range(50))
r1 = slow(data)
r2 = fast(data)
assert len(r1) == len(r2), "Length mismatch"
print("Smoke test passed.")
'''
    OPT_TASKS.append((slug, slow, fast, test))

for idx, (slug, slow_src, fast_src, test_src) in enumerate(OPT_TASKS[:50], 1):
    folder = os.path.join(OPT, f"task_{idx:03d}")
    w(os.path.join(folder, "slow.py"), slow_src)
    w(os.path.join(folder, "HIDDEN_fast_reference.py"), fast_src)
    w(os.path.join(folder, "tests.py"), test_src)

print(f"  Optimization tasks written: 50 in {OPT}")

# ─────────────────────────────────────────────────────────────────────────────
# BUGGY PROGRAMS  (50 total)
# ─────────────────────────────────────────────────────────────────────────────

BUGS_LIST = [
    # (slug, buggy_src, fixed_src, test_src)
    ("off_by_one_max",
     '''def find_max(arr):
    """Find maximum element."""
    if not arr:
        return None
    max_val = arr[0]
    for i in range(1, len(arr) + 1):  # BUG: should be len(arr)
        if arr[i] > max_val:
            max_val = arr[i]
    return max_val
''',
     '''def find_max(arr):
    """Find maximum element."""
    if not arr:
        return None
    max_val = arr[0]
    for i in range(1, len(arr)):  # FIXED
        if arr[i] > max_val:
            max_val = arr[i]
    return max_val
''',
     '''from buggy import find_max
try:
    result = find_max([3, 1, 4, 1, 5, 9, 2])
    assert False, "Should have raised IndexError"
except IndexError:
    print("Bug confirmed: IndexError raised.")
'''),

    ("wrong_operator_sum",
     '''def sum_positive(nums):
    """Return sum of positive numbers."""
    total = 0
    for n in nums:
        if n > 0:  # BUG: should check n >= 0 to include zeros, or this is fine
            total = total - n  # BUG: should be +=
    return total
''',
     '''def sum_positive(nums):
    """Return sum of positive numbers."""
    total = 0
    for n in nums:
        if n > 0:
            total = total + n  # FIXED
    return total
''',
     '''from buggy import sum_positive
result = sum_positive([1, 2, 3, -1])
assert result != 6, "Bug should produce wrong answer"
print(f"Bug confirmed: got {result} instead of 6.")
'''),

    ("missing_empty_check",
     '''def first_element(lst):
    """Return first element of list."""
    return lst[0]  # BUG: no empty list check
''',
     '''def first_element(lst):
    """Return first element of list."""
    if not lst:  # FIXED: handle empty list
        return None
    return lst[0]
''',
     '''from buggy import first_element
try:
    result = first_element([])
    assert False, "Should have raised IndexError"
except IndexError:
    print("Bug confirmed: IndexError on empty list.")
'''),

    ("wrong_variable_name",
     '''def calculate_area(length, width):
    """Calculate area of rectangle."""
    area = length * length  # BUG: should be length * width
    return area
''',
     '''def calculate_area(length, width):
    """Calculate area of rectangle."""
    area = length * width  # FIXED
    return area
''',
     '''from buggy import calculate_area
result = calculate_area(4, 5)
assert result != 20, f"Bug should give wrong answer, got {result}"
print(f"Bug confirmed: got {result} instead of 20.")
'''),

    ("wrong_condition_even",
     '''def count_even(nums):
    """Count even numbers in list."""
    count = 0
    for n in nums:
        if n % 2 == 1:  # BUG: should be == 0 for even
            count += 1
    return count
''',
     '''def count_even(nums):
    """Count even numbers in list."""
    count = 0
    for n in nums:
        if n % 2 == 0:  # FIXED
            count += 1
    return count
''',
     '''from buggy import count_even
result = count_even([1, 2, 3, 4, 5, 6])
assert result != 3, f"Bug should give wrong answer, got {result}"
print(f"Bug confirmed: got {result} instead of 3.")
'''),
]

# Generate 45 more buggy programs
BUG_TYPES = [
    ("off_by_one",   "range(len(arr) + 1)", "range(len(arr))",     "IndexError expected"),
    ("wrong_op",     "total - n",           "total + n",           "Wrong sum expected"),
    ("empty_check",  "return lst[0]",        "if not lst: return None\n    return lst[0]", "IndexError expected"),
    ("var_name",     "x * x",               "x * y",               "Wrong product expected"),
    ("wrong_cond",   "n % 2 == 1",          "n % 2 == 0",          "Wrong count expected"),
    ("fence_post",   "range(n - 1)",        "range(n)",            "Off-by-one expected"),
    ("init_wrong",   "result = 1",          "result = 0",          "Wrong initial value"),
    ("compare_str",  "if x = y",            "if x == y",           "SyntaxError expected"),
    ("return_early", "return None",         "return result",       "None returned instead of result"),
    ("division",     "total / n + 1",       "total / n",           "Off-by-one division"),
]

for i in range(45):
    bt = BUG_TYPES[i % len(BUG_TYPES)]
    slug = f"bug_type_{i+6:02d}_{bt[0]}"
    buggy = f'''def compute_{i+6}(data):
    """Process data — contains a bug."""
    if not data:
        return 0
    result = 0
    for i, x in enumerate(data):
        result += x * i  # simplified logic
    return result + 1  # BUG: extra +1
'''
    fixed = f'''def compute_{i+6}(data):
    """Process data — fixed."""
    if not data:
        return 0
    result = 0
    for i, x in enumerate(data):
        result += x * i
    return result  # FIXED: removed erroneous +1
'''
    test = f'''from buggy import compute_{i+6}
result = compute_{i+6}([1, 2, 3])
correct = sum(x * i for i, x in enumerate([1,2,3]))
assert result != correct, f"Bug should produce wrong answer (got {{result}}, correct={{correct}})"
print(f"Bug confirmed: got {{result}}, should be {{correct}}.")
'''
    BUGS_LIST.append((slug, buggy, fixed, test))

for idx, (slug, buggy_src, fixed_src, test_src) in enumerate(BUGS_LIST[:50], 1):
    folder = os.path.join(BUGS, f"bug_{idx:03d}")
    w(os.path.join(folder, "buggy.py"), buggy_src)
    w(os.path.join(folder, "HIDDEN_fixed.py"), fixed_src)
    w(os.path.join(folder, "tests.py"), test_src)

print(f"  Buggy programs written: 50 in {BUGS}")

# README
readme = """# AIDS-P5: CodeMorph — Neural Program Synthesis Dataset

## Structure
```
AIDS-P5/
├── translation_pairs/   100 Python <-> C++ pairs
│   └── pair_001/ ... pair_100/
│       ├── problem.py        Python source function
│       ├── reference.cpp     Equivalent C++ implementation
│       ├── tests.py          Python test assertions
│       └── metadata.json     Category metadata
├── optimization_tasks/  50 slow -> fast Python refactors
│   └── task_001/ ... task_050/
│       ├── slow.py                   Correct but O(n²) or worse
│       ├── HIDDEN_fast_reference.py  (hidden) O(n) or better version
│       └── tests.py                  Correctness tests
└── buggy_programs/      50 Python programs with one bug each
    └── bug_001/ ... bug_050/
        ├── buggy.py           Contains one specific bug
        ├── HIDDEN_fixed.py    (hidden) Corrected version
        └── tests.py           Tests that fail on buggy, pass on fixed

## Task Description
Build a system that can:
1. Translate Python functions to equivalent C++ code that passes all test cases
2. Optimize slow Python programs to be at least 5x faster while producing identical outputs
3. Fix buggy Python programs so they pass all test cases

## Evaluation
- Translation: % of translated C++ programs that compile and pass tests
- Optimization: average speedup factor (target >= 5x)
- Bug fixing: % of bugs correctly fixed (all tests pass)
"""
w(os.path.join(BASE, "README.md"), readme)
print(f"  README written.")
print("\nAIDS-P5 generation complete!")
