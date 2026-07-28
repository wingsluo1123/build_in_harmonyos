#include <stdio.h>
#include <stdlib.h>

int main(void) {
    int ret;

    /* Test 1: ipsumdump --version */
    printf("[test] checking ipsumdump --version ...\n");
    ret = system("ipsumdump --version > /dev/null 2>&1");
    if (ret != 0) {
        printf("[FAIL] ipsumdump --version returned %d\n", ret);
        return 1;
    }
    printf("[PASS] ipsumdump --version works\n");

    /* Test 2: ipsumdump -c -r on a minimal pcap file */
    printf("[test] checking ipsumdump -c -r test.pcap ...\n");
    ret = system("ipsumdump -c -r test.pcap > /dev/null 2>&1");
    if (ret != 0) {
        printf("[FAIL] ipsumdump -c -r returned %d\n", ret);
        return 1;
    }
    printf("[PASS] ipsumdump -c -r works\n");

    printf("All test_package tests passed!\n");
    return 0;
}
