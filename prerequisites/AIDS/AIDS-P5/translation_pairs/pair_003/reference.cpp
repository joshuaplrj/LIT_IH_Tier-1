#include <iostream>
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
