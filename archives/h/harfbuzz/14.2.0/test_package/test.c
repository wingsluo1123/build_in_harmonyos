#include <stdio.h>
#include <hb.h>

int main(void) {
    printf("HarfBuzz version: %s\n", hb_version_string());
    return 0;
}