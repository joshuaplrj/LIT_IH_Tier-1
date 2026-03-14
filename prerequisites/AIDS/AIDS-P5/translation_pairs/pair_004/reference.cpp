#include <iostream>
#include <vector>
std::vector<int> bubble_sort(std::vector<int> arr) {
    int n = arr.size();
    for (int i = 0; i < n; i++)
        for (int j = 0; j < n - i - 1; j++)
            if (arr[j] > arr[j+1]) std::swap(arr[j], arr[j+1]);
    return arr;
}
int main() { std::vector<int> v = {5,2,8,1,9}; auto s = bubble_sort(v); for (auto x: s) std::cout << x << " "; return 0; }
