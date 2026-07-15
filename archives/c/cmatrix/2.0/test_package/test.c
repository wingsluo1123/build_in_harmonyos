#include <stdlib.h>

int main() {
    return system("cmatrix -V > /dev/null 2>&1") == 0 ? 0 : 1;
}