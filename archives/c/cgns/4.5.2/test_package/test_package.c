#include <stdio.h>
#include <cgnslib.h>

int main(void) {
    int ier;
    int file_type, data_type;
    char filename[] = "test_cgns.cgns";

    ier = cg_open(filename, CG_MODE_READ, &file_type);
    if (ier != CG_ERROR) {
        printf("CGNS library linkage OK\n");
        cg_close(ier);
        return 0;
    }
    printf("CGNS library linked and ready\n");
    return 0;
}
