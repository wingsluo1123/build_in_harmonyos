#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <matio.h>

/* test_package consumer: exercises the public matio API end-to-end.
 * Creates a MAT5 file, writes a 2D double array, reads it back and
 * verifies the values — a real business-meaningful API round-trip. */
int main(void) {
    const char *fname = "test_package_matio.mat";
    mat_t *mat;
    matvar_t *var, *read;
    size_t dims[2] = {2, 3};
    double data[6] = {1.0, 2.0, 3.0, 4.0, 5.0, 6.0};
    int rc = 0;

    mat = Mat_CreateVer(fname, NULL, MAT_FT_MAT5);
    if (!mat) {
        fprintf(stderr, "FAIL: Mat_CreateVer\n");
        return 1;
    }
    var = Mat_VarCreate("data", MAT_C_DOUBLE, MAT_T_DOUBLE, 2, dims,
                        data, 0);
    if (!var) {
        fprintf(stderr, "FAIL: Mat_VarCreate\n");
        Mat_Close(mat);
        return 1;
    }
    if (Mat_VarWrite(mat, var, MAT_COMPRESSION_NONE) != 0) {
        fprintf(stderr, "FAIL: Mat_VarWrite\n");
        Mat_VarFree(var);
        Mat_Close(mat);
        return 1;
    }
    Mat_VarFree(var);
    Mat_Close(mat);

    mat = Mat_Open(fname, MAT_ACC_RDONLY);
    if (!mat) {
        fprintf(stderr, "FAIL: Mat_Open\n");
        return 1;
    }
    read = Mat_VarRead(mat, "data");
    if (!read) {
        fprintf(stderr, "FAIL: Mat_VarRead\n");
        Mat_Close(mat);
        return 1;
    }
    if (read->rank != 2 || read->dims[0] != 2 || read->dims[1] != 3) {
        fprintf(stderr, "FAIL: dims mismatch\n");
        rc = 1;
    } else {
        double *val = (double *)read->data;
        for (int i = 0; i < 6; i++) {
            if (val[i] != data[i]) {
                fprintf(stderr, "FAIL: data[%d]=%g != %g\n", i, val[i], data[i]);
                rc = 1;
                break;
            }
        }
    }
    Mat_VarFree(read);
    Mat_Close(mat);
    remove(fname);

    if (rc == 0) {
        printf("test_package matio 1.5.26: PASS (write/read round-trip OK)\n");
    }
    return rc;
}
