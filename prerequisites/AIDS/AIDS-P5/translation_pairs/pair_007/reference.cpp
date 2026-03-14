#include <iostream>
int gcd(int a, int b) {
    while (b) { int t = b; b = a % b; a = t; }
    return a;
}
int main() { std::cout << gcd(48, 18) << std::endl; return 0; }
