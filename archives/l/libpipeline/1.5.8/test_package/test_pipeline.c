#include <pipeline.h>
#include <stdio.h>

int main(void) {
    pipeline *p = pipeline_new();
    if (p == NULL) {
        fprintf(stderr, "Failed to create pipeline\n");
        return 1;
    }
    printf("pipeline created successfully\n");
    pipeline_free(p);
    return 0;
}
