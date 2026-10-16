#include <stdio.h>
#include <string.h>

typedef struct { int value[10]; } big_value;

int main(void) {
    big_value zero = {{0}}, ones = {{1, 1, 1, 1, 1, 1, 1, 1, 1, 1}};
    big_value current, observed, expected;
    __atomic_store(&current, &zero, __ATOMIC_SEQ_CST);
    __atomic_store(&current, &ones, __ATOMIC_SEQ_CST);
    __atomic_load(&current, &observed, __ATOMIC_SEQ_CST);
    if (memcmp(&observed, &ones, sizeof observed) != 0) return 1;
    expected = ones;
    if (!__atomic_compare_exchange(&current, &expected, &zero, 0,
                                   __ATOMIC_SEQ_CST, __ATOMIC_SEQ_CST)) return 2;
    __atomic_load(&current, &observed, __ATOMIC_SEQ_CST);
    if (memcmp(&observed, &zero, sizeof observed) != 0) return 3;
    puts("libatomic consumer 3/3 PASS");
    return 0;
}
