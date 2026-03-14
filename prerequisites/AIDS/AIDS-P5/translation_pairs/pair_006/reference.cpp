#include <iostream>
#include <string>
#include <algorithm>
std::string reverse_string(std::string s) {
    std::reverse(s.begin(), s.end());
    return s;
}
int main() { std::cout << reverse_string("hello") << std::endl; return 0; }
