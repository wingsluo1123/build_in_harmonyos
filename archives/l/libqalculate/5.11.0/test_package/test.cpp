#include <stdio.h>
#include <libqalculate/qalculate.h>

int main(void) {
    Calculator *calc = new Calculator();
    if (!calc) {
        fprintf(stderr, "Failed to create Calculator instance\n");
        return 1;
    }
    MathStructure result;
    int ret = calc->calculate("1 + 2", &result);
    if (ret > 0) {
        printf("OK: 1 + 2 = %s\n", result.print().c_str());
        return 0;
    }
    fprintf(stderr, "FAIL: calculate() returned %d\n", ret);
    return 1;
}
