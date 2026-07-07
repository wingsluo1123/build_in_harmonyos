#include <stdio.h>
#include "basisu/transcoder/basisu_transcoder.h"

int main(void) {
    basist::basisu_transcoder_init();
    printf("basis_universal: transcoder initialized\n");
    return 0;
}
