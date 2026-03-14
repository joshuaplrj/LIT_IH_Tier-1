#include <iostream>
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
