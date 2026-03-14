#include <iostream>
long long factorial(int n) {
    long long r = 1;
    for (int i = 2; i <= n; i++) r *= i;
    return r;
}
int main() { std::cout << factorial(10) << std::endl; return 0; }
