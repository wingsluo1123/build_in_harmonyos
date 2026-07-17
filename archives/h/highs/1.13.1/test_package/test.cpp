#include <stdio.h>
#include <stdlib.h>
#include "Highs.h"

int main(void) {
    Highs highs;
    HighsStatus status = highs.run();
    if (status == HighsStatus::kHighsStatusError) {
        printf("test highs 1.13.1: FAILED\n");
        return 1;
    }
    printf("test highs 1.13.1: OK\n");
    return 0;
}