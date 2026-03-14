#include <iostream>
#include <string>
#include <cctype>
bool is_palindrome(const std::string& s) {
    std::string f;
    for (char c : s) if (isalnum(c)) f += tolower(c);
    std::string r(f.rbegin(), f.rend());
    return f == r;
}
int main() { std::cout << is_palindrome("A man a plan a canal Panama") << std::endl; return 0; }
