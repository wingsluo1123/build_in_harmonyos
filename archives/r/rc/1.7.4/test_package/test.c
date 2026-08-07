// test.c — rc L1 test binary.
//
// R34: test_package must make substantive use of the tested package.
// rc is a command-line shell tool; this test runs the rc binary
// and verifies it can execute a simple echo command.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char *argv[]) {
    const char *rc_path = "rc";
    if (argc > 1) {
        rc_path = argv[1];
    }

    char cmd[1024];
    // rc -c 'echo hello' should output "hello"
    snprintf(cmd, sizeof(cmd), "%s -c 'echo hello' 2>/dev/null", rc_path);

    // Assertion 1: rc -c 'echo hello' exits with code 0
    int ret = system(cmd);
    if (ret != 0) {
        printf("rc -c 'echo hello': FAILED (exit %d)\n", ret);
        return 1;
    }
    printf("rc -c 'echo hello': exit code OK\n");

    // Assertion 2: output contains "hello"
    FILE *fp = popen(cmd, "r");
    if (!fp) {
        printf("popen: FAILED\n");
        return 1;
    }
    char buf[256];
    int found_hello = 0;
    while (fgets(buf, sizeof(buf), fp)) {
        if (strstr(buf, "hello") != NULL) {
            found_hello = 1;
            break;
        }
    }
    pclose(fp);

    if (!found_hello) {
        printf("rc output check: FAILED (no 'hello' in output)\n");
        return 1;
    }
    printf("rc output check: 'hello' found\n");

    // Assertion 3: rc version variable
    snprintf(cmd, sizeof(cmd), "%s -c 'echo $version' 2>/dev/null", rc_path);
    fp = popen(cmd, "r");
    if (!fp) {
        printf("popen(version): FAILED\n");
        return 1;
    }
    int found_version = 0;
    while (fgets(buf, sizeof(buf), fp)) {
        if (strstr(buf, "1.7.4") != NULL) {
            found_version = 1;
            break;
        }
    }
    pclose(fp);

    if (!found_version) {
        printf("rc version check: FAILED (no '1.7.4' in output)\n");
        return 1;
    }
    printf("rc version check: '1.7.4' found\n");

    printf("All tests passed\n");
    return 0;
}
