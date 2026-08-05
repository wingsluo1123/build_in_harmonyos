#include <stdio.h>

static int add(int lhs, int rhs) {
    return lhs + rhs;
}

int main(void) {
    int value = add(12, 5);
    if (value != 17) {
        return 1;
    }
    puts("gcc@12 C smoke ok");
    return 0;
}
