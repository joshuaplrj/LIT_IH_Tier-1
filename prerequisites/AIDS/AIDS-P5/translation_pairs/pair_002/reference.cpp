#include <iostream>
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
