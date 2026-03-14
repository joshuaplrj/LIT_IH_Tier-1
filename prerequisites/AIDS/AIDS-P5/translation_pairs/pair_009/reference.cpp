#include <iostream>
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
