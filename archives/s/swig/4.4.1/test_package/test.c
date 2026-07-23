/* test.c — C implementation of functions declared in test.i
 * This file provides the actual implementation that SWIG wraps.
 * The test_package conanfile.py uses swig -python to generate wrapper code
 * from test.i, which references these functions.
 */
int add(int a, int b) {
    return a + b;
}

int multiply(int a, int b) {
    return a * b;
}
